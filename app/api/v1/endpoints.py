import io
import logging

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import db_client
from app.schemas.empresa import EmpresaResponse

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.APP_ENV != "testing",
)


# ============================================================
# CONFIGURAÇÃO DOS DADOS
# ============================================================

ESTAB_PATH = settings.ESTAB_PATH
EMPRESAS_PATH = settings.EMPRESAS_PATH
R2_PATH = settings.R2_PATH


# ============================================================
# BUSCA DE EMPRESAS
# ============================================================


@router.get("/busca", response_model=EmpresaResponse)
@limiter.limit("10/minute")
async def buscar_empresas(
    request: Request,
    uf: str | None = Query(
        None,
        min_length=2,
        max_length=2,
        pattern="^[A-Za-z]{2}$",
        description="Sigla do estado (ex: BA)",
    ),
    municipio: str | None = Query(
        None,
        description="Código do município",
    ),
    cnae: str | None = Query(
        None,
        description="Código do CNAE",
    ),
    ativa: bool = Query(
        True,
        description="Filtrar apenas empresas ativas",
    ),
    com_telefone: bool = Query(
        False,
        description="Filtrar apenas empresas com telefone",
    ),
    com_email: bool = Query(
        False,
        description="Filtrar apenas empresas com e-mail",
    ),
    page: int = Query(
        1,
        ge=1,
    ),
    limit: int = Query(
        20,
        ge=1,
        le=100,
    ),
):
    offset = (page - 1) * limit

    where_clauses = []
    params = []

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    if uf:
        where_clauses.append("est.uf = ?")
        params.append(uf.upper())

    if municipio:
        where_clauses.append("est.municipio = ?")
        params.append(municipio)

    if cnae:
        where_clauses.append("est.cnae_fiscal_principal = ?")
        params.append(cnae)

    if ativa:
        where_clauses.append("est.situacao_cadastral = '02'")

    if com_telefone:
        where_clauses.append("(est.telefone_1 IS NOT NULL AND est.telefone_1 != '')")

    if com_email:
        where_clauses.append(
            "(est.correio_eletronico IS NOT NULL AND est.correio_eletronico != '')"
        )

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # --------------------------------------------------------
    # Consulta paginada
    # --------------------------------------------------------

    sql = f"""
        SELECT
            est.cnpj_basico,
            emp.razao_social,
            est.nome_fantasia,
            est.situacao_cadastral,
            est.uf,
            est.municipio,
            est.cnae_fiscal_principal,
            est.correio_eletronico,
            CONCAT(
                '(',
                est.ddd_1,
                ') ',
                est.telefone_1
            ) AS telefone_1

        FROM read_parquet(
            '{ESTAB_PATH}/**/*.parquet',
            hive_partitioning = true
        ) AS est

        JOIN read_parquet(
            '{EMPRESAS_PATH}/*.parquet'
        ) AS emp
            ON est.cnpj_basico = emp.cnpj_basico

        WHERE {where_sql}

        LIMIT ?
        OFFSET ?
    """

    query_params = params + [limit, offset]

    # --------------------------------------------------------
    # Contagem total
    # --------------------------------------------------------

    count_sql = f"""
        SELECT COUNT(*) AS total

        FROM read_parquet(
            '{ESTAB_PATH}/**/*.parquet',
            hive_partitioning = true
        ) AS est

        WHERE {where_sql}
    """

    try:
        results = db_client.query_params(
            sql,
            query_params,
        )

        total_df = db_client.query_params(
            count_sql,
            params,
        )

        total = total_df.iloc[0]["total"] if not total_df.empty else 0

        data = results.to_dict("records")
        for item in data:
            for k, v in item.items():
                if pd.isna(v):
                    item[k] = None

        return {
            "total_count": int(total),
            "page": page,
            "limit": limit,
            "data": data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro inesperado na busca")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a consulta",
        ) from e


# ============================================================
# EXPORTAÇÃO
# ============================================================


@router.get("/exportar/{formato}")
@limiter.limit("2/minute")
async def exportar_dados(
    request: Request,
    formato: str,
    uf: str | None = Query(None),
    ativa: bool = Query(True),
    com_telefone: bool = Query(False),
    com_email: bool = Query(False),
):
    # --------------------------------------------------------
    # Validação do formato
    # --------------------------------------------------------

    formato = formato.lower()

    if formato not in {"csv", "xlsx"}:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Use csv ou xlsx.",
        )

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    where_clauses = []
    params = []

    if uf:
        where_clauses.append("est.uf = ?")
        params.append(uf.upper())

    if ativa:
        where_clauses.append("est.situacao_cadastral = '02'")

    if com_telefone:
        where_clauses.append("(est.telefone_1 IS NOT NULL AND est.telefone_1 != '')")

    if com_email:
        where_clauses.append(
            "(est.correio_eletronico IS NOT NULL AND est.correio_eletronico != '')"
        )

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    # --------------------------------------------------------
    # Consulta
    # --------------------------------------------------------

    sql = f"""
        SELECT
            est.cnpj_basico,
            emp.razao_social,
            est.nome_fantasia,
            est.uf,
            est.municipio,
            est.correio_eletronico,
            est.telefone_1

        FROM read_parquet(
            '{ESTAB_PATH}/**/*.parquet',
            hive_partitioning = true
        ) AS est

        JOIN read_parquet(
            '{EMPRESAS_PATH}/*.parquet'
        ) AS emp
            ON est.cnpj_basico = emp.cnpj_basico

        WHERE {where_sql}

        LIMIT 10000
    """

    try:
        df = db_client.query_params(
            sql,
            params,
        )

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        if formato == "csv":
            stream = io.StringIO()

            df.to_csv(
                stream,
                index=False,
                sep=";",
                encoding="utf-8-sig",
            )

            response = StreamingResponse(
                iter([stream.getvalue()]),
                media_type="text/csv",
            )

            response.headers["Content-Disposition"] = (
                "attachment; filename=buscafri_export.csv"
            )

            return response

        # ----------------------------------------------------
        # XLSX
        # ----------------------------------------------------

        output = io.BytesIO()

        with pd.ExcelWriter(
            output,
            engine="xlsxwriter",
        ) as writer:
            df.to_excel(
                writer,
                index=False,
                sheet_name="Empresas",
            )

        output.seek(0)

        return StreamingResponse(
            output,
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition": ("attachment; filename=buscafri_export.xlsx")
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro inesperado na exportação")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao processar a exportação",
        ) from e
