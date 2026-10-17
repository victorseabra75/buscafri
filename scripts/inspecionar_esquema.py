import duckdb

con = duckdb.connect()
sample_file = "data/particionado/estabelecimentos/uf=AC/data_0.parquet"
schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sample_file}')").fetchall()

print("--- SCHEMA DE ESTABELECIMENTOS ---")
for col in schema:
    print(f"Coluna: {col[0]:<30} | Tipo: {col[1]}")

print("\n--- SAMPLE ROWS (uf=AC) ---")
sample_data = con.execute(
    f"SELECT municipio, cnae_fiscal_principal, cnpj_basico, cnpj_ordem, cnpj_dv FROM read_parquet('{sample_file}') LIMIT 5"
).fetchall()
for row in sample_data:
    print(row)

print("\n--- VERIFICAÇÃO DE ZEROS À ESQUERDA E TIPOS DAS 5 COLUNAS ---")
check_types = con.execute(f"""
    SELECT 
        typeof(municipio),
        typeof(cnae_fiscal_principal),
        typeof(cnpj_basico),
        typeof(cnpj_ordem),
        typeof(cnpj_dv)
    FROM read_parquet('{sample_file}') LIMIT 1
""").fetchone()
print("Tipos DuckDB:", check_types)

check_nulls = con.execute("""
    SELECT 
        COUNT(*) filter (WHERE municipio IS NULL) as null_mun,
        COUNT(*) filter (WHERE cnae_fiscal_principal IS NULL) as null_cnae,
        COUNT(*) filter (WHERE cnpj_basico IS NULL) as null_basico,
        COUNT(*) filter (WHERE cnpj_ordem IS NULL) as null_ordem,
        COUNT(*) filter (WHERE cnpj_dv IS NULL) as null_dv
    FROM read_parquet('data/particionado/estabelecimentos/*/*.parquet')
""").fetchone()
print("Nulls em todas as partições:", check_nulls)
