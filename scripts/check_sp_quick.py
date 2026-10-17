import sys
from pathlib import Path

import duckdb

# Define e adiciona a raiz do projeto ao caminho de importação.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Importa o módulo pelo caminho direto do arquivo.
import importlib.util

validator_path = PROJECT_ROOT / "scripts" / "validar_reordenacao_r2.py"

if not validator_path.is_file():
    raise FileNotFoundError(f"Arquivo de validação não encontrado: {validator_path}")

spec = importlib.util.spec_from_file_location(
    "validar_reordenacao_r2",
    validator_path,
)

if spec is None or spec.loader is None:
    raise ImportError(f"Não foi possível carregar o módulo: {validator_path}")

validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)

ORDER_COLUMNS = validator.ORDER_COLUMNS
fetch_scalar = validator.fetch_scalar

orig = (
    PROJECT_ROOT / "data/particionado/estabelecimentos/uf=SP/data_0.parquet"
).resolve()
novo = (
    PROJECT_ROOT / "data/reordenado/estabelecimentos/uf=SP/data_0.parquet"
).resolve()

if not orig.is_file():
    raise FileNotFoundError(f"Arquivo original não encontrado: {orig}")

if not novo.is_file():
    raise FileNotFoundError(f"Arquivo reordenado não encontrado: {novo}")

print("--- AUDITORIA RÁPIDA UF=SP ---")

with duckdb.connect() as con:
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
    print("1. Schema igual:", schema_ok)

    if not schema_ok:
        print("Schema original:", s_orig)
        print("Schema reordenado:", s_novo)
        raise SystemExit(1)

    # 2. Contagem
    c_orig = fetch_scalar(
        con,
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(orig)],
    )
    c_novo = fetch_scalar(
        con,
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(novo)],
    )

    counts_ok = c_orig == c_novo
    print(f"2. Contagens: Orig={c_orig:,} | Novo={c_novo:,}")
    print("   Contagens iguais:", counts_ok)

    # 3. Ordenação física
    def quote_identifier(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    columns = [row[0] for row in s_novo]
    missing = set(ORDER_COLUMNS) - set(columns)

    if missing:
        raise ValueError(f"Colunas de ordenação ausentes: {sorted(missing)}")

    quoted_order = [quote_identifier(col) for col in ORDER_COLUMNS]
    lag_columns = ", ".join(
        f"LAG({quote_identifier(col)}) OVER "
        f"(ORDER BY file_row_number) AS "
        f"{quote_identifier('prev_' + col)}"
        for col in ORDER_COLUMNS
    )

    equal_prefix = []
    inversion_terms = []

    for col in ORDER_COLUMNS:
        prev = quote_identifier("prev_" + col)
        curr = quote_identifier(col)

        greater = (
            f"(({prev} IS NULL AND {curr} IS NOT NULL) OR "
            f"({prev} IS NOT NULL AND {curr} IS NOT NULL "
            f"AND {prev} > {curr}))"
        )

        prefix = " AND ".join(equal_prefix)
        inversion_terms.append(f"({prefix} AND {greater})" if prefix else greater)
        equal_prefix.append(f"{prev} IS NOT DISTINCT FROM {curr}")

    inversion_condition = " OR ".join(inversion_terms)
    previous_exists = " OR ".join(
        f"{quote_identifier('prev_' + col)} IS NOT NULL" for col in ORDER_COLUMNS
    )

    order_sql = f"""
        WITH ordered_rows AS (
            SELECT
                file_row_number,
                {", ".join(quoted_order)},
                {lag_columns}
            FROM read_parquet(?, file_row_number = true)
        )
        SELECT COUNT(*)
        FROM ordered_rows
        WHERE ({previous_exists})
          AND ({inversion_condition})
    """

    inversions = fetch_scalar(con, order_sql, [str(novo)])
    order_ok = inversions == 0

    print(f"3. Inversões de ordenação: {inversions:,}")
    print("   Ordenação válida:", order_ok)

    # 4. Comparação exata de conteúdo
    print("4. Comparando conteúdo com EXCEPT ALL...")

    all_columns = ", ".join(quote_identifier(col) for col in columns)

    diff_sql = f"""
        SELECT COUNT(*)
        FROM (
            (
                SELECT {all_columns} FROM read_parquet(?)
                EXCEPT ALL
                SELECT {all_columns} FROM read_parquet(?)
            )
            UNION ALL
            (
                SELECT {all_columns} FROM read_parquet(?)
                EXCEPT ALL
                SELECT {all_columns} FROM read_parquet(?)
            )
        ) AS differences
    """

    diff_count = fetch_scalar(
        con,
        diff_sql,
        [str(orig), str(novo), str(novo), str(orig)],
    )

    content_ok = diff_count == 0
    print(f"   Diferenças encontradas: {diff_count:,}")
    print("   Conteúdo idêntico:", content_ok)

    passed = schema_ok and counts_ok and order_ok and content_ok

    print("\n" + "=" * 42)
    print(f"SCHEMA:    {'OK' if schema_ok else 'FALHA'}")
    print(f"CONTAGEM:  {'OK' if counts_ok else 'FALHA'}")
    print(f"ORDENAÇÃO: {'OK' if order_ok else 'FALHA'}")
    print(f"CONTEÚDO:  {'OK' if content_ok else 'FALHA'}")
    print(f"RESULTADO: {'APROVADO' if passed else 'FALHA'}")

if not passed:
    raise SystemExit(1)
