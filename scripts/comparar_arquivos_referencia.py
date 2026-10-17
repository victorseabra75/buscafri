from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

ARQUIVO_MUNICIPIOS_ORIGINAL = (
    ROOT / "data" / "processed" / "municipios" / "Municipios.parquet"
)
ARQUIVO_MUNICIPIOS_CORRIGIDO = (
    ROOT / "data" / "processed_corrigido" / "municipios" / "Municipios.parquet"
)


def carregar_parquet(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    return pd.read_parquet(caminho)


def normalizar_texto(serie: pd.Series) -> pd.Series:
    """Converte valores para texto e uniformiza espaços."""
    return serie.astype("string").fillna("").str.strip()


def testar_e_comparar() -> None:
    print("=== 1. VERIFICAÇÃO DE MUNICÍPIOS ===")

    df_original = carregar_parquet(ARQUIVO_MUNICIPIOS_ORIGINAL)
    df_corrigido = carregar_parquet(ARQUIVO_MUNICIPIOS_CORRIGIDO)

    print(f"Original: {df_original.shape}, colunas: {df_original.columns.tolist()}")
    print(f"Corrigido: {df_corrigido.shape}, colunas: {df_corrigido.columns.tolist()}")

    if df_original.shape[1] != 2 or df_corrigido.shape[1] != 2:
        raise ValueError("Esperadas duas colunas em cada arquivo de municípios.")

    # Renomear para permitir a comparação mesmo com cabeçalhos diferentes.
    original = df_original.iloc[:, :2].copy()
    original.columns = ["codigo", "descricao"]

    corrigido = df_corrigido.iloc[:, :2].copy()
    corrigido.columns = ["codigo", "descricao"]

    for coluna in ["codigo", "descricao"]:
        original[coluna] = normalizar_texto(original[coluna])
        corrigido[coluna] = normalizar_texto(corrigido[coluna])

    print("\nTipos após normalização:")
    print(original.dtypes)
    print(corrigido.dtypes)

    # Verificar duplicatas considerando o registro completo.
    print("\n--- Duplicatas ---")
    print(f"Duplicatas no original: {original.duplicated().sum()}")
    print(f"Duplicatas no corrigido: {corrigido.duplicated().sum()}")

    # Comparar registros completos, sem depender dos índices do Pandas.
    original_unico = original.drop_duplicates()
    corrigido_unico = corrigido.drop_duplicates()

    comparacao = original_unico.merge(
        corrigido_unico,
        on=["codigo", "descricao"],
        how="outer",
        indicator=True,
    )

    apenas_original = comparacao.loc[
        comparacao["_merge"] == "left_only",
        ["codigo", "descricao"],
    ]

    apenas_corrigido = comparacao.loc[
        comparacao["_merge"] == "right_only",
        ["codigo", "descricao"],
    ]

    comuns = int((comparacao["_merge"] == "both").sum())

    print("\n--- Resultado da comparação ---")
    print(f"Registros únicos no original: {len(original_unico)}")
    print(f"Registros únicos no corrigido: {len(corrigido_unico)}")
    print(f"Registros correspondentes: {comuns}")
    print(f"Registros apenas no original: {len(apenas_original)}")
    print(f"Registros apenas no corrigido: {len(apenas_corrigido)}")

    print("\n--- Exemplos apenas no original ---")
    print(apenas_original.head(20).to_string(index=False))

    print("\n--- Exemplos apenas no corrigido ---")
    print(apenas_corrigido.head(20).to_string(index=False))

    # Verificar se há códigos associados a descrições diferentes.
    codigos_original = original.groupby("codigo")["descricao"].agg(set)
    codigos_corrigido = corrigido.groupby("codigo")["descricao"].agg(set)

    codigos_comuns = set(codigos_original.index) & set(codigos_corrigido.index)

    alteracoes = [
        {
            "codigo": codigo,
            "descricao_original": sorted(codigos_original[codigo]),
            "descricao_corrigida": sorted(codigos_corrigido[codigo]),
        }
        for codigo in sorted(codigos_comuns)
        if codigos_original[codigo] != codigos_corrigido[codigo]
    ]

    print("\n--- Códigos com descrições diferentes ---")
    print(f"Total: {len(alteracoes)}")

    for alteracao in alteracoes[:20]:
        print(alteracao)


if __name__ == "__main__":
    testar_e_comparar()
