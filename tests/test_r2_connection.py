import os

import pytest

from app.core.database import db_client

# Verifica se as credenciais reais do R2 estão disponíveis e não vazias/espaços
has_r2_creds = all(
    (val := os.getenv(var)) and val.strip()
    for var in [
        "R2_ACCOUNT_ID",
        "R2_TOKEN_VALUE",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
    ]
)

# Se não temos credenciais reais, testamos a ausência com skip interno
# Removido o pytestmark de nível de módulo para que o teste seja explicitamente listado e pulado.


@pytest.mark.integration
def test_r2_duckdb_connection_and_schemas():
    """Testa a conexão do DuckDB com o Cloudflare R2 e inspeciona as tabelas"""
    if not has_r2_creds:
        pytest.skip("Credenciais R2 não configuradas")

    # Garante que o cliente está conectado
    if db_client.conn is None:
        db_client.connect()

    assert db_client.conn is not None, "Falha ao conectar no DuckDB"

    # Mapeamento de caminhos: para o teste do loop, estabelecimentos usa uma partição representativa (uf=BA)
    # para evitar a listagem recursiva pesada em todas as 28 UFs durante a checagem individual.
    # A verificação geral continua garantindo a presença e leitura de dados reais no R2.
    caminhos = {
        "cnaes": "s3://buscafri-data/cnaes/*.parquet",
        "empresas": "s3://buscafri-data/empresas/*.parquet",
        "estabelecimentos": "s3://buscafri-data/estabelecimentos/uf=BA/*.parquet",
        "motivos": "s3://buscafri-data/motivos/*.parquet",
        "municipios": "s3://buscafri-data/municipios/*.parquet",
        "naturezas": "s3://buscafri-data/naturezas/*.parquet",
        "paises": "s3://buscafri-data/paises/*.parquet",
        "qualificacoes": "s3://buscafri-data/qualificacoes/*.parquet",
        "simples": "s3://buscafri-data/simples/*.parquet",
        "socios": "s3://buscafri-data/socios/*.parquet",
    }

    for pasta, path in caminhos.items():
        # Lê uma amostra diretamente. Essa única query valida que o caminho existe,
        # que o protocolo HTTPFS/S3 funciona e que há dados retornados.
        df = db_client.query(f"SELECT * FROM '{path}' LIMIT 5")
        assert df is not None
        assert not df.empty, f"Nenhum dado retornado para {pasta} em {path}"

        # Verificação de colunas obrigatórias via DataFrame retornado (substitui o DESCRIBE redundante)
        if pasta == "empresas":
            colunas_presentes = list(df.columns)
            assert "cnpj_basico" in colunas_presentes, (
                "Coluna cnpj_basico ausente em empresas"
            )
            assert "razao_social" in colunas_presentes, (
                "Coluna razao_social ausente em empresas"
            )

    # Teste de JOIN entre empresas e estabelecimentos (chave cnpj_basico)
    # Usamos a partição representativa uf=BA para evitar que o DuckDB faça o scan
    # de metadados das 28 partições do R2 apenas para retornar 10 registros.
    caminho_estabelecimentos_ba = "s3://buscafri-data/estabelecimentos/uf=BA/*.parquet"
    join_query = f"""
        SELECT 
            e.cnpj_basico, 
            e.razao_social, 
            t.cnpj_ordem, 
            t.cnpj_dv 
        FROM '{caminhos["empresas"]}' e
        JOIN '{caminho_estabelecimentos_ba}' t ON e.cnpj_basico = t.cnpj_basico
        LIMIT 10
    """
    join_df = db_client.query(join_query)

    assert not join_df.empty, (
        "O JOIN entre empresas e estabelecimentos falhou ou retornou vazio"
    )
    assert "cnpj_basico" in join_df.columns
    assert "razao_social" in join_df.columns
    assert "cnpj_ordem" in join_df.columns
    assert "cnpj_dv" in join_df.columns
