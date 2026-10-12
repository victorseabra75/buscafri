import os

from app.core.database import db_client


def rebuild_files():
    source_dir = "data/processed_corrigido/empresas"
    target_dir = "data/rebuild/empresas"

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    elif os.listdir(target_dir):
        print(f"ERRO: Diretório {target_dir} já existe e não está vazio.")
        return

    cols = [
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte_empresa",
        "ente_federativo_responsavel",
    ]
    col_query = ", ".join([f'"{c}"' for c in cols])

    print("--- RECONSTRUÇÃO EM STAGING ---")

    for i in range(10):
        src = f"{source_dir}/Empresas{i}.parquet"
        dst = f"{target_dir}/Empresas{i}.parquet"

        print(f"Processando {src} -> {dst}...")

        # Copia com DuckDB
        query = f"COPY (SELECT {col_query} FROM '{src}') TO '{dst}' (FORMAT PARQUET)"
        db_client.query(query)

        # Validação
        src_count = db_client.query(f"SELECT COUNT(*) FROM '{src}'").iloc[0, 0]
        dst_count = db_client.query(f"SELECT COUNT(*) FROM '{dst}'").iloc[0, 0]

        if src_count != dst_count:
            print(
                f"FALHA: Contagem divergente em {i}. Orig: {src_count}, Novo: {dst_count}"
            )
            return

        # Validação Schema
        schema = db_client.query(f"DESCRIBE SELECT * FROM '{dst}'")
        if list(schema["column_name"]) != cols:
            print(f"FALHA: Esquema divergente em {i}")
            return

        print(f"OK: {dst_count} registros.")

    print("\nReconstrução concluída com sucesso.")


if __name__ == "__main__":
    rebuild_files()
