import json
import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.observability import (
    ACCESS_LOGGER_NAME,
    HttpObservabilityMiddleware,
    setup_access_logger,
)


@pytest.fixture
def temp_log_dir(tmp_path):
    """Cria um diretório temporário para logs de teste."""
    return tmp_path / "logs"


@pytest.fixture
def test_app(temp_log_dir):
    """Cria uma aplicação FastAPI mínima para testar o middleware de observabilidade."""
    app = FastAPI()
    log_file = temp_log_dir / "test_access.jsonl"

    # Configura o logger para gravar no arquivo temporário
    setup_access_logger(
        log_file_path=log_file,
        max_bytes=1024 * 1024,
        backup_count=1,
    )

    app.add_middleware(HttpObservabilityMiddleware)

    # Rota de sucesso
    @app.get("/success")
    async def success():
        return {"status": "ok"}

    # Rota de erro tratado (400)
    @app.get("/error-400")
    async def error_400():
        raise HTTPException(status_code=400, detail="Bad Request")

    # Rota de exceção não tratada (500)
    @app.get("/exception")
    async def exception():
        raise RuntimeError("Erro interno simulado")

    # Rota de busca simulada (para testar extração de metadados)
    @app.get("/api/v1/busca")
    async def mock_busca(
        uf: str | None = None,
        municipio: str | None = None,
    ):
        return {"results": []}

    return app, log_file


def test_observability_success_log(test_app):
    app, log_file = test_app
    client = TestClient(app)

    response = client.get("/success")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

    # Verifica o conteúdo do log
    content = log_file.read_text().strip()
    log_entry = json.loads(content)

    assert log_entry["method"] == "GET"
    assert log_entry["route"] == "/success"
    assert log_entry["status_code"] == 200
    assert log_entry["result"] == "success"
    assert log_entry["error_class"] is None
    assert "timestamp" in log_entry
    assert "request_id" in log_entry
    assert "duration_ms" in log_entry


def test_observability_404_log(test_app):
    app, log_file = test_app
    client = TestClient(app)

    response = client.get("/not-found")
    assert response.status_code == 404

    content = log_file.read_text().strip()
    log_entry = json.loads(content)

    assert log_entry["route"] == "/not-found"
    assert log_entry["status_code"] == 404
    assert log_entry["result"] == "error"


def test_observability_exception_log(test_app):
    app, log_file = test_app
    client = TestClient(app)

    # O TestClient do FastAPI por padrão relança exceções não tratadas
    # se raise_server_exceptions for True (default).
    with pytest.raises(RuntimeError):
        client.get("/exception")

    content = log_file.read_text().strip()
    log_entry = json.loads(content)

    assert log_entry["route"] == "/exception"
    assert log_entry["status_code"] == 500
    assert log_entry["result"] == "error"
    assert log_entry["error_class"] == "RuntimeError"


def test_observability_search_metadata_sanitization(test_app):
    app, log_file = test_app
    client = TestClient(app)

    # Faz uma busca com filtros válidos e um parâmetro sensível proibido (cnpj)
    # e um parâmetro desconhecido
    client.get("/api/v1/busca?uf=ba&municipio=1234&cnpj=12345678000199&unknown=val")

    content = log_file.read_text().strip()
    log_entry = json.loads(content)

    assert log_entry["route"] == "/api/v1/busca"
    search = log_entry["search"]

    assert search["uf"] == "BA"  # Normalizado para upper
    assert search["municipio"] == "1234"
    assert search["ativa"] is True  # Valor padrão

    # Campos proibidos ou desconhecidos não devem aparecer
    assert "cnpj" not in search
    assert "unknown" not in search
    assert "cnpj" not in content
    assert "12345678000199" not in content


def test_observability_rotation(temp_log_dir):
    """Verifica se a rotação de arquivos funciona corretamente."""
    log_file = temp_log_dir / "rotate.jsonl"

    # Logger com limite minúsculo para forçar rotação rápida
    logger = setup_access_logger(
        log_file_path=log_file,
        max_bytes=100,  # 100 bytes
        backup_count=1,
    )

    # Grava mensagens até rotacionar
    msg = {"test": "data"}
    for _ in range(10):
        logger.info(msg)

    assert log_file.exists()
    backup_file = temp_log_dir / "rotate.jsonl.1"
    assert backup_file.exists()


def test_observability_logging_failure_safety(test_app, monkeypatch):
    """Garante que falhas no logger não quebram a resposta da API."""
    app, _ = test_app
    client = TestClient(app)

    def mock_info(*args, **kwargs):
        raise RuntimeError("Disk full or something")

    # Monkeypatch no logger específico
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    monkeypatch.setattr(logger, "info", mock_info)

    # A requisição deve completar com sucesso apesar da falha no log
    response = client.get("/success")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
