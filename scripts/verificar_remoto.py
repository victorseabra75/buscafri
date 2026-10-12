import duckdb

from app.core.database import db_client


def check_remote() -> None:
    print("--- VERIFICAÇÃO DE ACESSO REMOTO ---")

    path = "s3://buscafri-data/empresas/*.parquet"

    try:
        count = db_client.query(f"SELECT COUNT(*) FROM read_parquet('{path}')").iloc[
            0, 0
        ]
        print(f"Total de registros na tabela oficial: {count}")

    except duckdb.Error as e:
        print(f"Erro ao consultar a tabela oficial: {e}")
        return

    path_v2 = "s3://buscafri-data/empresas-v2/*.parquet"

    try:
        count_v2 = db_client.query(
            f"SELECT COUNT(*) FROM read_parquet('{path_v2}')"
        ).iloc[0, 0]
        print(f"Total de registros na tabela staging (v2): {count_v2}")

    except duckdb.Error as e:
        print(f"Prefix 'empresas-v2' vazio ou inacessível: {e}")


if __name__ == "__main__":
    check_remote()
