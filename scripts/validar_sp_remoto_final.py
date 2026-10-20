import os
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"

load_dotenv(ENV_FILE)

BUCKET = os.getenv("R2_BUCKET_NAME", "buscafri-data").strip()

REMOTE_PATH = f"s3://{BUCKET}/estabelecimentos/uf=SP/data_0.parquet"


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================


def sql_literal(valor: str) -> str:
    """Escapa uma string para uso seguro como literal SQL."""
    return "'" + valor.replace("'", "''") + "'"


def obter_contagem(
    conn: duckdb.DuckDBPyConnection,
    sql: str,
) -> int:
    """Executa uma consulta COUNT(*) e retorna um inteiro."""
    resultado = conn.execute(sql).fetchone()

    if resultado is None:
        raise RuntimeError("A consulta de contagem não retornou nenhuma linha.")

    valor = resultado[0]

    if not isinstance(valor, int):
        raise TypeError(
            f"A contagem deveria ser um inteiro, mas retornou {type(valor).__name__}."
        )

    return valor


# ============================================================
# VALIDAÇÃO DO ARQUIVO NO R2
# ============================================================


def main() -> int:
    account_id = os.getenv("R2_ACCOUNT_ID", "").strip()
    access_key = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()

    variaveis_ausentes = [
        nome
        for nome, valor in [
            ("R2_ACCOUNT_ID", account_id),
            ("R2_ACCESS_KEY_ID", access_key),
            ("R2_SECRET_ACCESS_KEY", secret_key),
        ]
        if not valor
    ]

    if variaveis_ausentes:
        print(
            "ERRO: variáveis ausentes no arquivo .env: " + ", ".join(variaveis_ausentes)
        )
        return 1

    endpoint = f"{account_id}.r2.cloudflarestorage.com"

    conn: duckdb.DuckDBPyConnection | None = None

    try:
        print(f"Arquivo .env: {ENV_FILE}")
        print(f"Arquivo remoto: {REMOTE_PATH}")
        print("Conectando ao Cloudflare R2...")

        conn = duckdb.connect(database=":memory:")

        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")

        # Configurações do Cloudflare R2.
        # Os valores são escapados antes de serem inseridos no SQL.
        conn.execute(f"SET s3_endpoint = {sql_literal(endpoint)}")
        conn.execute(f"SET s3_access_key_id = {sql_literal(access_key)}")
        conn.execute(f"SET s3_secret_access_key = {sql_literal(secret_key)}")
        conn.execute("SET s3_url_style = 'path'")
        conn.execute("SET s3_region = 'auto'")

        # 1. Verifica se o arquivo pode ser acessado e conta os registros.
        print("\n[1/4] Contando os registros remotos...")

        count_remoto = obter_contagem(
            conn,
            f"SELECT COUNT(*) FROM read_parquet({sql_literal(REMOTE_PATH)})",
        )

        print(f"Total de registros: {count_remoto:,}")

        # 2. Conta os estabelecimentos ativos.
        print("\n[2/4] Contando os estabelecimentos ativos...")

        ativas = obter_contagem(
            conn,
            f"""
            SELECT COUNT(*)
            FROM read_parquet({sql_literal(REMOTE_PATH)})
            WHERE situacao_cadastral = '02'
            """,
        )

        print(f"Estabelecimentos ativos (situação 02): {ativas:,}")

        # 3. Exibe o esquema do Parquet.
        print("\n[3/4] Verificando o esquema do arquivo...")

        esquema = conn.execute(
            f"""
            DESCRIBE
            SELECT *
            FROM read_parquet({sql_literal(REMOTE_PATH)})
            """
        ).fetchall()

        for coluna in esquema:
            nome_coluna = coluna[0]
            tipo_coluna = coluna[1]
            print(f"  {nome_coluna}: {tipo_coluna}")

        # 4. Exibe uma amostra dos registros.
        print("\n[4/4] Exibindo até 10 registros...")

        amostra = conn.execute(
            f"""
            SELECT *
            FROM read_parquet({sql_literal(REMOTE_PATH)})
            LIMIT 10
            """
        ).fetchdf()

        if amostra.empty:
            print("O arquivo foi acessado, mas não contém registros.")
        else:
            print(amostra.to_string(index=False))

        print("\nValidação concluída com sucesso.")
        return 0

    except duckdb.Error as erro:
        print(f"\nERRO DO DUCKDB: {erro}")
        return 1

    except (OSError, RuntimeError, TypeError, ValueError) as erro:
        print(f"\nERRO NA VALIDAÇÃO: {erro}")
        return 1

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
