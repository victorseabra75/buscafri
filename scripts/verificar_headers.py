import duckdb

from app.core.database import db_client


def check_headers() -> None:
    files = [f"s3://buscafri-data/empresas/Empresas{i}.parquet" for i in range(10)]

    expected_header = [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte_empresa",
        "ente_federativo_responsavel",
    ]

    print("--- VERIFICAÇÃO DE CABEÇALHOS NO R2 ---")

    for filepath in files:
        try:
            schema = db_client.query(
                f"DESCRIBE SELECT * FROM read_parquet('{filepath}')"
            )

            columns: list[str] = schema["column_name"].tolist()
            match = columns == expected_header

            sample = db_client.query(
                f"SELECT * FROM read_parquet('{filepath}') LIMIT 1"
            )

            row_str = (
                [str(value).strip() for value in sample.iloc[0].tolist()]
                if not sample.empty
                else []
            )

            print(f"{filepath}: match={match}, colunas={columns}, amostra={row_str}")

            if not match:
                print(f"  ERRO: Cabeçalho esperado: {expected_header}")

        except (duckdb.Error, RuntimeError, ValueError, KeyError, IndexError) as error:
            print(f"{filepath}: Erro: {error}")


if __name__ == "__main__":
    check_headers()
