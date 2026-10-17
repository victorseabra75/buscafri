from pathlib import Path

import duckdb

mun_local = Path("data/processed_corrigido/municipios/Municipios.parquet")
cnae_local = Path("data/processed_corrigido/cnaes/Cnaes.parquet")

print("--- Validação Local Pré-Upload ---")
con = duckdb.connect()

df_mun = con.execute(f"SELECT * FROM read_parquet('{mun_local}')").df()
print(f"Municípios Locais: {len(df_mun)} linhas")
print(f"Esquema Municípios: {df_mun.dtypes.to_dict()}")
print(f"Colunas Municípios: {list(df_mun.columns)}")

df_cnae = con.execute(f"SELECT * FROM read_parquet('{cnae_local}')").df()
print(f"CNAEs Locais: {len(df_cnae)} linhas")
print(f"Esquema CNAEs: {df_cnae.dtypes.to_dict()}")
print(f"Colunas CNAEs: {list(df_cnae.columns)}")
