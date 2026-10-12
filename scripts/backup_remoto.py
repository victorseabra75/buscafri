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


def backup_remoto() -> bool:
    backup_dir = Path("data/backup_remoto")
    expected_records = 70_085_602

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)

        existing_files = list(backup_dir.iterdir())

        if existing_files:
            print(
                "ERRO: O diretório de backup já contém arquivos: "
                f"{[file.name for file in existing_files]}"
            )
            return False

        print("--- INICIANDO BACKUP REMOTO VIA DUCKDB ---")

        total_records = 0
        total_files = 0

        for i in range(10):
            filename = f"Empresas{i}.parquet"
            src = f"s3://buscafri-data/empresas/{filename}"
            dst = backup_dir / filename

            escaped_dst = dst.resolve().as_posix().replace("'", "''")
            escaped_src = src.replace("'", "''")

            print(f"Baixando/exportando {src} -> {dst}...")

            query = (
                "COPY (SELECT * "
                f"FROM read_parquet('{escaped_src}')) "
                f"TO '{escaped_dst}' (FORMAT PARQUET)"
            )

            db_client.query(query)

            if not dst.is_file():
                print(f"ERRO: Falha ao criar o arquivo {dst}")
                return False

            size_bytes = dst.stat().st_size
            sha256 = compute_sha256(dst)

            parquet_path = dst.resolve().as_posix().replace("'", "''")
            count_result = db_client.query(
                f"SELECT COUNT(*) AS total FROM read_parquet('{parquet_path}')"
            )
            count = cast(int, count_result.at[0, "total"])

            total_records += count
            total_files += 1

            print(
                f"  OK: {dst.name}: {count:,} registros | "
                f"{size_bytes:,} bytes | SHA256: {sha256[:12]}..."
            )

        print("\n--- RELATÓRIO FINAL DO BACKUP ---")
        print(f"Total de arquivos baixados: {total_files}")
        print(f"Total de registros validados: {total_records:,}")

        if total_files != 10:
            print(f"ERRO: Esperados 10 arquivos; obtidos {total_files}.")
            return False

        if total_records != expected_records:
            print(
                "ERRO: DIVERGÊNCIA NA CONTAGEM: "
                f"Esperado {expected_records:,}; "
                f"obtido {total_records:,}."
            )
            return False

        print(
            "SUCESSO: Validação de contagem concluída! "
            f"({expected_records:,} registros)"
        )
        return True

    except (
        OSError,
        duckdb.Error,
        RuntimeError,
        ValueError,
        IndexError,
        KeyError,
    ) as error:
        print(f"ERRO durante o backup remoto: {error}")
        return False


if __name__ == "__main__":
    backup_remoto()
