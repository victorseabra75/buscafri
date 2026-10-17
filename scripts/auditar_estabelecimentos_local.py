from pathlib import Path

import duckdb


def count_rows(
    con: duckdb.DuckDBPyConnection,
    pattern: str,
) -> int:
    """Conta os registros dos arquivos Parquet de uma partição."""
    result = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [pattern],
    ).fetchone()

    if result is None:
        raise RuntimeError(f"A consulta não retornou resultado para: {pattern}")

    count = result[0]

    if not isinstance(count, int):
        raise TypeError(f"A contagem retornada não é um inteiro: {pattern}")

    return count


def main() -> None:
    path = Path("data/particionado/estabelecimentos")

    if not path.is_dir():
        print(f"Diretório não encontrado: {path}")
        return

    partitions = sorted(folder for folder in path.iterdir() if folder.is_dir())

    print(f"Total partition folders: {len(partitions)}")

    total_rows = 0

    with duckdb.connect() as con:
        for part in partitions:
            files = sorted(part.glob("*.parquet"))

            if not files:
                print(f"{part.name}: nenhum arquivo Parquet encontrado")
                continue

            pattern = (part / "*.parquet").as_posix()

            try:
                count = count_rows(con, pattern)
            except (duckdb.Error, OSError, RuntimeError, TypeError) as e:
                print(f"Erro na partição {part.name}: {e}")
                continue

            total_size = sum(file.stat().st_size for file in files)
            total_rows += count

            print(
                f"{part.name}: {len(files)} files, "
                f"{total_size / 1024 / 1024:.2f} MB, "
                f"{count:,} rows"
            )

    print(f"Total rows across all partitions: {total_rows:,}")


if __name__ == "__main__":
    main()
