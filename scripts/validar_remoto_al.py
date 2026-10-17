import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv


def configurar_duckdb() -> duckdb.DuckDBPyConnection:
    """Configura uma conexão DuckDB com o Cloudflare R2."""

    load_dotenv(Path(".env"))

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id:
        raise ValueError("R2_ACCOUNT_ID não está configurado no .env.")

    if not access_key:
        raise ValueError("R2_ACCESS_KEY_ID não está configurado no .env.")

    if not secret_key:
        raise ValueError("R2_SECRET_ACCESS_KEY não está configurado no .env.")

    endpoint = (
        os.getenv(
            "R2_ENDPOINT",
            f"{account_id}.r2.cloudflarestorage.com",
        )
        .strip()
        .rstrip("/")
    )

    # Remove o protocolo se o endpoint tiver sido configurado com URL.
    endpoint = endpoint.removeprefix("https://")
    endpoint = endpoint.removeprefix("http://")

    conn = duckdb.connect(database=":memory:")

    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        configuracoes = {
            "s3_endpoint": endpoint,
            "s3_access_key_id": access_key,
            "s3_secret_access_key": secret_key,
            "s3_url_style": "path",
            "s3_region": "auto",
        }

        for nome, valor in configuracoes.items():
            valor_sql = valor.replace("'", "''")
            conn.execute(f"SET {nome} = '{valor_sql}'")

    except duckdb.Error:
        conn.close()
        raise

    return conn


def main() -> int:
    remote_path = "s3://buscafri-data/estabelecimentos/uf=AL/data_0.parquet"

    conn: duckdb.DuckDBPyConnection | None = None

    try:
        conn = configurar_duckdb()

        print("--- Validação Remota Alagoas (Pós-Upload) ---")

        # 1. Inspecionar o esquema sem carregar todas as linhas.
        esquema = conn.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [remote_path],
        ).fetchall()

        colunas = [linha[0] for linha in esquema]

        print(f"Colunas: {colunas}")

        # 2. Contar os registros do arquivo remoto.
        resultado = conn.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [remote_path],
        ).fetchone()

        if resultado is None:
            raise RuntimeError("A consulta de contagem não retornou resultado.")

        total_linhas = int(resultado[0])
        print(f"Linhas: {total_linhas:,}")

        # 3. Verificar se as colunas necessárias existem.
        sort_cols = [
            "municipio",
            "cnae_fiscal_principal",
            "cnpj_basico",
            "cnpj_ordem",
            "cnpj_dv",
        ]

        colunas_ausentes = [coluna for coluna in sort_cols if coluna not in colunas]

        if colunas_ausentes:
            raise ValueError(
                f"Colunas necessárias à validação ausentes: {colunas_ausentes}"
            )

        if "situacao_cadastral" not in colunas:
            raise ValueError("A coluna situacao_cadastral não existe no Parquet.")

        # 4. Mostrar os primeiros cinco registros na ordem armazenada.
        colunas_sql = ", ".join(f'"{coluna}"' for coluna in sort_cols)

        print("\nAmostra da ordenação (Remoto):")

        amostra = conn.execute(
            f"""
            SELECT {colunas_sql}
            FROM read_parquet(?)
            LIMIT 5
            """,
            [remote_path],
        ).df()

        print(amostra.to_string(index=False))

        # 5. Contar empresas com situação cadastral ativa.
        # LPAD também trata códigos numéricos como 2, convertendo-os
        # para "02", sem alterar códigos que já sejam "02".

        print("\nTeste funcional (Count Ativas em AL):")

        resultado_ativas = conn.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE LPAD(
                TRIM(CAST(situacao_cadastral AS VARCHAR)),
                2,
                '0'
            ) = '02'
            """,
            [remote_path],
        ).fetchone()

        if resultado_ativas is None:
            raise RuntimeError("A consulta de empresas ativas não retornou resultado.")

        count_ativas = int(resultado_ativas[0])

        print(f"Total de registros ativos em AL: {count_ativas:,}")

        print("\nValidação remota concluída.")

        return 0

    except (
        duckdb.Error,
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
    ) as erro:
        print(
            f"\nERRO: {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
