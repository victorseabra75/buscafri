import time
from pathlib import Path
import duckdb


def run_benchmark():
    conn = duckdb.connect(database=":memory:")

    estab_path = "data/particionado/estabelecimentos/uf=BA/*.parquet"
    empresas_path = "data/processed_corrigido/empresas/*.parquet"

    if not list(Path("data/particionado/estabelecimentos/uf=BA").glob("*.parquet")):
        print("Dados locais de teste não encontrados para benchmark.")
        return

    print("==================================================")
    print("BENCHMARK: Comparação de Estratégias de Consulta")
    print("==================================================")

    # 1. Estratégia Antiga: JOIN de toda a base antes do LIMIT
    query_antiga = f"""
        SELECT
            est.cnpj_basico,
            emp.razao_social,
            est.nome_fantasia,
            est.situacao_cadastral,
            est.uf,
            est.municipio,
            est.cnae_fiscal_principal
        FROM read_parquet('{estab_path}', hive_partitioning = true) AS est
        JOIN read_parquet('{empresas_path}') AS emp
            ON est.cnpj_basico = emp.cnpj_basico
        WHERE est.situacao_cadastral = '02'
        ORDER BY est.municipio, est.cnae_fiscal_principal, est.cnpj_basico, est.cnpj_ordem, est.cnpj_dv
        LIMIT 21;
    """

    # 2. Nova Estratégia: Late Materialization (Subquery com LIMIT 21 antes do JOIN)
    query_nova = f"""
        WITH paginados AS (
            SELECT
                est.cnpj_basico,
                est.nome_fantasia,
                est.situacao_cadastral,
                est.uf,
                est.municipio,
                est.cnae_fiscal_principal,
                est.cnpj_ordem,
                est.cnpj_dv
            FROM read_parquet('{estab_path}', hive_partitioning = true) AS est
            WHERE est.situacao_cadastral = '02'
            ORDER BY est.municipio, est.cnae_fiscal_principal, est.cnpj_basico, est.cnpj_ordem, est.cnpj_dv
            LIMIT 21
        )
        SELECT
            p.cnpj_basico,
            emp.razao_social,
            p.nome_fantasia,
            p.situacao_cadastral,
            p.uf,
            p.municipio,
            p.cnae_fiscal_principal
        FROM paginados p
        JOIN read_parquet('{empresas_path}') AS emp
            ON p.cnpj_basico = emp.cnpj_basico
        ORDER BY p.municipio, p.cnae_fiscal_principal, p.cnpj_basico, p.cnpj_ordem, p.cnpj_dv;
    """

    # Warmup
    conn.execute(query_nova).fetchall()

    # Teste Antigo
    start = time.perf_counter()
    res_antigo = conn.execute(query_antiga).fetchall()
    tempo_antigo = (time.perf_counter() - start) * 1000

    # Teste Novo
    start = time.perf_counter()
    res_novo = conn.execute(query_nova).fetchall()
    tempo_novo = (time.perf_counter() - start) * 1000

    print(
        f"Estratégia Antiga (JOIN antes do LIMIT): {tempo_antigo:.2f} ms | Registros: {len(res_antigo)}"
    )
    print(
        f"Estratégia Nova (Late Materialization):   {tempo_novo:.2f} ms | Registros: {len(res_novo)}"
    )
    print(
        f"Redução de latência: {((tempo_antigo - tempo_novo) / tempo_antigo) * 100:.1f}%"
    )

    print("\n--- EXPLAIN ANALYZE DA NOVA ESTRATÉGIA ---")
    plan = conn.execute(f"EXPLAIN ANALYZE {query_nova}").fetchall()
    for row in plan:
        print(str(row[1]).encode("ascii", "ignore").decode("ascii"))


if __name__ == "__main__":
    run_benchmark()

    print("\n--- EXPLAIN ANALYZE DA NOVA ESTRATÉGIA ---")
    plan = conn.execute(f"EXPLAIN ANALYZE {query_nova}").fetchall()
    for row in plan:
        print(row[1])


if __name__ == "__main__":
    run_benchmark()
