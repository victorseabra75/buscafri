from app.core.database import db_client


def diag():
    local_path = "data/processed_corrigido/empresas/Empresas0.parquet"
    remote_path = "s3://buscafri-data/empresas/Empresas0.parquet"

    print("--- LOCAL ---")
    print(db_client.query(f"DESCRIBE SELECT * FROM '{local_path}'"))
    print(
        "Contagem:", db_client.query(f"SELECT COUNT(*) FROM '{local_path}'").iloc[0, 0]
    )

    print("\n--- REMOTO ---")
    print(db_client.query(f"DESCRIBE SELECT * FROM '{remote_path}'"))
    print(
        "Contagem:", db_client.query(f"SELECT COUNT(*) FROM '{remote_path}'").iloc[0, 0]
    )


if __name__ == "__main__":
    diag()
