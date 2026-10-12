from pathlib import Path
from typing import cast

from app.core.database import db_client


def verify_source() -> None:
    base_dir = Path("data/processed_corrigido/empresas")
    files = [base_dir / f"Empresas{i}.parquet" for i in range(10)]

    print(f"--- VERIFICAÇÃO DA FONTE LOCAL ({base_dir}) ---")

    total_count: int = 0

    for file_path in files:
        if not file_path.is_file():
            print(f"ERRO: Arquivo não encontrado: {file_path}")
            continue

        parquet_path = file_path.as_posix().replace("'", "''")

        try:
            count_result = db_client.query(
                f"SELECT COUNT(*) AS total FROM read_parquet('{parquet_path}')"
            )

            count_value = cast(int, count_result.at[0, "total"])
            total_count += count_value

            schema = db_client.query(
                f"DESCRIBE SELECT * FROM read_parquet('{parquet_path}')"
            )

            columns: list[str] = schema["column_name"].tolist()

            print(f"{file_path}: {count_value:,} registros | Colunas: {columns}")

            if count_value > 0:
                sample = db_client.query(
                    f"SELECT * FROM read_parquet('{parquet_path}') LIMIT 1"
                )
                print(f"   Amostra: {sample.iloc[0].tolist()}")
            else:
                print("   Arquivo vazio.")

        except (RuntimeError, TypeError, ValueError, IndexError) as error:
            print(f"ERRO ao verificar {file_path}: {error}")

    print(f"\nTOTAL LOCAL: {total_count:,} registros")


if __name__ == "__main__":
    verify_source()
