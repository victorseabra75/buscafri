import os

import duckdb
from dotenv import load_dotenv

load_dotenv()

con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")
con.execute(
    f"SET s3_endpoint='{os.getenv('R2_ENDPOINT', '').replace('https://', '').replace('http://', '')}';"
)
con.execute(f"SET s3_access_key_id='{os.getenv('R2_ACCESS_KEY_ID')}';")
con.execute(f"SET s3_secret_access_key='{os.getenv('R2_SECRET_ACCESS_KEY')}';")
con.execute("SET s3_url_style='path';")
con.execute("SET s3_region='auto';")

print("--- MUNICÍPIOS NO ACRE (AMERICA / REGIONAL / OU DISTINTOS) ---")
# Como o arquivo de municípios não tem coluna UF, vamos ver quais códigos de município aparecem nos estabelecimentos do AC
mun_ac = con.execute("""
    SELECT DISTINCT est.municipio, mun.descricao 
    FROM read_parquet('s3://buscafri-data/estabelecimentos/uf=AC/data_0.parquet') AS est
    LEFT JOIN read_parquet('s3://buscafri-data/municipios/Municipios.parquet') AS mun
        ON est.municipio = mun.codigo
    ORDER BY est.municipio
""").fetchall()

for m in mun_ac:
    print(f"Código: {m[0]} | Município: {m[1]}")

print("\n--- AMOSTRA DE CNAES PRESENTES NO ACRE ---")
cnae_ac = con.execute("""
    SELECT DISTINCT est.cnae_fiscal_principal, cnae.descricao 
    FROM read_parquet('s3://buscafri-data/estabelecimentos/uf=AC/data_0.parquet') AS est
    LEFT JOIN read_parquet('s3://buscafri-data/cnaes/Cnaes.parquet') AS cnae
        ON est.cnae_fiscal_principal = cnae.codigo
    LIMIT 10
""").fetchall()

for c in cnae_ac:
    print(f"CNAE: {c[0]} | Descrição: {c[1]}")
