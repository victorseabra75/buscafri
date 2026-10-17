import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

REMOTE_PATH = "s3://buscafri-data/estabelecimentos/uf=AM/data_0.parquet"

LOCAL_PATH = Path("data/reordenado/estabelecimentos/uf=AM/data_0.parquet")

MUNICIPIOS_PATH = "s3://buscafri-data/municipios/Municipios.parquet"
CNAES_PATH = "s3://buscafri-data/cnaes/Cnaes.parquet"


def configurar_duckdb() -> duckdb.DuckDBPyConnection:
    """Configura o DuckDB para acessar o Cloudflare R2."""

    load_dotenv(".env")

    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id or not access_key or not secret_key:
        raise ValueError(
            "Verifique R2_ACCOUNT_ID, R2_ACCESS_KEY_ID e "
            "R2_SECRET_ACCESS_KEY no arquivo .env."
        )

    endpoint = (
        os.getenv(
            "R2_ENDPOINT",
            f"{account_id}.r2.cloudflarestorage.com",
        )
        .strip()
        .rstrip("/")
    )

    if endpoint.startswith("https://"):
        endpoint = endpoint.removeprefix("https://")
    elif endpoint.startswith("http://"):
        endpoint = endpoint.removeprefix("http://")

    conn = duckdb.connect(database=":memory:")

    try:
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        configuracoes = {
            "s3_endpoint": endpoint,
            "s3_access_key_id": access_key,
            "s3_secret_access_key": secret_key,
            "s3_url_style": "path",
            "s3_region": "auto",
        }

        for nome, valor in configuracoes.items():
            valor_sql = valor.replace("'", "''")
            conn.execute(f"SET {nome} = '{valor_sql}'")

    except duckdb.Error:
        conn.close()
        raise

    return conn


def obter_esquema(
    conn: duckdb.DuckDBPyConnection,
    caminho: str | Path,
) -> list[tuple[str, str]]:
    """Retorna os nomes e tipos das colunas de um Parquet."""

    return [
        (str(linha[0]), str(linha[1]))
        for linha in conn.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [str(caminho)],
        ).fetchall()
    ]


def contar_registros(
    conn: duckdb.DuckDBPyConnection,
    caminho: str | Path,
) -> int:
    """Conta os registros sem carregar o arquivo inteiro."""

    resultado = conn.execute(
        "SELECT COUNT(*) FROM read_parquet(?)",
        [str(caminho)],
    ).fetchone()

    if resultado is None:
        raise RuntimeError(f"A contagem não retornou resultado: {caminho}")

    return int(resultado[0])


def comparar_arquivos(
    conn: duckdb.DuckDBPyConnection,
    remoto: str,
    local: Path,
) -> tuple[int, int]:
    """Compara os dois arquivos nos dois sentidos."""

    consulta = """
        SELECT COUNT(*)
        FROM (
            SELECT * FROM read_parquet(?)
            EXCEPT ALL
            SELECT * FROM read_parquet(?)
        ) AS diferencas
    """

    diff_remote_1 = conn.execute(
        consulta,
        [remoto, str(local)],
    ).fetchone()

    diff_remote_2 = conn.execute(
        consulta,
        [str(local), remoto],
    ).fetchone()

    if diff_remote_1 is None or diff_remote_2 is None:
        raise RuntimeError("Uma das consultas EXCEPT ALL não retornou resultado.")

    return int(diff_remote_1[0]), int(diff_remote_2[0])


def descobrir_colunas_referencia(
    conn: duckdb.DuckDBPyConnection,
    caminho: str,
    nomes_esperados: tuple[str, str],
) -> tuple[str, str]:
    """
    Aceita referências com colunas codigo/descricao ou 0/1.
    Interrompe se o esquema não corresponder a nenhuma opção.
    """

    colunas = [nome for nome, _ in obter_esquema(conn, caminho)]

    if all(nome in colunas for nome in nomes_esperados):
        return nomes_esperados

    if "0" in colunas and "1" in colunas:
        print(f"Aviso: {caminho} utiliza colunas '0' e '1'.")
        return "0", "1"

    raise ValueError(f"Esquema inesperado em {caminho}. Colunas encontradas: {colunas}")


