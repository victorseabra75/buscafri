import os
import sys

import duckdb
from dotenv import load_dotenv


def configurar_conexao() -> duckdb.DuckDBPyConnection:
    """Configura o DuckDB para acessar os arquivos Parquet no R2."""
    load_dotenv(".env")

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not all((account_id, access_key, secret_key)):
        raise RuntimeError(
            "Credenciais ausentes no .env. Verifique "
            "R2_ACCOUNT_ID, R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY."
        )

    endpoint = f"{account_id}.r2.cloudflarestorage.com"

    conn = duckdb.connect(":memory:")

    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        conn.execute("SET s3_endpoint = ?", [endpoint])
        conn.execute("SET s3_access_key_id = ?", [access_key])
        conn.execute("SET s3_secret_access_key = ?", [secret_key])
        conn.execute("SET s3_url_style = 'path'")
        conn.execute("SET s3_region = 'auto'")

        return conn

    except duckdb.Error:
        conn.close()
        raise


def consultar_municipios(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Consulta uma amostra de municípios com código 12."""
    arquivo = "s3://buscafri-data/municipios/Municipios.parquet"

    print("\n--- MUNICÍPIOS AC (AMOSTRA) ---")

    try:
        # TRY_CAST permite comparar códigos numéricos com 12.
        resultado = conn.execute(
            f"""
            SELECT *
            FROM read_parquet('{arquivo}')
            WHERE TRY_CAST("0" AS INTEGER) = ?
            LIMIT 10
            """,
            [12],
        )

        print(resultado.df())

    except duckdb.Error as error:
        print(f"Erro na consulta de municípios: {error}")
        raise


def consultar_cnaes(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Exibe uma amostra dos CNAEs."""
    arquivo = "s3://buscafri-data/cnaes/Cnaes.parquet"

    print("\n--- CNAES (AMOSTRA) ---")

    try:
        resultado = conn.execute(
            f"""
            SELECT *
            FROM read_parquet('{arquivo}')
            LIMIT 10
            """
        )

        print(resultado.df())

    except duckdb.Error as error:
        print(f"Erro na consulta de CNAEs: {error}")
        raise


def main() -> int:
    conn = None

    try:
        conn = configurar_conexao()
        consultar_municipios(conn)
        consultar_cnaes(conn)
        return 0

    except (RuntimeError, OSError, duckdb.Error) as error:
        print(f"\nFalha na execução: {error}", file=sys.stderr)
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
