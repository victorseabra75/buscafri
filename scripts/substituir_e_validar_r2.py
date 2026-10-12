from pathlib import Path
from typing import cast

import duckdb

from app.core.database import db_client


def replace_and_validate_r2() -> bool:
    rebuild_dir = Path("data/rebuild/empresas")
    expected_total = 70_085_592

    expected_cols = [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte_empresa",
        "ente_federativo_responsavel",
    ]

    print("\n--- 3 & 4. UPLOAD DOS ARQUIVOS CORRIGIDOS VIA DUCKDB (COPY TO S3) ---")

    for i in range(10):
        fname = f"Empresas{i}.parquet"
        local_file = rebuild_dir / fname

        if not local_file.is_file():
            print(f"ERRO: Arquivo local não encontrado: {local_file}")
            return False

        local_path = local_file.as_posix().replace("'", "''")
        remote_path = f"s3://buscafri-data/empresas/{fname}"
        escaped_remote_path = remote_path.replace("'", "''")

        print(f"Substituindo {remote_path} com {local_file}...")

        try:
            query = (
                f"COPY (SELECT * FROM read_parquet('{local_path}')) "
                f"TO '{escaped_remote_path}' (FORMAT PARQUET)"
            )
            db_client.query(query)
            print(f"  OK: {fname} enviado com sucesso.")

        except (duckdb.Error, RuntimeError, ValueError) as error:
            print(f"ERRO ao enviar {fname}: {error}")
            return False

    print("\n--- 5. VALIDAÇÃO DOS DADOS REMOTOS NO R2 ---")

    remote_pattern = "s3://buscafri-data/empresas/*.parquet"

    try:
        # 5.1 Total de registros
        total_result = db_client.query(
            f"SELECT COUNT(*) AS total FROM read_parquet('{remote_pattern}')"
        )
        total_remote = cast(int, total_result.at[0, "total"])

        print(f"Total de registros remotos: {total_remote:,}")

        if total_remote != expected_total:
            print(
                "ERRO CRÍTICO: Total de registros remotos divergente! "
                f"Esperado: {expected_total:,}; recebido: {total_remote:,}"
            )
            return False

        # 5.2 Esquema
        schema_df = db_client.query(
            f"DESCRIBE SELECT * FROM read_parquet('{remote_pattern}')"
        )

        cols: list[str] = schema_df["column_name"].tolist()
        types: list[str] = schema_df["column_type"].tolist()

        print("Esquema remoto:")
        for column, column_type in zip(cols, types, strict=True):
            print(f"  - {column}: {column_type}")

        if cols != expected_cols:
            print("ERRO CRÍTICO: Nomes ou ordem das colunas incorretos!")
            print(f"Esperado: {expected_cols}")
            print(f"Recebido: {cols}")
            return False

        # 5.3 Ausência de cabeçalho residual
        header_result = db_client.query(
            "SELECT COUNT(*) AS total "
            f"FROM read_parquet('{remote_pattern}') "
            "WHERE cnpj_basico = 'cnpj_basico'"
        )
        header_count = cast(int, header_result.at[0, "total"])

        print(f"Registros contendo 'cnpj_basico' como dado: {header_count}")

        if header_count != 0:
            print("ERRO CRÍTICO: Cabeçalho residual encontrado!")
            return False

        # 5.4 Contagem individual por arquivo
        print("\nContagem por arquivo remoto:")

        for i in range(10):
            fname = f"Empresas{i}.parquet"
            remote_file = f"s3://buscafri-data/empresas/{fname}"

            count_result = db_client.query(
                f"SELECT COUNT(*) AS total FROM read_parquet('{remote_file}')"
            )
            count = cast(int, count_result.at[0, "total"])

            print(f"  {fname}: {count:,} registros")

        # 5.5 Teste de JOIN com estabelecimentos
        print("\n--- 6. TESTE DE JOIN COM ESTABELECIMENTOS ---")

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
                's3://buscafri-data/estabelecimentos/*.parquet'
            ) AS est
                ON emp.cnpj_basico = est.cnpj_basico
            LIMIT 3
        """

        join_result = db_client.query(join_query)

        print("Resultado do JOIN (amostra de 3 linhas):")
        print(join_result.to_string())
        print("\nJOIN executado com sucesso!")

    except (duckdb.Error, RuntimeError, ValueError, IndexError) as error:
        print(f"ERRO durante a validação remota: {error}")
        return False

    print("\nSUBSTITUIÇÃO E VALIDAÇÃO NO R2 CONCLUÍDAS COM SUCESSO!")
    return True


if __name__ == "__main__":
    replace_and_validate_r2()
