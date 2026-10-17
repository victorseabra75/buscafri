from pathlib import Path

import duckdb

orig_path = Path("data/particionado/estabelecimentos/uf=AL/data_0.parquet")
reord_path = Path("data/reordenado/estabelecimentos/uf=AL/data_0.parquet")

con = duckdb.connect()

print("--- Comparação Alagoas (AL) ---")

# 1. Contagem e Esquema
print("\n[Original]")
orig_info = con.execute(
    f"SELECT count(*) as total FROM read_parquet('{orig_path}')"
).df()
print(f"Total registros: {orig_info.iloc[0]['total']}")
print(
    f"Esquema (amostra colunas): {list(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{orig_path}')").df()['column_name'][:5])}"
)

print("\n[Reordenado]")
reord_info = con.execute(
    f"SELECT count(*) as total FROM read_parquet('{reord_path}')"
).df()
print(f"Total registros: {reord_info.iloc[0]['total']}")
print(
    f"Esquema (amostra colunas): {list(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{reord_path}')").df()['column_name'][:5])}"
)

# 2. Verificação de Ordenação Física
print("\n[Verificando Ordenação Física]")
# A ordenação esperada é: municipio, cnae_fiscal_principal, cnpj_basico, cnpj_ordem, cnpj_dv
sort_cols = [
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
]
query_sort = f"SELECT {', '.join(sort_cols)} FROM read_parquet('{reord_path}') LIMIT 10"
print("Amostra da ordenação:")
print(con.execute(query_sort).df())

# 3. Comparação de Conteúdo (hashes de colunas chaves ou count total por filtros)
print("\n[Comparação de Conteúdo]")
if orig_info.iloc[0]["total"] == reord_info.iloc[0]["total"]:
    print("✅ Quantidade de registros coincide.")
else:
    print("❌ Divergência na quantidade de registros!")
