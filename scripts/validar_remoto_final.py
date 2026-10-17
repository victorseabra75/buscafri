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

print("--- Verificação Remota Pós-Upload ---")

print("\nMunicípios Remoto:")
df_mun = conn.execute(
    "SELECT * FROM read_parquet('s3://buscafri-data/municipios/Municipios.parquet')"
).df()
print(f"Linhas: {len(df_mun)}")
print(f"Colunas: {list(df_mun.columns)}")
print(df_mun.head(3))

print("\nCNAEs Remoto:")
df_cnae = conn.execute(
    "SELECT * FROM read_parquet('s3://buscafri-data/cnaes/Cnaes.parquet')"
).df()
print(f"Linhas: {len(df_cnae)}")
print(f"Colunas: {list(df_cnae.columns)}")
print(df_cnae.head(3))

print("\n--- Teste Funcional (Acre) ---")
query = """
SELECT 
    est.municipio, 
    mun.descricao AS nome_municipio,
    est.cnae_fiscal_principal,
    cnae.descricao AS nome_cnae
FROM read_parquet('s3://buscafri-data/estabelecimentos/uf=AC/data_0.parquet') AS est
LEFT JOIN read_parquet('s3://buscafri-data/municipios/Municipios.parquet') AS mun ON est.municipio = mun.codigo
LEFT JOIN read_parquet('s3://buscafri-data/cnaes/Cnaes.parquet') AS cnae ON est.cnae_fiscal_principal = cnae.codigo
LIMIT 5
"""
res = conn.execute(query).df()
print(res)
