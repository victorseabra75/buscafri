import duckdb


def check_nulls() -> None:
    path = "data/particionado/estabelecimentos/uf=BA/*.parquet"
    conn = duckdb.connect(":memory:")

    try:
        res = conn.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE municipio IS NULL
                OR cnae_fiscal_principal IS NULL
                OR cnpj_basico IS NULL
                OR cnpj_ordem IS NULL
                OR cnpj_dv IS NULL
            """,
            [path],
        ).fetchone()

        if res is None:
            raise RuntimeError("A consulta de valores nulos não retornou resultado.")

        null_count = res[0]

        if not isinstance(null_count, int):
            raise TypeError("A contagem de valores nulos não é um inteiro.")

        print(f"Nulls in BA: {null_count}")

        schema = conn.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [path],
        ).df()

        print("\nSchema:")
        print(schema[["column_name", "column_type"]])

        sample = conn.execute(
            """
            SELECT
                municipio,
                cnae_fiscal_principal,
                cnpj_basico,
                cnpj_ordem,
                cnpj_dv
            FROM read_parquet(?)
            LIMIT 5
            """,
            [path],
        ).df()

        print("\nSample:")
        print(sample)

    except duckdb.Error as e:
        print(f"Erro do DuckDB: {e}")
    except OSError as e:
        print(f"Erro de acesso aos arquivos: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    check_nulls()
