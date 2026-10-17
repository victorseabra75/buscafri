import sys
from pathlib import Path

import duckdb

RAIZ = Path.cwd()

ORIG_PATH = (
    RAIZ / "data" / "particionado" / "estabelecimentos" / "uf=AM" / "data_0.parquet"
)

REORD_PATH = (
    RAIZ / "data" / "reordenado" / "estabelecimentos" / "uf=AM" / "data_0.parquet"
)

SORT_COLS = [
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
]


def contar_registros(
    con: duckdb.DuckDBPyConnection,
    caminho: Path,
) -> int:
    resultado = con.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(caminho)],
    ).fetchone()

    if resultado is None:
        raise RuntimeError(f"A contagem não retornou resultado: {caminho}")

    return int(resultado[0])


def obter_esquema(
    con: duckdb.DuckDBPyConnection,
    caminho: Path,
) -> list[tuple[str, str]]:
    resultado = con.execute(
        "DESCRIBE SELECT * FROM read_parquet(?)",
        [str(caminho)],
    ).fetchall()

    return [(str(linha[0]), str(linha[1])) for linha in resultado]


def contar_diferencas(
    con: duckdb.DuckDBPyConnection,
    caminho_a: Path,
    caminho_b: Path,
) -> int:
    resultado = con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT * FROM read_parquet(?)
            EXCEPT ALL
            SELECT * FROM read_parquet(?)
        ) AS diferencas
        """,
        [str(caminho_a), str(caminho_b)],
    ).fetchone()

    if resultado is None:
        raise RuntimeError(
            f"EXCEPT ALL não retornou resultado para {caminho_a} e {caminho_b}."
        )

    return int(resultado[0])


def validar() -> int:
    print("--- Validação Local Amazonas (AM) ---")
    print(f"Diretório de execução: {RAIZ}")

    # 1. Verificar os arquivos.

    for caminho in (ORIG_PATH, REORD_PATH):
        if not caminho.is_file():
            print(
                f"ERRO: Arquivo não encontrado: {caminho}",
                file=sys.stderr,
            )
            return 1

        tamanho = caminho.stat().st_size

        if tamanho == 0:
            print(
                f"ERRO: Arquivo vazio: {caminho}",
                file=sys.stderr,
            )
            return 1

        print(f"\nArquivo: {caminho}")
        print(f"Tamanho: {tamanho:,} bytes")

    con = duckdb.connect(database=":memory:")

    try:
        # 2. Validar leitura e contagem.

        print("\n--- 1. Contagem de registros ---")

        try:
            orig_count = contar_registros(con, ORIG_PATH)
        except duckdb.Error as erro:
            print(
                f"ERRO lendo o original: {erro}",
                file=sys.stderr,
            )
            return 1

        try:
            reord_count = contar_registros(con, REORD_PATH)
        except duckdb.Error as erro:
            print(
                f"ERRO lendo o reordenado: {erro}",
                file=sys.stderr,
            )
            return 1

        print(f"Original:   {orig_count:,}")
        print(f"Reordenado: {reord_count:,}")

        if orig_count != reord_count:
            print(
                "ERRO: As quantidades de registros divergem.",
                file=sys.stderr,
            )
            return 1

        print("Contagens iguais.")

        # 3. Comparar esquemas.

        print("\n--- 2. Comparação dos esquemas ---")

        orig_schema = obter_esquema(con, ORIG_PATH)
        reord_schema = obter_esquema(con, REORD_PATH)

        print(f"Colunas originais: {len(orig_schema)}")
        print(f"Colunas reordenadas: {len(reord_schema)}")

        if orig_schema != reord_schema:
            print("\nERRO: Os esquemas diferem.")

            orig_dict = dict(orig_schema)
            reord_dict = dict(reord_schema)

            for coluna in sorted(set(orig_dict) | set(reord_dict)):
                tipo_orig = orig_dict.get(coluna, "AUSENTE")
                tipo_reord = reord_dict.get(coluna, "AUSENTE")

                if tipo_orig != tipo_reord:
                    print(f"  {coluna}: original={tipo_orig}; reordenado={tipo_reord}")

            print(
                "\nA comparação EXCEPT ALL não será executada "
                "até o esquema ser investigado.",
                file=sys.stderr,
            )
            return 1

        print("Nomes, ordem e tipos das colunas são iguais.")

        # 4. Comparar conteúdo integral nos dois sentidos.

        print("\n--- 3. Comparação integral EXCEPT ALL ---")

        try:
            diff_1 = contar_diferencas(
                con,
                ORIG_PATH,
                REORD_PATH,
            )
        except duckdb.Error as erro:
            print(
                f"ERRO no Original EXCEPT Reordenado: {erro}",
                file=sys.stderr,
            )
            return 1

        try:
            diff_2 = contar_diferencas(
                con,
                REORD_PATH,
                ORIG_PATH,
            )
        except duckdb.Error as erro:
            print(
                f"ERRO no Reordenado EXCEPT Original: {erro}",
                file=sys.stderr,
            )
            return 1

        print(f"Original EXCEPT Reordenado: {diff_1:,}")
        print(f"Reordenado EXCEPT Original: {diff_2:,}")

        if diff_1 != 0 or diff_2 != 0:
            print(
                "ERRO: Os conteúdos dos arquivos divergem.",
                file=sys.stderr,
            )
            return 1

        print("SUCESSO: Conteúdo integral equivalente.")

        # 5. Verificar as colunas necessárias à ordenação.

        print("\n--- 4. Amostra da ordenação ---")

        colunas = [nome for nome, _ in reord_schema]
        ausentes = [nome for nome in SORT_COLS if nome not in colunas]

        if ausentes:
            print(
                f"ERRO: Colunas de ordenação ausentes: {ausentes}",
                file=sys.stderr,
            )
            return 1

        colunas_sql = ", ".join(f'"{nome}"' for nome in SORT_COLS)

        amostra = con.execute(
            f"""
            SELECT {colunas_sql}
            FROM read_parquet(?)
            LIMIT 10
            """,
            [str(REORD_PATH)],
        ).df()

        print(amostra.to_string(index=False))

        print(
            "\nValidação concluída. "
            "Os arquivos têm contagens, esquemas e conteúdos equivalentes."
        )

        return 0

    except (
        duckdb.Error,
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
    ) as erro:
        print(
            f"\nERRO: {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )
        return 1

    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(validar())
