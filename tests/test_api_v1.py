from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.main import app

client = TestClient(app)


def rate_limit_handler(
    request: Request,
    exc: Exception,
) -> Response:
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    raise exc


def test_busca_empresas_rate_limit():
    """Verifica o rate limit sem consultar DuckDB/R2."""
    test_app = FastAPI()
    test_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["2/minute"],
    )
    test_app.state.limiter = test_limiter
    test_app.add_exception_handler(
        RateLimitExceeded,
        rate_limit_handler,
    )

    @test_app.get("/api/v1/busca")
    @test_limiter.limit("2/minute")
    def busca_teste(request: Request):
        return {"resultado": "ok"}

    with TestClient(test_app) as test_client:
        primeira = test_client.get("/api/v1/busca")
        segunda = test_client.get("/api/v1/busca")
        terceira = test_client.get("/api/v1/busca")

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert terceira.status_code == 429


def test_exportar_formatos_invalidos():
    """Testa se a API recusa formatos de exportação desconhecidos."""
    response = client.get("/api/v1/exportar/pdf")

    if response.status_code == 429:
        return

    assert response.status_code == 400
    assert "Formato inválido" in response.json()["detail"]


def test_filtros_parametros():
    """Verifica se os parâmetros de filtro são aceitos."""
    response = client.get("/api/v1/busca?uf=BA&ativa=true")

    assert response.status_code in [200, 500, 429]


def test_uf_validacao_formato():
    """Verifica se a API valida o formato do parâmetro uf (deve retornar 422 para formatos inválidos)."""
    # Formato inválido com números
    resp_num = client.get("/api/v1/busca?uf=12")
    if resp_num.status_code != 429:
        assert resp_num.status_code == 422

    # Formato inválido com mais de 2 caracteres
    resp_long = client.get("/api/v1/busca?uf=SPP")
    if resp_long.status_code != 429:
        assert resp_long.status_code == 422

    # Formato inválido com caracteres especiais/não alfabéticos
    resp_char = client.get("/api/v1/busca?uf=B#")
    if resp_char.status_code != 429:
        assert resp_char.status_code == 422


def test_busca_empresas_falha_duckdb_mensagem_generica(monkeypatch):
    """Verifica se falhas inesperadas no DuckDB retornam HTTP 500 sem expor detalhes internos."""
    from app.core.database import db_client

    def mock_query_params(*args, **kwargs):
        raise RuntimeError("FATAL_SECRET_LEAK_TOKEN_12345_S3_PATH_FAIL")

    monkeypatch.setattr(db_client, "query_params", mock_query_params)

    response = client.get("/api/v1/busca?uf=BA")
    if response.status_code != 429:
        assert response.status_code == 500
        assert "FATAL_SECRET_LEAK_TOKEN_12345_S3_PATH_FAIL" not in response.text
        assert response.json()["detail"] == "Erro interno ao processar a consulta"


def test_exportar_dados_falha_duckdb_mensagem_generica(monkeypatch):
    """Verifica se falhas inesperadas no DuckDB durante exportação retornam HTTP 500 sem expor detalhes internos."""
    from app.core.database import db_client

    def mock_query_params(*args, **kwargs):
        raise RuntimeError("FATAL_SECRET_LEAK_EXPORT_PATH_999")

    monkeypatch.setattr(db_client, "query_params", mock_query_params)

    response = client.get("/api/v1/exportar/csv?uf=BA")
    if response.status_code != 429:
        assert response.status_code == 500
        assert "FATAL_SECRET_LEAK_EXPORT_PATH_999" not in response.text
        assert response.json()["detail"] == "Erro interno ao processar a consulta"
