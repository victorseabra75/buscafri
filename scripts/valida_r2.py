import os

import duckdb
from dotenv import load_dotenv

BUCKET = "buscafri-data"

MUNICIPIOS_URI = f"s3://{BUCKET}/municipios/Municipios.parquet"
CNAES_URI = f"s3://{BUCKET}/cnaes/Cnaes.parquet"
ESTABELECIMENTOS_AC_URI = f"s3://{BUCKET}/estabelecimentos/uf=AC/data_0.parquet"


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

        # Escapar aspas simples para evitar erros na configuração SQL.
        endpoint = endpoint.replace("'", "''")
        access_key = access_key.replace("'", "''")
        secret_key = secret_key.replace("'", "''")

        conn.execute(f"SET s3_endpoint = '{endpoint}'")
        conn.execute(f"SET s3_access_key_id = '{access_key}'")
        conn.execute(f"SET s3_secret_access_key = '{secret_key}'")
        conn.execute("SET s3_url_style = 'path'")
        conn.execute("SET s3_region = 'auto'")

        return conn

    except Exception:
        conn.close()
        raise


def inspecionar_arquivo(
    conn: duckdb.DuckDBPyConnection,
    titulo: str,
    uri: str,
    mostrar_amostra: bool = False,
) -> None:
    print(f"\n--- {titulo}: esquema ---")

    esquema = conn.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [uri],
    ).df()

    print(esquema)

    print(f"\n--- {titulo}: quantidade de registros ---")

    quantidade = conn.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [uri],
    ).fetchone()

    print(f"Total: {quantidade[0] if quantidade else 'indisponível'}")

    if mostrar_amostra:
        print(f"\n--- {titulo}: amostra ---")

        amostra = conn.execute(
            "SELECT * FROM read_parquet(?) LIMIT 10",
            [uri],
        ).df()

        print(amostra)


def verificar_municipios_ac(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    print("\n--- Códigos de municípios dos estabelecimentos do Acre ---")

    resultado = conn.execute(
        """
        SELECT
            TRIM(CAST(municipio AS VARCHAR)) AS codigo_municipio,
            COUNT(*) AS quantidade
        FROM read_parquet(?)
        GROUP BY 1
        ORDER BY 1
        LIMIT 50
        """,
        [ESTABELECIMENTOS_AC_URI],
    ).df()

    print(resultado)

    print("\n--- Correspondência com a tabela de municípios ---")

    correspondencia = conn.execute(
        """
        WITH municipios_ac AS (
            SELECT DISTINCT
                TRIM(CAST(municipio AS VARCHAR)) AS codigo
            FROM read_parquet(?)
        ),
        referencia AS (
            SELECT DISTINCT
                TRIM(CAST("0" AS VARCHAR)) AS codigo,
                "1" AS nome
            FROM read_parquet(?)
        )
        SELECT
            a.codigo,
            r.nome,
            CASE
                WHEN r.codigo IS NULL THEN 'SEM CORRESPONDÊNCIA'
                ELSE 'ENCONTRADO'
            END AS resultado
        FROM municipios_ac AS a
        LEFT JOIN referencia AS r
            ON a.codigo = r.codigo
        ORDER BY a.codigo
        """,
        [ESTABELECIMENTOS_AC_URI, MUNICIPIOS_URI],
    ).df()

    print(correspondencia.to_string(index=False))

    sem_correspondencia = (correspondencia["resultado"] == "SEM CORRESPONDÊNCIA").sum()

    print(f"\nCódigos sem correspondência exata: {sem_correspondencia}")


def main() -> None:
    conn = configurar_conexao()

    try:
        inspecionar_arquivo(
            conn,
            "Municípios",
            MUNICIPIOS_URI,
            mostrar_amostra=True,
        )

        inspecionar_arquivo(
            conn,
            "CNAEs",
            CNAES_URI,
            mostrar_amostra=True,
        )

        inspecionar_arquivo(
            conn,
            "Estabelecimentos AC",
            ESTABELECIMENTOS_AC_URI,
            mostrar_amostra=True,
        )

        verificar_municipios_ac(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
