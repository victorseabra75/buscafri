import sys
from pathlib import Path

import duckdb

from scripts.validar_reordenacao_r2 import validate_integrity

ORIGINAL_BASE = Path("data/particionado/estabelecimentos")
REORDERED_BASE = Path("data/reordenado/estabelecimentos")


def count_rows(
    con: duckdb.DuckDBPyConnection,
    files: list[Path],
) -> int:
    """Conta os registros de um conjunto de arquivos Parquet."""
    if not files:
        raise FileNotFoundError("Nenhum arquivo Parquet encontrado.")

    paths = [str(file.resolve()) for file in files]

    result = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [paths],
    ).fetchone()

    if result is None:
        raise RuntimeError("A consulta de contagem não retornou resultado.")

    count = result[0]

    if not isinstance(count, int):
        raise TypeError("A contagem retornada não é um inteiro.")

    return count


def main() -> int:
    if not ORIGINAL_BASE.is_dir():
        print(f"Diretório de origem não encontrado: {ORIGINAL_BASE}")
        return 1

    if not REORDERED_BASE.is_dir():
        print(f"Diretório reordenado não encontrado: {REORDERED_BASE}")
        return 1

    partitions = sorted(
        directory.name
        for directory in ORIGINAL_BASE.iterdir()
        if directory.is_dir() and directory.name.startswith("uf=")
    )

    print(f"Total de partições para auditoria: {len(partitions)}")
    print(
        f"{'UF':<8} | {'Reg. Origem':>12} | {'Reg. Novo':>12} | "
        f"{'Integridade':<12} | {'Status':<10}"
    )
    print("-" * 68)

    all_passed = True
    total_original = 0
    total_reordered = 0

    with duckdb.connect() as con:
        for partition in partitions:
            original_dir = ORIGINAL_BASE / partition
            reordered_dir = REORDERED_BASE / partition

            original_files = sorted(original_dir.glob("*.parquet"))
            reordered_files = sorted(reordered_dir.glob("*.parquet"))

            if not original_files or not reordered_files:
                print(f"{partition:<8} | Arquivos Parquet ausentes")
                all_passed = False
                continue

            try:
                original_count = count_rows(con, original_files)
                reordered_count = count_rows(con, reordered_files)
            except (
                duckdb.Error,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    f"{partition:<8} | Erro na contagem: "
                    f"{type(error).__name__}: {error}"
                )
                all_passed = False
                continue

            total_original += original_count
            total_reordered += reordered_count

            if original_count != reordered_count:
                print(
                    f"{partition:<8} | {original_count:>12,} | "
                    f"{reordered_count:>12,} | DIVERGENTE    | FALHA"
                )
                all_passed = False
                continue

            # A função de integridade deve comparar o conteúdo
            # da origem com o conteúdo reordenado e validar a
            # ordenação do arquivo reordenado.
            try:
                integrity_passed = validate_integrity(
                    str(original_dir / "*.parquet"),
                    str(reordered_dir / "*.parquet"),
                )
            except (
                duckdb.Error,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as error:
                print(
                    f"{partition:<8} | {original_count:>12,} | "
                    f"{reordered_count:>12,} | ERRO          | FALHA"
                )
                print(f"  Detalhe: {type(error).__name__}: {error}")
                all_passed = False
                continue

            status = "APROVADO" if integrity_passed else "FALHA"
            integrity = "IGUAL" if integrity_passed else "DIVERGENTE"

            print(
                f"{partition:<8} | {original_count:>12,} | "
                f"{reordered_count:>12,} | {integrity:<12} | {status}"
            )

            if not integrity_passed:
                all_passed = False

    print("-" * 68)
    print(f"Total de registros na origem:      {total_original:,}")
    print(f"Total de registros reordenados:     {total_reordered:,}")
    print(f"Status geral: {'APROVADO' if all_passed else 'REPROVADO'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
