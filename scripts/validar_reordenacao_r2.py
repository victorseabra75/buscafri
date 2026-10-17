import logging
import os
from pathlib import Path

import duckdb
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ORDER_COLUMNS = (
    "municipio",
    "cnae_fiscal_principal",
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
)


def configure_r2(con: duckdb.DuckDBPyConnection) -> None:
    """Configura o DuckDB para acessar o Cloudflare R2."""
    load_dotenv(dotenv_path=Path(".env"), override=False)

    account_id = os.getenv("R2_ACCOUNT_ID")
    token_value = os.getenv("R2_TOKEN_VALUE")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")

    if not account_id:
        raise ValueError("R2_ACCOUNT_ID não está configurado.")
    if not token_value:
        raise ValueError("R2_TOKEN_VALUE não está configurado.")
    if not access_key:
        raise ValueError("R2_ACCESS_KEY_ID não está configurado.")
    if not secret_key:
        raise ValueError("R2_SECRET_ACCESS_KEY não está configurado.")

    endpoint = os.getenv(
        "R2_ENDPOINT",
        f"https://{account_id}.r2.cloudflarestorage.com",
    )

    clean_endpoint = (
        endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
    )

    con.execute("INSTALL httpfs")
    con.execute("LOAD httpfs")

    # Os valores são passados como parâmetros quando suportado.
    # Para as configurações SET, os valores são escapados como literais SQL.
    def sql_literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    con.execute(f"SET s3_endpoint={sql_literal(clean_endpoint)}")
    con.execute(f"SET s3_access_key_id={sql_literal(access_key)}")
    con.execute(f"SET s3_secret_access_key={sql_literal(secret_key)}")
    con.execute("SET s3_url_style='path'")
    con.execute("SET s3_region='auto'")

    # token_value é validado porque faz parte da configuração existente
    # do projeto, mas não é usado como chave S3 nesta configuração.
    del token_value


def fetch_scalar(
    con: duckdb.DuckDBPyConnection,
    sql: str,
    params: list,
) -> int:
    """Executa uma consulta escalar e valida seu resultado."""
    result = con.execute(sql, params).fetchone()

    if result is None:
        raise RuntimeError("A consulta não retornou resultado.")

    value = result[0]

    if not isinstance(value, int):
        raise TypeError("O resultado da consulta não é um inteiro.")

    return value


def validate_integrity(local_file: str, remote_url: str) -> bool:
    """Compara esquema, contagem, ordenação física e conteúdo dos Parquet."""
    con = duckdb.connect()

    try:
        # Configurar o acesso S3 antes de ler o objeto remoto.
        configure_r2(con)

        if not Path(local_file).is_file():
            print(f"Falha: arquivo local não encontrado: {local_file}")
            return False

        # 1. Verificar se os arquivos podem ser lidos.
        for label, path in (
            ("local", local_file),
            ("remoto", remote_url),
        ):
            try:
                con.execute(
                    "SELECT 1 FROM read_parquet(?) LIMIT 1",
                    [path],
                ).fetchone()
            except duckdb.Error as exc:
                print(f"Falha ao ler o arquivo {label}: {exc}")
                return False

        # 2. Comparar o esquema.
        local_schema = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [local_file],
        ).fetchall()

        remote_schema = con.execute(
            "DESCRIBE SELECT * FROM read_parquet(?)",
            [remote_url],
        ).fetchall()

        local_columns = [(row[0], row[1]) for row in local_schema]
        remote_columns = [(row[0], row[1]) for row in remote_schema]

        if local_columns != remote_columns:
            print("Falha: esquema divergente.")
            print(f"Local:  {local_columns}")
            print(f"Remoto: {remote_columns}")
            return False

        print("OK: esquema compatível.")

        # 3. Comparar a quantidade de registros.
        local_count = fetch_scalar(
            con,
            "SELECT COUNT(*) FROM read_parquet(?)",
            [local_file],
        )

        remote_count = fetch_scalar(
            con,
            "SELECT COUNT(*) FROM read_parquet(?)",
            [remote_url],
        )

        if local_count != remote_count:
            print(
                "Falha: contagem divergente "
                f"(local={local_count:,}; remoto={remote_count:,})."
            )
            return False

        print(f"OK: {local_count:,} registros em ambos os arquivos.")

        # 4. Verificar as colunas necessárias para a ordenação.
        column_names = {row[0] for row in local_schema}
        missing_columns = set(ORDER_COLUMNS) - column_names

        if missing_columns:
            print(f"Falha: colunas de ordenação ausentes: {sorted(missing_columns)}")
            return False

        # 5. Validar a ordenação física do arquivo remoto.
        quoted_columns = [f'"{col}"' for col in ORDER_COLUMNS]

        lag_columns = ",\n".join(
            f'LAG("{col}") OVER (ORDER BY file_row_number) AS "prev_{col}"'
            for col in ORDER_COLUMNS
        )

        equal_prefix = []
        inversion_terms = []

        for col in ORDER_COLUMNS:
            prev = f'"prev_{col}"'
            curr = f'"{col}"'

            greater = (
                f"(({prev} IS NULL AND {curr} IS NOT NULL) OR "
                f"({prev} IS NOT NULL AND {curr} IS NOT NULL "
                f"AND {prev} > {curr}))"
            )

            prefix = " AND ".join(equal_prefix)

            if prefix:
                inversion_terms.append(f"({prefix} AND {greater})")
            else:
                inversion_terms.append(greater)

            equal_prefix.append(f"{prev} IS NOT DISTINCT FROM {curr}")

        inversion_condition = " OR ".join(inversion_terms)

        order_check_sql = f"""
            WITH ordered_rows AS (
                SELECT
                    file_row_number,
                    {", ".join(quoted_columns)},
                    {lag_columns}
                FROM read_parquet(?, file_row_number = true)
            )
            SELECT COUNT(*)
            FROM ordered_rows
            WHERE file_row_number > 0
              AND ({inversion_condition})
        """

        inversions = fetch_scalar(
            con,
            order_check_sql,
            [remote_url],
        )

        if inversions > 0:
            print(
                "Falha: arquivo remoto fora da ordenação esperada. "
                f"Inversões encontradas: {inversions:,}."
            )
            return False

        print("OK: ordenação física dos registros validada.")

        # 6. Comparar todo o conteúdo nos dois sentidos.
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
            ) AS differences
        """

        differences = fetch_scalar(
            con,
            diff_sql,
            [
                local_file,
                remote_url,
                remote_url,
                local_file,
            ],
        )

        if differences != 0:
            print(
                "Falha: conteúdo divergente. "
                f"Registros nas diferenças: {differences:,}."
            )
            return False

        print("OK: conteúdo integral idêntico, incluindo duplicatas.")
        print("Sucesso: validação de integridade aprovada.")
        return True

    except (
        duckdb.Error,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"Erro durante a validação: {type(exc).__name__}: {exc}")
        return False

    finally:
        con.close()


if __name__ == "__main__":
    path = "data/reordenado/estabelecimentos/uf=AC/data_0.parquet"

    if not Path(path).is_file():
        print(f"Arquivo local não encontrado: {path}")
    elif validate_integrity(
        path,
        "s3://buscafri-data/estabelecimentos/uf=AC/data_0.parquet",
    ):
        print("Resultado final: APROVADO.")
    else:
        print("Resultado final: REPROVADO.")
