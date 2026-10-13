import logging
import os
from typing import Any

import duckdb
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DuckDBClient:
    def __init__(self):
        self.conn: duckdb.DuckDBPyConnection | None = None
        self.connect()

    def connect(self) -> None:
        try:
            self.conn = duckdb.connect(
                database=":memory:",
                read_only=False,
            )

            # Instala e carrega extensão para leitura S3 / HTTPS
            self.conn.execute("INSTALL httpfs;")
            self.conn.execute("LOAD httpfs;")

            # Credenciais Cloudflare R2
            account_id = os.getenv("R2_ACCOUNT_ID")
            if not account_id:
                raise ValueError(
                    "A variável de ambiente R2_ACCOUNT_ID não está definida."
                )

            token_value = os.getenv("R2_TOKEN_VALUE")
            if not token_value:
                raise ValueError(
                    "A variável de ambiente R2_TOKEN_VALUE não está definida."
                )

            endpoint = os.getenv(
                "R2_ENDPOINT",
                f"https://{account_id}.r2.cloudflarestorage.com",
            )

            clean_endpoint = endpoint.replace("https://", "").replace("http://", "")

            access_key = os.getenv("R2_ACCESS_KEY_ID")
            if not access_key:
                raise ValueError(
                    "A variável de ambiente R2_ACCESS_KEY_ID não está definida."
                )

            secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
            if not secret_key:
                raise ValueError(
                    "A variável de ambiente R2_SECRET_ACCESS_KEY não está definida."
                )

            self.conn.execute(f"SET s3_endpoint='{clean_endpoint}';")
            self.conn.execute(f"SET s3_access_key_id='{access_key}';")
            self.conn.execute(f"SET s3_secret_access_key='{secret_key}';")
            self.conn.execute("SET s3_url_style='path';")
            self.conn.execute("SET s3_region='auto';")

            logger.info("Conectado ao DuckDB com suporte ao Cloudflare R2 S3")

        except Exception:  # noqa: BLE001
            self.conn = None
            logger.error("Erro ao conectar ao DuckDB")

    def query(self, sql: str):
        if self.conn is None:
            self.connect()

        if self.conn is None:
            raise RuntimeError("Não foi possível conectar ao DuckDB.")

        return self.conn.execute(sql).df()

    def query_params(
        self,
        sql: str,
        params: list[Any],
    ):
        if self.conn is None:
            self.connect()

        if self.conn is None:
            raise RuntimeError("Não foi possível conectar ao DuckDB.")

        return self.conn.execute(sql, params).df()


db_client = DuckDBClient()
