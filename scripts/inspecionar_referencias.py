import os
import sys

import duckdb
from dotenv import load_dotenv


def configurar_duckdb() -> duckdb.DuckDBPyConnection:
    """Configura uma conexão DuckDB para acessar arquivos Parquet no R2."""
    load_dotenv()

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    endpoint_env = os.getenv("R2_ENDPOINT")

    if not all((account_id, access_key, secret_key)):
        raise RuntimeError(
            "Credenciais ausentes. Verifique R2_ACCOUNT_ID, "
            "R2_ACCESS_KEY_ID e R2_SECRET_ACCESS_KEY no arquivo .env."
        )

    endpoint = endpoint_env or f"https://{account_id}.r2.cloudflarestorage.com"
    endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")

    con = duckdb.connect(database=":memory:")

    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")

        # Usa parâmetros para evitar problemas com aspas nos valores.
        configuracoes = {
            "s3_endpoint": endpoint,
            "s3_access_key_id": access_key,
            "s3_secret_access_key": secret_key,
            "s3_url_style": "path",
            "s3_region": "auto",
        }

        for chave, valor in configuracoes.items():
            con.execute(
                f"SET {chave} = ?",
                [valor],
            )

    except duckdb.Error as error:
        con.close()
        raise RuntimeError(
            f"Falha ao configurar o DuckDB para o R2: {error}"
        ) from error

    return con


def inspecionar_arquivo(
    con: duckdb.DuckDBPyConnection,
    titulo: str,
    caminho: str,
) -> None:
    """Exibe esquema, quantidade de registros e amostra de um Parquet."""
    print(f"\n=== {titulo} ===")
    print(f"Arquivo: {caminho}")

    try:
        # O caminho é uma constante interna deste script, não entrada externa.
        schema = con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{caminho}')"
        ).fetchall()

        print("\nEsquema:")
        for coluna in schema:
            print(coluna)

        resultado = con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{caminho}')"
        ).fetchone()

        if resultado is None:
            raise RuntimeError("A consulta COUNT(*) não retornou resultado.")

        print(f"\nTotal de registros: {resultado[0]}")

        amostra = con.execute(
            f"SELECT * FROM read_parquet('{caminho}') LIMIT 5"
        ).fetchall()

        print("\nAmostra:")
        for linha in amostra:
            print(linha)

    except duckdb.Error as error:
        raise RuntimeError(
            f"Falha ao consultar {titulo} em {caminho}: {error}"
        ) from error


def main() -> int:
    con = None

    try:
        con = configurar_duckdb()

        inspecionar_arquivo(
            con,
            "MUNICÍPIOS",
            "s3://buscafri-data/municipios/Municipios.parquet",
        )

        inspecionar_arquivo(
            con,
            "CNAES",
            "s3://buscafri-data/cnaes/Cnaes.parquet",
        )

        return 0

    except (RuntimeError, OSError, duckdb.Error) as error:
        print(f"\nERRO: {error}", file=sys.stderr)
        return 1

    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    sys.exit(main())
