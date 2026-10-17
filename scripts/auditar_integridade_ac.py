import os

import duckdb
from dotenv import load_dotenv

BUCKET = "buscafri-data"
ESTAB_AC = f"s3://{BUCKET}/estabelecimentos/uf=AC/data_0.parquet"
MUNICIPIOS = f"s3://{BUCKET}/municipios/Municipios.parquet"
CNAES = f"s3://{BUCKET}/cnaes/Cnaes.parquet"


def configurar_conexao() -> duckdb.DuckDBPyConnection:
    load_dotenv(".env")

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id or not account_id.strip():
        raise RuntimeError("R2_ACCOUNT_ID não configurado no .env.")

    if not access_key or not access_key.strip():
        raise RuntimeError("R2_ACCESS_KEY_ID não configurado no .env.")

    if not secret_key or not secret_key.strip():
        raise RuntimeError("R2_SECRET_ACCESS_KEY não configurado no .env.")

    conn = duckdb.connect(":memory:")

    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        endpoint = f"{account_id}.r2.cloudflarestorage.com"

        # Escapar aspas simples para configurar os valores em SQL.
        endpoint_sql = endpoint.replace("'", "''")
        access_key_sql = access_key.replace("'", "''")
        secret_key_sql = secret_key.replace("'", "''")

        conn.execute(f"SET s3_endpoint = '{endpoint_sql}'")
        conn.execute(f"SET s3_access_key_id = '{access_key_sql}'")
        conn.execute(f"SET s3_secret_access_key = '{secret_key_sql}'")
        conn.execute("SET s3_url_style = 'path'")
        conn.execute("SET s3_region = 'auto'")

        return conn

    except Exception:
        conn.close()
        raise


def auditar_referencia(
    conn: duckdb.DuckDBPyConnection,
    titulo: str,
    coluna_estabelecimento: str,
    uri_referencia: str,
) -> None:
    print(f"\n--- Auditoria de {titulo} (Acre) ---")

    # Os nomes de coluna usados abaixo são constantes internas,
    # não valores recebidos do usuário.
    consulta = f"""
        WITH CodigosEstabelecimentos AS (
            SELECT DISTINCT
                TRIM(CAST({coluna_estabelecimento} AS VARCHAR)) AS codigo
            FROM read_parquet(?)
            WHERE {coluna_estabelecimento} IS NOT NULL
        ),
        Referencias AS (
            SELECT
                TRIM(CAST("0" AS VARCHAR)) AS codigo,
                "1" AS descricao
            FROM read_parquet(?)
        )
        SELECT
            e.codigo AS codigo_estabelecimento,
            r.descricao AS descricao_referencia,
            CASE
                WHEN r.codigo IS NOT NULL THEN 'MATCH'
                ELSE 'MISSING'
            END AS status
        FROM CodigosEstabelecimentos AS e
        LEFT JOIN Referencias AS r
            ON e.codigo = r.codigo
        ORDER BY status, e.codigo
    """

    df = conn.execute(
        consulta,
        [ESTAB_AC, uri_referencia],
    ).df()

    total = len(df)
    matches = int((df["status"] == "MATCH").sum())
    missing = int((df["status"] == "MISSING").sum())

    print(f"Códigos únicos nos estabelecimentos: {total}")
    print(f"Correspondências (MATCH): {matches}")
    print(f"Não correspondidos (MISSING): {missing}")

    if total:
        print(f"Taxa de correspondência: {matches / total:.2%}")

    print("\nExemplos de códigos não correspondidos:")
    print(
        df.loc[
            df["status"] == "MISSING",
            ["codigo_estabelecimento", "descricao_referencia"],
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nExemplos de códigos correspondidos:")
    print(
        df.loc[
            df["status"] == "MATCH",
            ["codigo_estabelecimento", "descricao_referencia"],
        ]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    conn = configurar_conexao()

    try:
        auditar_referencia(
            conn,
            titulo="Municípios",
            coluna_estabelecimento="municipio",
            uri_referencia=MUNICIPIOS,
        )

        auditar_referencia(
            conn,
            titulo="CNAEs",
            coluna_estabelecimento="cnae_fiscal_principal",
            uri_referencia=CNAES,
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()