def executar_validacao(
    conn: duckdb.DuckDBPyConnection,
) -> None:
    """Executa as verificações remotas e os testes funcionais."""

    print("--- Validação Remota Amazonas (Pós-Upload) ---")

    if not LOCAL_PATH.is_file():
        raise FileNotFoundError(f"Parquet local não encontrado: {LOCAL_PATH.resolve()}")

    # 1. Inspecionar os esquemas.

    print("\n1. Esquema remoto:")
    esquema_remoto = obter_esquema(conn, REMOTE_PATH)

    for nome, tipo in esquema_remoto:
        print(f"  {nome}: {tipo}")

    print("\nEsquema local:")
    esquema_local = obter_esquema(conn, LOCAL_PATH)

    for nome, tipo in esquema_local:
        print(f"  {nome}: {tipo}")

    nomes_remotos = [nome for nome, _ in esquema_remoto]
    nomes_locais = [nome for nome, _ in esquema_local]

    if nomes_remotos != nomes_locais:
        raise ValueError(
            "Os nomes ou a ordem das colunas diferem entre o Parquet remoto e o local."
        )

    # 2. Quantidade de registros.

    print("\n2. Contagem de registros:")

    total_remoto = contar_registros(conn, REMOTE_PATH)
    total_local = contar_registros(conn, LOCAL_PATH)

    print(f"Remoto: {total_remoto:,}")
    print(f"Local:  {total_local:,}")

    if total_remoto != total_local:
        print("AVISO: as quantidades de registros divergem.")

    # 3. Amostra da ordenação.

    sort_cols = [
        "municipio",
        "cnae_fiscal_principal",
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
    ]

    ausentes = [coluna for coluna in sort_cols if coluna not in nomes_remotos]

    if ausentes:
        raise ValueError(f"Colunas de ordenação ausentes: {ausentes}")

    colunas_sql = ", ".join(f'"{coluna}"' for coluna in sort_cols)

    print("\n3. Amostra remota:")
    amostra = conn.execute(
        f"""
        SELECT {colunas_sql}
        FROM read_parquet(?)
        LIMIT 5
        """,
        [REMOTE_PATH],
    ).df()

    print(amostra.to_string(index=False))

    # 4. Comparação integral de conteúdo.

    print("\n4. Comparação integral EXCEPT ALL:")

    diff_remote_1, diff_remote_2 = comparar_arquivos(
        conn,
        REMOTE_PATH,
        LOCAL_PATH,
    )

    print(f"Diferenças (Remoto EXCEPT Local): {diff_remote_1:,}")
    print(f"Diferenças (Local EXCEPT Remoto): {diff_remote_2:,}")

    if diff_remote_1 == 0 and diff_remote_2 == 0:
        print(
            "SUCESSO: os conteúdos são equivalentes, "
            "incluindo a multiplicidade dos registros."
        )
    else:
        print("FALHA: os arquivos apresentam diferenças de conteúdo.")

    # 5. Contagem de estabelecimentos ativos.

    print("\n5. Teste funcional — estabelecimentos ativos:")

    colunas = dict(esquema_remoto)

    if "situacao_cadastral" not in colunas:
        raise ValueError("A coluna situacao_cadastral não existe no Parquet remoto.")

    tipo_situacao = colunas["situacao_cadastral"].upper()

    # O código cadastral deve ser comparado de acordo com seu tipo.
    if "INT" in tipo_situacao:
        filtro_ativo = "situacao_cadastral = 2"
    else:
        filtro_ativo = "TRIM(CAST(situacao_cadastral AS VARCHAR)) = '02'"

    consulta_ativas = f"""
        SELECT COUNT(*)
        FROM read_parquet(?) 
        WHERE {filtro_ativo}
    """

    resultado_ativas = conn.execute(
        consulta_ativas,
        [REMOTE_PATH],
    ).fetchone()

    if resultado_ativas is None:
        raise RuntimeError("A consulta de estabelecimentos ativos falhou.")

    count_ativas = int(resultado_ativas[0])

    print(f"Estabelecimentos ativos em AM: {count_ativas:,}")

    # 6. JOIN com municípios e CNAEs.

    print("\n6. Teste de JOIN com tabelas de referência:")

    coluna_codigo_mun, coluna_descricao_mun = descobrir_colunas_referencia(
        conn,
        MUNICIPIOS_PATH,
        ("codigo", "descricao"),
    )

    coluna_codigo_cnae, coluna_descricao_cnae = descobrir_colunas_referencia(
        conn,
        CNAES_PATH,
        ("codigo", "descricao"),
    )

    # Os nomes das colunas foram validados acima.
    # Os caminhos dos Parquets são passados como parâmetros.

    query_funcional = f"""
        SELECT
            est.municipio,
            mun."{coluna_descricao_mun}" AS nome_municipio,
            est.cnae_fiscal_principal,
            cnae."{coluna_descricao_cnae}" AS nome_cnae,
            COUNT(*) AS total_estabelecimentos
        FROM read_parquet(?) AS est
        LEFT JOIN read_parquet(?) AS mun
            ON CAST(est.municipio AS VARCHAR)
             = CAST(mun."{coluna_codigo_mun}" AS VARCHAR)
        LEFT JOIN read_parquet(?) AS cnae
            ON CAST(est.cnae_fiscal_principal AS VARCHAR)
             = CAST(cnae."{coluna_codigo_cnae}" AS VARCHAR)
        WHERE {filtro_ativo}
        GROUP BY
            est.municipio,
            mun."{coluna_descricao_mun}",
            est.cnae_fiscal_principal,
            cnae."{coluna_descricao_cnae}"
        ORDER BY total_estabelecimentos DESC
        LIMIT 5
    """

    resultado_funcional = conn.execute(
        query_funcional,
        [REMOTE_PATH, MUNICIPIOS_PATH, CNAES_PATH],
    ).df()

    print("\nTop 5 combinações município/CNAE ativos em AM:")
    print(resultado_funcional.to_string(index=False))


def main() -> int:
    conn: duckdb.DuckDBPyConnection | None = None

    try:
        conn = configurar_duckdb()
        executar_validacao(conn)
        return 0

    except (
        duckdb.Error,
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
    ) as erro:
        print(
            f"\nERRO: {type(erro).__name__}: {erro}",
            file=sys.stderr,
        )
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
