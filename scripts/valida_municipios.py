import os

import duckdb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(".env")

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if account_id is None or not account_id.strip():
        raise RuntimeError("R2_ACCOUNT_ID não foi configurado no .env.")

    if access_key is None or not access_key.strip():
        raise RuntimeError("R2_ACCESS_KEY_ID não foi configurado no .env.")

    if secret_key is None or not secret_key.strip():
        raise RuntimeError("R2_SECRET_ACCESS_KEY não foi configurado no .env.")

    endpoint = f"{account_id}.r2.cloudflarestorage.com"
    conn = duckdb.connect(":memory:")

    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        # Escapar aspas simples nos valores usados no SQL.
        endpoint_sql = endpoint.replace("'", "''")
        access_key_sql = access_key.replace("'", "''")
        secret_key_sql = secret_key.replace("'", "''")

        conn.execute(f"SET s3_endpoint = '{endpoint_sql}'")
        conn.execute(f"SET s3_access_key_id = '{access_key_sql}'")
        conn.execute(f"SET s3_secret_access_key = '{secret_key_sql}'")
        conn.execute("SET s3_url_style = 'path'")
        conn.execute("SET s3_region = 'auto'")

        print("\n--- Municípios: amostra geral ---")

        resultado = conn.execute(
            """
            SELECT *
            FROM read_parquet(
                's3://buscafri-data/municipios/Municipios.parquet'
            )
            LIMIT 50
            """
        ).df()

        print(resultado)
        print("\nColunas encontradas:")
        print(resultado.columns.tolist())

    except duckdb.Error as erro:
        print(f"Erro do DuckDB: {erro}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()
