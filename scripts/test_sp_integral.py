from pathlib import Path

import duckdb

# Raiz do projeto: ajuste apenas se este script estiver em outra pasta.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

orig = (
    PROJECT_ROOT / "data/particionado/estabelecimentos/uf=SP/data_0.parquet"
).resolve()

novo = (
    PROJECT_ROOT / "data/reordenado/estabelecimentos/uf=SP/data_0.parquet"
).resolve()

temp_dir = (PROJECT_ROOT / "data/duckdb_temp").resolve()
temp_dir.mkdir(parents=True, exist_ok=True)

ORDER_COLS = [
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
]


def scalar_int(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: list[str] | None = None,
) -> int:
    """Executa uma consulta escalar e valida seu resultado."""
    result = con.execute(sql, params or []).fetchone()

    if result is None or result[0] is None:
        raise RuntimeError("A consulta não retornou um valor válido.")

    return int(result[0])


def audit() -> bool:
    """Executa a auditoria da partição SP."""
    if not orig.is_file():
        raise FileNotFoundError(f"Arquivo original não encontrado: {orig}")

    if not novo.is_file():
        raise FileNotFoundError(f"Arquivo reordenado não encontrado: {novo}")

    print("--- AUDITORIA DETALHADA UF=SP ---")
    print(f"Origem:     {orig}")
    print(f"Reordenado: {novo}")

    with duckdb.connect(
        config={
            "temp_directory": str(temp_dir),
            "max_memory": "8GB",
        }
    ) as con:
        # 1. Schema
        s_orig = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(orig)],
        ).fetchall()

        s_novo = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(novo)],
        ).fetchall()

        schema_ok = s_orig == s_novo
        print(f"\n1. Schema igual: {schema_ok}")

        if not schema_ok:
            print("Schema original:")
            for column in s_orig:
                print(f"  {column}")

            print("Schema reordenado:")
            for column in s_novo:
                print(f"  {column}")

            print("\nAuditoria interrompida: os schemas são diferentes.")
            return False

        column_names = {column[0] for column in s_novo}
        missing_columns = set(ORDER_COLS) - column_names

        if missing_columns:
            print(
                "Colunas necessárias à ordenação ausentes:",
                sorted(missing_columns),
            )
            return False

        # 2. Quantidade de registros
        c_orig = scalar_int(
            con,
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(orig)],
        )

        c_novo = scalar_int(
            con,
            "SELECT COUNT(*) FROM read_parquet(?)",
            [str(novo)],
        )

        counts_ok = c_orig == c_novo
        print(f"\n2. Contagens: Orig={c_orig:,} | Novo={c_novo:,}")
        print(f"   Quantidades iguais: {counts_ok}")

        # 3. Ordenação física
        # file_row_number representa a posição do registro no arquivo.
        # O segundo ROW_NUMBER usa as chaves de ordenação e a posição
        # original como desempate determinístico.
        order_by = ", ".join(f'"{column}" ASC NULLS LAST' for column in ORDER_COLS)

        order_sql = f"""
            SELECT COUNT(*)
            FROM (
                SELECT
                    ROW_NUMBER() OVER (
                        ORDER BY file_row_number
                    ) AS posicao_atual,
                    ROW_NUMBER() OVER (
                        ORDER BY {order_by}, file_row_number
                    ) AS posicao_esperada
                FROM read_parquet(
                    ?,
                    file_row_number = true
                )
            ) AS verificacao
            WHERE posicao_atual <> posicao_esperada
        """

        order_errors = scalar_int(
            con,
            order_sql,
            [str(novo)],
        )

        order_ok = order_errors == 0
        print(f"\n3. Erros de ordenação: {order_errors:,}")
        print(f"   Ordenação validada: {order_ok}")

        # 4. Comparação de conteúdo e multiplicidade (EXCEPT ALL)
        print("\n4. Executando EXCEPT ALL; pode demorar...")

        diff_sql = """
            SELECT COUNT(*)
            FROM (
                (
                    SELECT * FROM read_parquet(?)
                    EXCEPT ALL
                    SELECT * FROM read_parquet(?)
                )
                UNION ALL
                (
                    SELECT * FROM read_parquet(?)
                    EXCEPT ALL
                    SELECT * FROM read_parquet(?)
                )
            ) AS diferencas
        """

        diff_count = scalar_int(
            con,
            diff_sql,
            [
                str(orig),
                str(novo),
                str(novo),
                str(orig),
            ],
        )

        content_ok = diff_count == 0
        print(f"   Diferenças de conteúdo: {diff_count:,}")
        print(f"   Conteúdo idêntico: {content_ok}")

        # Resultado final
        passed = schema_ok and counts_ok and order_ok and content_ok

        print("\n" + "=" * 48)
        print(f"SCHEMA:      {'OK' if schema_ok else 'FALHA'}")
        print(f"CONTAGEM:    {'OK' if counts_ok else 'FALHA'}")
        print(f"ORDENAÇÃO:   {'OK' if order_ok else 'FALHA'}")
        print(f"CONTEÚDO:    {'OK' if content_ok else 'FALHA'}")
        print("=" * 48)
        print(f"RESULTADO: {'APROVADO' if passed else 'FALHA'}")

        return passed


if __name__ == "__main__":
    try:
        if not audit():
            raise SystemExit(1)
    except (duckdb.Error, OSError, RuntimeError, ValueError) as error:
        print(f"\nERRO NA AUDITORIA: {type(error).__name__}: {error}")
        raise SystemExit(1) from error
