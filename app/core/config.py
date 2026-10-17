from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Permite carregar do arquivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Variáveis gerais
    APP_ENV: str = "development"  # development, testing, production
    APP_SECRET_KEY: str = "dev-secret-keep-it-safe"

    # R2 Buckets
    R2_BUCKET_NAME: str = "buscafri-data"
    R2_PATH: str = f"s3://{R2_BUCKET_NAME}"

    # Caminhos padrão locais para Desenvolvimento/Teste
    # Se estiver em produção, esses caminhos padrão não devem ser usados.
    ESTAB_PATH: str = "data/particionado/estabelecimentos"
    EMPRESAS_PATH: str = "data/processed_corrigido/empresas"

    def model_post_init(self, /, __context: Any) -> None:
        # Se for produção, garantimos que os caminhos apontam para o S3
        # caso as variáveis de ambiente não tenham sido injetadas explicitamente.
        if self.APP_ENV == "production":
            if self.ESTAB_PATH == "data/particionado/estabelecimentos":
                self.ESTAB_PATH = f"{self.R2_PATH}/estabelecimentos"
            if self.EMPRESAS_PATH == "data/processed_corrigido/empresas":
                self.EMPRESAS_PATH = f"{self.R2_PATH}/empresas"


settings = Settings()
