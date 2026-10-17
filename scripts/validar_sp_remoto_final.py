import os
import duckdb
from dotenv import load_dotenv

load_dotenv(".env")

conn = duckdb.connect(":memory:")
conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")

account_id = os.getenv("R2_ACCOUNT_ID")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
endpoint = f"{account_id}.r2.cloudflarestorage.com"

conn.execute(f"SET s3_endpoint='{endpoint}'")
conn.execute(f"SET s3_access_key_id='{access_key}'")
conn.execute(f"SET s3_secret_access_key='{secret_key}'")
conn.execute("SET s3_url_style='path'")
conn.execute("SET s3_region='auto'")

remote_path = "s3://buscafri-data/estabelecimentos/uf=SP/data_0.parquet"

print("--- Validação Remota São Paulo (SP) ---")

# 1. Contagem remota
print("Consultando contagem remota de registros...")
count_remoto = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{remote_path}')").fetchone()[0]
print(f"Contagem remota: {count_remoto:,} registros")

# 2. Esquema e colunas
print("\nVerificando colunas e tipos...")
schema_df = conn.execute(f"DESCRIBE SELECT * FROM read_parquet('{remote_path}')").df()
print(f"Total de colunas: {len(schema_df)}")
print("Amostra de colunas e tipos:")
print(schema_df[["column_name", "column_type"]].head(10))

# 3. Ordenação física (amostra inicial)
sort_cols = ["municipio", "cnae_fiscal_principal", "cnpj_basico", "cnpj_ordem", "cnpj_dv"]
print("\nAmostra inicial da ordenação física no R2:")
amostra = conn.execute(f"SELECT {', '.join(sort_cols)} FROM read_parquet('{remote_path}') LIMIT 10").df()
print(amostra)

# 4. Consulta funcional representativa (estabelecimentos ativos)
print("\nConsulta funcional: Estabelecimentos ativos em SP...")
ativas = conn.execute(f"SELECT COUNT(*) FROM read_parquet('{remote_path}') WHERE situacao_cadastral = '02'").fetchone()[0]
print(f"Total de estabelecimentos ativos (02) em SP: {ativas:,}")
