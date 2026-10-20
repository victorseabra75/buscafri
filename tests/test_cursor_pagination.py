import base64
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# Configurar ambiente para testes
os.environ["ESTAB_PATH"] = str(Path("data/particionado/estabelecimentos").resolve())
os.environ["EMPRESAS_PATH"] = str(Path("data/processed_corrigido/empresas").resolve())
os.environ["APP_ENV"] = "testing"

client = TestClient(app)


def test_keyset_pagination_flow():
    """Testa o fluxo completo de paginação keyset com dados determinísticos."""
    uf = "BA"
    limit = 20  # Respeitando limite mínimo de 20
    # Primeira página
    response = client.get(f"/api/v1/busca?uf={uf}&limit={limit}")
    assert response.status_code == 200
    data1 = response.json()
    assert len(data1["data"]) <= limit

    if len(data1["data"]) == limit and data1["next_cursor"]:
        assert data1["next_cursor"] is not None

        # Segunda página usando o cursor
        cursor = data1["next_cursor"]
        response2 = client.get(f"/api/v1/busca?uf={uf}&limit={limit}&cursor={cursor}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["data"]) <= limit

        # Verificar que não há repetição
        def get_id(item):
            # Identidade única baseada na chave de ordenação
            return f"{item['municipio']}-{item['cnae_fiscal_principal']}-{item['cnpj_basico']}"

        ids1 = {get_id(item) for item in data1["data"]}
        ids2 = {get_id(item) for item in data2["data"]}
        assert ids1.isdisjoint(ids2), "Duplicação detectada entre páginas."


def test_invalid_cursor():
    """Testa comportamento com cursor inválido ou malformado."""
    response = client.get("/api/v1/busca?uf=BA&cursor=dGhpcy1pcy1ub3QtYS1qc29u")
    assert response.status_code == 400
    assert "Cursor inválido" in response.json()["detail"]


def test_pagination_limit_range():
    """Valida os limites da API (20-100)."""
    # Abaixo do limite
    resp_low = client.get("/api/v1/busca?uf=BA&limit=19")
    assert resp_low.status_code == 422

    # Acima do limite
    resp_high = client.get("/api/v1/busca?uf=BA&limit=101")
    assert resp_high.status_code == 422

    # Dentro do range
    resp_ok = client.get("/api/v1/busca?uf=BA&limit=20")
    assert resp_ok.status_code == 200


def test_incompatible_cursor_filters():
    """Testa cursor gerado para um conjunto de filtros sendo usado em outro."""
    # Gera cursor para UF=BA
    resp_ba = client.get("/api/v1/busca?uf=BA&limit=20")
    data_ba = resp_ba.json()
    if not data_ba.get("next_cursor"):
        pytest.skip("Não há registros suficientes em BA para gerar cursor")

    cursor_ba = data_ba["next_cursor"]

    # Tenta usar o cursor de BA na busca de SP
    resp_sp = client.get(f"/api/v1/busca?uf=SP&limit=20&cursor={cursor_ba}")
    assert resp_sp.status_code == 400
    assert "Cursor inválido ou incompatível" in resp_sp.json()["detail"]


def test_signed_cursor_tampering():
    """Testa se a alteração manual do cursor é detectada pela assinatura."""
    resp = client.get("/api/v1/busca?uf=BA&limit=20")
    data = resp.json()
    if not data.get("next_cursor"):
        pytest.skip("Não há registros suficientes em BA para gerar cursor")

    cursor = data["next_cursor"]

    # O cursor é base64url(payload|sig).
    padding = 4 - (len(cursor) % 4)
    if padding < 4:
        cursor += "=" * padding

    decoded = base64.urlsafe_b64decode(cursor).decode("utf-8")
    payload, sig = decoded.rsplit("|", 1)

    payload_dict = json.loads(payload)
    payload_dict["m"] = "9999"  # Município inexistente
    new_payload = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)

    tampered_token = f"{new_payload}|{sig}"
    tampered_cursor = (
        base64.urlsafe_b64encode(tampered_token.encode()).decode().rstrip("=")
    )

    resp_tampered = client.get(f"/api/v1/busca?uf=BA&limit=20&cursor={tampered_cursor}")
    assert resp_tampered.status_code == 400
    assert "Cursor inválido" in resp_tampered.json()["detail"]


def test_pagination_end():
    """Testa o comportamento ao chegar ao fim dos resultados."""
    resp = client.get("/api/v1/busca?uf=AC&limit=100")
    data = resp.json()

    assert resp.status_code == 200
    # Valida que total_count é opcional (None se include_total=False)
    assert data["total_count"] is None

    # Se a quantidade de dados for menor que o limite, next_cursor deve ser None
    if len(data["data"]) < 100:
        assert data["next_cursor"] is None


def test_pagination_include_total():
    """Valida o funcionamento do parâmetro include_total."""
    resp = client.get("/api/v1/busca?uf=AC&limit=20&include_total=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] is not None
    assert isinstance(data["total_count"], int)
