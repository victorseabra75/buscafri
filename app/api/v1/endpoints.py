import base64
import binascii
import hashlib
import hmac
import io
import json
import logging
from pathlib import Path
from typing import Any

import duckdb
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

SORT_COLUMNS = [
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


def sql_literal(value: str) -> str:
    """Escapa um valor textual para uso como literal SQL."""
    return "'" + value.replace("'", "''") + "'"


def build_estab_pattern(uf: str | None) -> str:
    """Monta o padrão dos arquivos de estabelecimentos."""
    if uf:
        return f"{ESTAB_PATH.rstrip('/')}/uf={uf.upper()}/*.parquet"

    return f"{ESTAB_PATH.rstrip('/')}/**/*.parquet"


def cursor_predicate(cursor_data: dict[str, Any]) -> tuple[str, list[Any]]:
    """Cria o predicado SQL para avançar na ordenação do cursor, tratando NULLS LAST."""
    cols = [
        "est.municipio",
        "est.cnae_fiscal_principal",
        "est.cnpj_basico",
        "est.cnpj_ordem",
        "est.cnpj_dv",
    ]
    keys = ["m", "c", "b", "o", "d"]
    params = []

    def build_recursive(index: int) -> str:
        if index >= len(cols):
            return "FALSE"

        col = cols[index]
        val = cursor_data.get(keys[index])

        # Predicado para col > val considerando NULLS LAST:
        # (col > val) OR (col IS NULL AND val IS NOT NULL)
        strict_gt = f"({col} > ? OR ({col} IS NULL AND ? IS NOT NULL))"
        params.extend([val, val])

        # Predicado para col = val considerando NULLS (IS NOT DISTINCT FROM):
        eq = f"{col} IS NOT DISTINCT FROM ?"
        params.append(val)

        return f"({strict_gt} OR ({eq} AND {build_recursive(index + 1)}))"

    predicate = build_recursive(0)
    return predicate, params


def sign_cursor(payload: str) -> str:
    """Gera uma assinatura HMAC-SHA256 para o payload."""
    return hmac.new(
        settings.APP_SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_filters_hash(filters: dict[str, Any]) -> str:
    """Gera um hash curto para vincular o cursor aos filtros da consulta."""
    normalized = {
        k: str(v).upper() if v is not None else "" for k, v in filters.items()
    }
    content = json.dumps(normalized, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def decode_cursor(cursor: str, filters_hash: str) -> dict[str, Any]:
    """Decodifica, valida e verifica a integridade de um cursor."""
    try:
        # Readiciona preenchimento se necessário
        padding = 4 - (len(cursor) % 4)
        if padding < 4:
            cursor += "=" * padding

        decoded = base64.urlsafe_b64decode(cursor).decode("utf-8")
        if "|" not in decoded:
            raise ValueError("Formato de cursor inválido.")

        payload, sig = decoded.rsplit("|", 1)

        if not hmac.compare_digest(sign_cursor(payload), sig):
            raise ValueError("Assinatura do cursor inválida.")

        cursor_data = json.loads(payload)

        if not isinstance(cursor_data, dict):
            raise TypeError("O cursor precisa conter um objeto JSON.")

        if cursor_data.get("v") != 1:
            raise ValueError("Versão de cursor incompatível.")

        if cursor_data.get("f") != filters_hash:
            raise ValueError("Cursor incompatível com os filtros aplicados.")

        required_fields = ("m", "c", "b", "o", "d")
        for field in required_fields:
            if field not in cursor_data:
                raise KeyError(f"Campo obrigatório ausente no cursor: {field}")

        return cursor_data

    except (
        binascii.Error,
        UnicodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        KeyError,
    ) as error:
        logger.warning("Tentativa de uso de cursor inválido: %s", str(error))
        raise HTTPException(
            status_code=400,
            detail="Cursor inválido ou incompatível",
        ) from error


def encode_cursor(record: pd.Series, filters_hash: str) -> str:
    """Gera o cursor assinado a partir do último registro da página."""

    def val(x: Any) -> str | None:
        return None if pd.isna(x) else str(x)

    cursor_data = {
        "v": 1,
        "m": val(record["municipio"]),
        "c": val(record["cnae_fiscal_principal"]),
        "b": val(record["cnpj_basico"]),
        "o": val(record["cnpj_ordem"]),
        "d": val(record["cnpj_dv"]),
        "f": filters_hash,
    }

    payload = json.dumps(
        cursor_data,
        separators=(",", ":"),
        sort_keys=True,
    )

    sig = sign_cursor(payload)
    token = f"{payload}|{sig}"

    return base64.urlsafe_b64encode(token.encode("utf-8")).decode("ascii").rstrip("=")


def normalize_records(data: list[dict]) -> list[dict]:
    """Converte valores ausentes do Pandas em None."""
    for item in data:
        for key, value in item.items():
            if pd.isna(value):
                item[key] = None

    return data


def local_partition_missing(uf: str | None) -> bool:
    """Verifica partições locais ausentes sem acessar caminhos S3."""
    if not uf or ESTAB_PATH.startswith("s3://"):
        return False

    partition_path = Path(ESTAB_PATH) / f"uf={uf.upper()}"
    return not partition_path.is_dir()


def build_filters(
    uf: str | None,
    municipio: str | None = None,
    cnae: str | None = None,
    ativa: bool = True,
    com_telefone: bool = False,
    com_email: bool = False,
) -> tuple[list[str], list[str]]:
    """Monta filtros parametrizados para as consultas."""
    clauses = []
    params = []

    if uf:
        clauses.append("est.uf = ?")
        params.append(uf.upper())

    if municipio:
        clauses.append("est.municipio = ?")
        params.append(municipio)

    if cnae:
        clauses.append("est.cnae_fiscal_principal = ?")
        params.append(cnae)

    if ativa:
        clauses.append("est.situacao_cadastral = '02'")

    if com_telefone:
        clauses.append("(est.telefone_1 IS NOT NULL AND est.telefone_1 != '')")

    if com_email:
        clauses.append(
            "(est.correio_eletronico IS NOT NULL AND est.correio_eletronico != '')"
        )

    return clauses, params


def unexpected_database_error(error: Exception) -> HTTPException:
    """Registra um erro interno sem expor detalhes ao cliente."""
    logger.error(
        "Erro ao executar consulta no BuscaFri: %s",
        type(error).__name__,
    )

    return HTTPException(
        status_code=500,
        detail="Erro interno ao processar a consulta",
    )


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
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(
        None,
        description="Cursor para keyset pagination",
    ),
):
    if local_partition_missing(uf):
        return {
            "total_count": 0,
            "page": None if cursor else page,
            "limit": limit,
            "next_cursor": None,
            "data": [],
        }

    estab_path_pattern = build_estab_pattern(uf)
    empresas_pattern = f"{EMPRESAS_PATH.rstrip('/')}/*.parquet"

    base_clauses, base_params = build_filters(
        uf=uf,
        municipio=municipio,
        cnae=cnae,
        ativa=ativa,
        com_telefone=com_telefone,
        com_email=com_email,
    )

    filters_dict = {
        "uf": uf,
        "municipio": municipio,
        "cnae": cnae,
        "ativa": ativa,
        "com_telefone": com_telefone,
        "com_email": com_email,
    }
    filters_hash = generate_filters_hash(filters_dict)

    base_where_sql = " AND ".join(base_clauses) if base_clauses else "1=1"

    page_clauses = list(base_clauses)
    page_params = list(base_params)

    if cursor:
        cursor_data = decode_cursor(cursor, filters_hash)
        predicate, cursor_params = cursor_predicate(cursor_data)
        page_clauses.append(predicate)
        page_params.extend(cursor_params)

    page_where_sql = " AND ".join(page_clauses) if page_clauses else "1=1"

    # O cursor usa uma ordenação determinística pelos cinco campos.
    order_sql = ", ".join(f"est.{column} ASC NULLS LAST" for column in SORT_COLUMNS)

    offset_sql = "" if cursor else "OFFSET ?"
    query_params = list(page_params) + [limit + 1]

    if not cursor:
        query_params.append((page - 1) * limit)

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
            ) AS telefone_1,
            est.cnpj_ordem,
            est.cnpj_dv

        FROM read_parquet(
            {sql_literal(estab_path_pattern)},
            hive_partitioning = true
        ) AS est

        JOIN read_parquet(
            {sql_literal(empresas_pattern)}
        ) AS emp
            ON est.cnpj_basico = emp.cnpj_basico

        WHERE {page_where_sql}

        ORDER BY {order_sql}

        LIMIT ?
        {offset_sql}
    """

    count_sql = f"""
        SELECT COUNT(*) AS total

        FROM read_parquet(
            {sql_literal(estab_path_pattern)},
            hive_partitioning = true
        ) AS est

        WHERE {base_where_sql}
    """

    try:
        results = db_client.query_params(sql, query_params)
        total_df = db_client.query_params(count_sql, base_params)

        total = int(total_df.iloc[0]["total"]) if not total_df.empty else 0

        has_more = len(results) > limit
        page_results = results.iloc[:limit].copy()

        next_cursor = None

        if has_more and not page_results.empty:
            next_cursor = encode_cursor(page_results.iloc[-1], filters_hash)

        # Os campos internos da chave não fazem parte da resposta pública.
        public_results = page_results.drop(
            columns=["cnpj_ordem", "cnpj_dv"],
        )

        data = normalize_records(public_results.to_dict("records"))

        return {
            "total_count": total,
            "page": None if cursor else page,
            "limit": limit,
            "next_cursor": next_cursor,
            "data": data,
        }

    except HTTPException:
        raise
    except (
        duckdb.Error,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        KeyError,
    ) as error:
        raise unexpected_database_error(error) from error


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
    formato = formato.lower()

    if formato not in {"csv", "xlsx"}:
        raise HTTPException(
            status_code=400,
            detail="Formato inválido. Use csv ou xlsx.",
        )

    if local_partition_missing(uf):
        uf_label = uf.upper() if uf else ""
        raise HTTPException(
            status_code=404,
            detail=f"Nenhuma partição encontrada para a UF {uf_label}.",
        )

    estab_path_pattern = build_estab_pattern(uf)
    empresas_pattern = f"{EMPRESAS_PATH.rstrip('/')}/*.parquet"

    clauses, params = build_filters(
        uf=uf,
        ativa=ativa,
        com_telefone=com_telefone,
        com_email=com_email,
    )

    where_sql = " AND ".join(clauses) if clauses else "1=1"

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
            {sql_literal(estab_path_pattern)},
            hive_partitioning = true
        ) AS est

        JOIN read_parquet(
            {sql_literal(empresas_pattern)}
        ) AS emp
            ON est.cnpj_basico = emp.cnpj_basico

        WHERE {where_sql}

        ORDER BY est.municipio, est.cnae_fiscal_principal,
                 est.cnpj_basico, est.cnpj_ordem, est.cnpj_dv

        LIMIT 10000
    """

    try:
        df = db_client.query_params(sql, params)

        if formato == "csv":
            csv_content = df.to_csv(
                index=False,
                sep=";",
            ).encode("utf-8-sig")

            stream = io.BytesIO(csv_content)

            return StreamingResponse(
                stream,
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": ("attachment; filename=buscafri_export.csv")
                },
            )

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
    except (
        duckdb.Error,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        ImportError,
    ) as error:
        raise unexpected_database_error(error) from error
