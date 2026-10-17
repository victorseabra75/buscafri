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

print("--- BUSCA NO ACRE (UF=AC) ---")
# Filtros: UF=AC, Município 0001 (exemplo da amostra anterior), CNAE 0111301
query = """
SELECT count(*), municipio, cnae_fiscal_principal 
FROM read_parquet('s3://buscafri-data/estabelecimentos/uf=AC/data_0.parquet')
GROUP BY municipio, cnae_fiscal_principal
LIMIT 5
"""
results = con.execute(query).fetchall()
for r in results:
    print(r)
