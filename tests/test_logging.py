import logging

from fastapi.testclient import TestClient

from app.core.database import db_client
from app.main import app

client = TestClient(app)


def test_database_connection_error_logs_error(caplog, monkeypatch):
    """Verifica se falha de conexão do DuckDB gera log de nível ERROR sem vazar segredos.

    Simulamos uma falha em duckdb.connect para que o bloco try/except em connect()
    seja acionado, garantindo que o erro seja tratado e registrado via logging.
    """
    import duckdb

    from app.core.database import DuckDBClient

    SECRET_SENTINEL = "SECRET_TOKEN_CONNECTION_FAIL_123"

    def mock_duckdb_connect(*args, **kwargs):
        raise RuntimeError(f"DuckDB connection failure with {SECRET_SENTINEL}")

    monkeypatch.setattr(duckdb, "connect", mock_duckdb_connect)

    with caplog.at_level(logging.ERROR):
        # Instanciar o cliente força a execução do __init__ e do connect()
        _ = DuckDBClient()

    # Verifica que o erro foi capturado e logado corretamente
    assert any(record.levelname == "ERROR" for record in caplog.records)
    assert "Erro ao conectar ao DuckDB" in caplog.text
    # Garante que dados sensíveis/sentinela não vazaram para o log
    assert SECRET_SENTINEL not in caplog.text


def test_busca_endpoint_logging_and_response(caplog, monkeypatch):
    """Verifica se o endpoint de busca loga erro e retorna 500 sem vazar dados sensíveis."""
    SECRET_SENTINEL = "SECRET_TOKEN_BUSCA_999"

    def mock_query_params(*args, **kwargs):
        raise RuntimeError(f"Database error with {SECRET_SENTINEL}")

    monkeypatch.setattr(db_client, "query_params", mock_query_params)

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/v1/busca?uf=BA")

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno ao processar a consulta"

    # A resposta HTTP nunca deve conter a sentinela
    assert SECRET_SENTINEL not in response.text

    # Validações de logging
    assert "Erro inesperado na busca" in caplog.text
    # O requisito de segurança exige que a sentinela não apareça nos logs
    assert SECRET_SENTINEL not in caplog.text


def test_exportar_dados_logging_and_response(caplog, monkeypatch):
    """Verifica se o endpoint de exportação loga erro e retorna 500 sem vazar dados sensíveis."""
    SECRET_SENTINEL = "SECRET_TOKEN_EXPORT_888"

    def mock_query_params(*args, **kwargs):
        raise RuntimeError(f"Export error with {SECRET_SENTINEL}")

    monkeypatch.setattr(db_client, "query_params", mock_query_params)

    with caplog.at_level(logging.ERROR):
        response = client.get("/api/v1/exportar/csv?uf=BA")

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno ao processar a exportação"

    # A resposta HTTP nunca deve conter a sentinela
    assert SECRET_SENTINEL not in response.text

    # Validações de logging
    assert "Erro inesperado na exportação" in caplog.text
    # O requisito de segurança exige que a sentinela não apareça nos logs
    assert SECRET_SENTINEL not in caplog.text
