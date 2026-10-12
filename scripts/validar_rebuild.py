from pathlib import Path
from typing import cast

from app.core.database import db_client


def validate_rebuild() -> None:
    src_dir = Path("data/processed_corrigido/empresas")
    dst_dir = Path("data/rebuild/empresas")

    print("--- RELATÓRIO DE VALIDAÇÃO ---")

    total_src: int = 0
    total_dst: int = 0

    for i in range(10):
        src = src_dir / f"Empresas{i}.parquet"
        dst = dst_dir / f"Empresas{i}.parquet"

        if not src.is_file():
            print(f"FALHA: Arquivo de origem não encontrado: {src}")
            return

        if not dst.is_file():
            print(f"FALHA: Arquivo reconstruído não encontrado: {dst}")
            return

        src_path = src.as_posix().replace("'", "''")
        dst_path = dst.as_posix().replace("'", "''")

        try:
            # Contagem de registros
            result_src = db_client.query(
                f"SELECT COUNT(*) AS total FROM read_parquet('{src_path}')"
            )
            result_dst = db_client.query(
                f"SELECT COUNT(*) AS total FROM read_parquet('{dst_path}')"
            )

            c_src = cast(int, result_src.at[0, "total"])
            c_dst = cast(int, result_dst.at[0, "total"])

            total_src += c_src
            total_dst += c_dst

            # Amostra de capital social para validar os dados
            s_src = db_client.query(
                f"SELECT capital_social FROM read_parquet('{src_path}') LIMIT 5"
            )
            s_dst = db_client.query(
                f"SELECT capital_social FROM read_parquet('{dst_path}') LIMIT 5"
            )

            # Comparação de contagens
            if c_src != c_dst:
                print(
                    f"FALHA: Divergência de contagem no arquivo {i}. "
                    f"Origem: {c_src}, reconstruído: {c_dst}"
                )
                return

            print(f"Arquivo {i}: OK ({c_dst:,} registros)")

            # Comparação da amostra
            if not s_src.equals(s_dst):
                print(f"AVISO: Amostras de capital_social diferentes no arquivo {i}.")

        except (RuntimeError, ValueError, IndexError, TypeError) as error:
            print(f"ERRO ao validar o arquivo {i}: {error}")
            return

    if total_src == total_dst == 70_085_592:
        print(f"\nTOTAL VALIDADO: {total_dst:,} registros")
    else:
        print(
            f"\nFALHA: Total divergente. "
            f"Origem: {total_src:,} | Reconstruído: {total_dst:,}"
        )


if __name__ == "__main__":
    validate_rebuild()
