import duckdb

from app.core.database import db_client


def check_join() -> bool:
    print("--- TESTE DE CONSULTA DE JOIN COM ESTABELECIMENTOS ---")

    try:
        query_estab = """
            SELECT COUNT(*) AS total
            FROM read_parquet(
                's3://buscafri-data/estabelecimentos/uf=SP/*.parquet'
            )
        """

        cnt_sp = db_client.query(query_estab).at[0, "total"]
        print(f"Estabelecimentos UF=SP encontrados: {cnt_sp:,} registros.")

        join_query = """
            SELECT
                emp.cnpj_basico,
                emp.razao_social,
                est.nome_fantasia,
                est.uf
            FROM read_parquet(
                's3://buscafri-data/empresas/*.parquet'
            ) AS emp
            JOIN read_parquet(
                's3://buscafri-data/estabelecimentos/uf=SP/*.parquet'
            ) AS est
                ON emp.cnpj_basico = est.cnpj_basico
            LIMIT 3
        """

        result = db_client.query(join_query)

        print("\nResultado do JOIN com estabelecimentos de SP:")
        print(result.to_string(index=False))

        if result.empty:
            print("\nAVISO: O JOIN foi executado, mas não retornou registros.")
            return False

        print("\nOK: JOIN executado com sucesso!")
        return True

    except (
        duckdb.Error,
        RuntimeError,
        OSError,
        ValueError,
        KeyError,
        IndexError,
    ) as error:
        print(f"Erro no teste de JOIN: {error}")
        return False


if __name__ == "__main__":
    check_join()
