from pathlib import Path

import duckdb
import pandas as pd

# Configuração simulando o ambiente do projeto
PROCESSED_DIR = Path("data/preprocessed")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mapeamento de colunas para arquivos de referência
# O CSV no preprocessed já tem o cabeçalho injetado pelo PowerShell (ex: codigo;descricao)
# O script de conversão atual (convert_to_parquet.py) lê como header=None, o que causa
# o problema das colunas "0" e "1". Precisamos corrigir a leitura.


def corrigir_conversao_referencia(table_name, csv_filename, output_name):
    print(f"🔄 Corrigindo conversão: {table_name}")

    csv_path = PROCESSED_DIR / csv_filename
    output_parquet = OUTPUT_DIR / table_name / f"{output_name}.parquet"
    output_parquet.parent.mkdir(parents=True, exist_ok=True)

    # Lê o CSV com o cabeçalho correto que já está lá (injetado pelo PowerShell)
    df = pd.read_csv(csv_path, sep=";", encoding="utf-8", dtype=str)

    # Validação básica
    print(f"   Colunas detectadas: {list(df.columns)}")
    print(f"   Quantidade de registros: {len(df)}")

    # Salva como Parquet com os nomes de colunas corretos
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(
        f"COPY df_data TO '{output_parquet}' (FORMAT 'PARQUET', COMPRESSION 'SNAPPY');"
    )
    con.close()
    print(f"   ✅ Salvo em: {output_parquet}")


# Executa para Municipios e Cnaes
# Precisamos encontrar o nome correto do arquivo CSV na pasta preprocessed
# Ex: Municípios1.csv (baseado na lógica do script de processamento)


def find_file(category):
    for f in PROCESSED_DIR.glob(f"{category}*.csv"):
        return f.name
    return None


mun_csv = find_file("Municipios")
cnae_csv = find_file("Cnaes")

if mun_csv:
    corrigir_conversao_referencia("municipios", mun_csv, "Municipios")
if cnae_csv:
    corrigir_conversao_referencia("cnaes", cnae_csv, "Cnaes")
