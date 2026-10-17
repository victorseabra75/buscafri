import duckdb

ARQUIVOS = {
    "Municípios original": ("data/processed/municipios/Municipios.parquet"),
    "Municípios corrigido": ("data/processed_corrigido/municipios/Municipios.parquet"),
    "CNAEs original": ("data/processed/cnaes/Cnaes.parquet"),
    "CNAEs corrigido": ("data/processed_corrigido/cnaes/Cnaes.parquet"),
}


def inspecionar_arquivo(
    con: duckdb.DuckDBPyConnection,
    nome: str,
    caminho: str,
) -> None:
    print(f"\n{'=' * 60}")
    print(nome)
    print(f"Arquivo: {caminho}")
    print("=" * 60)

    try:
        esquema = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [caminho],
        ).df()

        print("\nEsquema:")
        print(esquema.to_string(index=False))

        total = con.execute(
            "SELECT COUNT(*) FROM read_parquet(?)",
            [caminho],
        ).fetchone()

        print(f"\nTotal de registros: {total[0] if total else 0}")

        print("\nPrimeiros 5 registros:")
        amostra = con.execute(
            "SELECT * FROM read_parquet(?) LIMIT 5",
            [caminho],
        ).df()

        print(amostra.to_string(index=False))

    except (duckdb.Error, OSError) as erro:
        print(f"Erro ao inspecionar o arquivo: {erro}")


def comparar_registros(
    con: duckdb.DuckDBPyConnection,
    nome: str,
    original: str,
    corrigido: str,
) -> None:
    print(f"\n{'=' * 60}")
    print(f"COMPARAÇÃO: {nome}")
    print("=" * 60)

    try:
        totais = con.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM read_parquet(?)) AS total_original,
                (SELECT COUNT(*) FROM read_parquet(?)) AS total_corrigido
            """,
            [original, corrigido],
        ).fetchone()

        if totais is None:
            raise RuntimeError(f"Não foi possível obter as contagens de {nome}.")

        total_original, total_corrigido = totais

        print(f"Original: {total_original}")
        print(f"Corrigido: {total_corrigido}")
        print(f"Diferença: {total_corrigido - total_original}")

        esquema_original = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [original],
        ).df()

        esquema_corrigido = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [corrigido],
        ).df()

        colunas_original = esquema_original["column_name"].tolist()
        colunas_corrigido = esquema_corrigido["column_name"].tolist()

        print(f"\nColunas originais: {colunas_original}")
        print(f"Colunas corrigidas: {colunas_corrigido}")

        if len(colunas_original) != len(colunas_corrigido):
            print("ATENÇÃO: os arquivos têm quantidades diferentes de colunas.")
        elif colunas_original != colunas_corrigido:
            print("ATENÇÃO: os nomes ou a ordem das colunas são diferentes.")
        else:
            print("Quantidade, nomes e ordem das colunas são iguais.")

    except duckdb.Error as erro:
        print(f"Erro ao comparar arquivos: {erro}")


def main() -> None:
    con = duckdb.connect(":memory:")

    try:
        for nome, caminho in ARQUIVOS.items():
            inspecionar_arquivo(con, nome, caminho)

        comparar_registros(
            con,
            "Municípios",
            ARQUIVOS["Municípios original"],
            ARQUIVOS["Municípios corrigido"],
        )

        comparar_registros(
            con,
            "CNAEs",
            ARQUIVOS["CNAEs original"],
            ARQUIVOS["CNAEs corrigido"],
        )

    finally:
        con.close()


if __name__ == "__main__":
    main()
