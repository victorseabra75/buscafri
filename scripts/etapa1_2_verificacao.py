import hashlib
from pathlib import Path
from typing import cast

import duckdb

from app.core.database import db_client


def compute_sha256(filepath: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo."""
    sha256_hash = hashlib.sha256()

    with filepath.open("rb") as file:
        for byte_block in iter(lambda: file.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def count_parquet_records(filepath: Path) -> int:
    """Conta os registros de um arquivo Parquet usando DuckDB."""
    parquet_path = filepath.as_posix().replace("'", "''")

    result = db_client.query(
        f"SELECT COUNT(*) AS total FROM read_parquet('{parquet_path}')"
    )

    return cast(int, result.at[0, "total"])


def verify_local_files() -> bool:
    backup_dir = Path("data/backup_remoto")
    rebuild_dir = Path("data/rebuild/empresas")

    expected_backup_records = 70_085_602
    expected_rebuild_records = 70_085_592

    backup_files = [f"Empresas{i}.parquet" for i in range(10)]
    rebuild_files = [f"Empresas{i}.parquet" for i in range(10)]

    print("--- 1. CONFIRMAÇÃO DO BACKUP (data/backup_remoto) ---")

    total_backup_records = 0

    try:
        for fname in backup_files:
            filepath = backup_dir / fname

            if not filepath.is_file():
                print(f"ERRO: Arquivo de backup não encontrado: {filepath}")
                return False

            size = filepath.stat().st_size
            sha = compute_sha256(filepath)
            count = count_parquet_records(filepath)

            total_backup_records += count

            print(
                f"  Backup {fname}: {count:,} registros | "
                f"{size:,} bytes | SHA256: {sha[:12]}..."
            )

        print(
            f"Total de registros do backup: {total_backup_records:,} "
            f"(Esperado: {expected_backup_records:,})"
        )

        print(
            "\n--- 2. CONFIRMAÇÃO DOS ARQUIVOS CORRIGIDOS (data/rebuild/empresas) ---"
        )

        total_rebuild_records = 0

        for fname in rebuild_files:
            filepath = rebuild_dir / fname

            if not filepath.is_file():
                print(f"ERRO: Arquivo reconstruído não encontrado: {filepath}")
                return False

            size = filepath.stat().st_size
            sha = compute_sha256(filepath)
            count = count_parquet_records(filepath)

            total_rebuild_records += count

            print(
                f"  Rebuild {fname}: {count:,} registros | "
                f"{size:,} bytes | SHA256: {sha[:12]}..."
            )

        print(
            f"Total de registros reconstruídos: {total_rebuild_records:,} "
            f"(Esperado: {expected_rebuild_records:,})"
        )

    except (
        OSError,
        duckdb.Error,
        RuntimeError,
        ValueError,
        IndexError,
        KeyError,
    ) as error:
        print(f"ERRO durante a verificação dos arquivos: {error}")
        return False

    if total_backup_records != expected_backup_records:
        print(
            "ERRO: Total de registros do backup divergente! "
            f"Esperado: {expected_backup_records:,}; "
            f"encontrado: {total_backup_records:,}."
        )
        return False

    if total_rebuild_records != expected_rebuild_records:
        print(
            "ERRO: Total de registros reconstruídos divergente! "
            f"Esperado: {expected_rebuild_records:,}; "
            f"encontrado: {total_rebuild_records:,}."
        )
        return False

    print("\nSUCESSO: Os arquivos locais passaram na validação de contagem.")
    return True


if __name__ == "__main__":
    verify_local_files()
