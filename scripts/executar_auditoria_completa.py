import argparse
import sys
from pathlib import Path

import duckdb

# Define a raiz do projeto independentemente do diretório de execução.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validar_reordenacao_r2 import validate_integrity

original_base = PROJECT_ROOT / "data/particionado/estabelecimentos"
reordered_base = PROJECT_ROOT / "data/reordenado/estabelecimentos"


def parquet_files(directory: Path) -> list[Path]:
    """Retorna todos os arquivos Parquet de um diretório."""
    if not directory.is_dir():
        return []

    return sorted(
        path.resolve() for path in directory.glob("*.parquet") if path.is_file()
    )


def count_rows(con: duckdb.DuckDBPyConnection, files: list[Path]) -> int:
    """Conta os registros de um ou mais arquivos Parquet."""
    if not files:
        raise FileNotFoundError("Nenhum arquivo Parquet encontrado.")

    paths = [path.as_posix() for path in files]

    result = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [paths],
    ).fetchone()

    if result is None:
        raise RuntimeError("O DuckDB não retornou o resultado da contagem.")

    return int(result[0])


if not original_base.is_dir():
    raise FileNotFoundError(f"Diretório de origem não encontrado: {original_base}")

# CHAMADA DA FUNÇÃO DE PARSER DE ARGUMENTOS
parser = argparse.ArgumentParser(
    description="Audita a integridade das partições Parquet."
)
parser.add_argument(
    "--uf",
    nargs="+",
    type=str.upper,
    help="Audita uma ou mais UFs. Exemplo: --uf SP TO RS SC",
)
args = parser.parse_args()

# Lista todas as partições disponíveis no diretório original.
partitions = sorted(
    directory.name
    for directory in original_base.iterdir()
    if directory.is_dir() and directory.name.startswith("uf=")
)

# Se o usuário especificou uma UF, filtra a lista de partições.
if args.uf:
    selected_partitions = {f"uf={uf}" for uf in args.uf}
    missing = selected_partitions - set(partitions)

    if missing:
        parser.error(f"Partições não encontradas: {', '.join(sorted(missing))}")

    partitions = [
        partition for partition in partitions if partition in selected_partitions
    ]


print(f"Total de partições para auditoria: {len(partitions)}")
print(
    f"{'UF':<5} | {'Reg. Origem':<11} | {'Reg. Novo':<11} | "
    f"{'Integridade':<11} | {'Status':<10}"
)
print("-" * 65)

all_passed = True
total_orig = 0
total_novo = 0

with duckdb.connect() as con:
    for part in partitions:
        original_dir = original_base / part
        reordered_dir = reordered_base / part

        orig_files = parquet_files(original_dir)
        new_files = parquet_files(reordered_dir)

        uf = part.removeprefix("uf=")

        try:
            if not orig_files:
                raise FileNotFoundError(f"Nenhum Parquet na origem: {original_dir}")

            if not new_files:
                raise FileNotFoundError(f"Nenhum Parquet reordenado: {reordered_dir}")

            orig_count = count_rows(con, orig_files)
            new_count = count_rows(con, new_files)

            total_orig += orig_count
            total_novo += new_count

            # Passa padrões para permitir a leitura de múltiplos arquivos.
            original_pattern = (original_dir / "*.parquet").as_posix()
            reordered_pattern = (reordered_dir / "*.parquet").as_posix()

            # Confirme que validate_integrity aceita padrões glob.
            integrity_ok = validate_integrity(
                original_pattern,
                reordered_pattern,
            )

            counts_match = orig_count == new_count
            passed = counts_match and integrity_ok

            if not passed:
                all_passed = False

            integrity_status = "OK" if integrity_ok else "FALHA"
            status = "APROVADO" if passed else "FALHA"

            print(
                f"{uf:<5} | {orig_count:<11,d} | {new_count:<11,d} | "
                f"{integrity_status:<11} | {status:<10}"
            )

        except (
            duckdb.Error,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            all_passed = False
            print(
                f"{uf:<5} | {'-':<11} | {'-':<11} | "
                f"{'ERRO':<11} | {type(error).__name__}"
            )
            print(f"       Detalhe: {error}")

print("-" * 65)
print(f"Total geral: Origem = {total_orig:,} | Reordenado = {total_novo:,}")
print(f"Resultado geral: {'APROVADO' if all_passed else 'FALHA'}")

if not all_passed:
    sys.exit(1)
