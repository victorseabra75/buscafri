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
    """Testa o fluxo completo de paginação keyset."""
    uf = "BA"
    limit = 5

    # Primeira página
    response = client.get(f"/api/v1/busca?uf={uf}&limit={limit}")
    assert response.status_code == 200
    data1 = response.json()
    assert len(data1["data"]) <= limit
    assert data1["next_cursor"] is not None

    # Segunda página usando o cursor
    cursor = data1["next_cursor"]
    response = client.get(f"/api/v1/busca?uf={uf}&limit={limit}&cursor={cursor}")
    assert response.status_code == 200
    data2 = response.json()
    assert len(data2["data"]) <= limit

    # Verificar que não há repetição
    ids1 = {item["cnpj_basico"] for item in data1["data"]}
    ids2 = {item["cnpj_basico"] for item in data2["data"]}
    intersection = ids1.intersection(ids2)
    assert not intersection, f"Registros duplicados entre páginas: {intersection}"


def test_invalid_cursor():
    """Testa comportamento com cursor inválido ou malformado."""
    # Base64 válido mas conteúdo lixo
    response = client.get("/api/v1/busca?uf=BA&cursor=dGhpcy1pcy1ub3QtYS1qc29u")
    assert response.status_code == 400
    assert "Cursor inválido" in response.json()["detail"]


def test_incompatible_cursor_filters():
    """Testa cursor gerado para um conjunto de filtros sendo usado em outro."""
    # Gera cursor para UF=BA
    resp_ba = client.get("/api/v1/busca?uf=BA&limit=1")
    cursor_ba = resp_ba.json()["next_cursor"]

    # Tenta usar o cursor de BA na busca de SP
    resp_sp = client.get(f"/api/v1/busca?uf=SP&cursor={cursor_ba}")
    assert resp_sp.status_code == 400
    assert "Cursor inválido ou incompatível" in resp_sp.json()["detail"]


def test_signed_cursor_tampering():
    """Testa se a alteração manual do cursor é detectada pela assinatura."""
    resp = client.get("/api/v1/busca?uf=BA&limit=1")
    cursor = resp.json()["next_cursor"]

    # O cursor é base64url(payload|sig). Vamos tentar decodificar, alterar o payload e re-encodar sem mudar a sig.
    import base64

    decoded = base64.urlsafe_b64decode(cursor + "==").decode()
    payload, sig = decoded.rsplit("|", 1)

    # Altera o município no payload
    import json

    payload_dict = json.loads(payload)
    payload_dict["m"] = "9999"  # Município inexistente
    new_payload = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)

    tampered_token = f"{new_payload}|{sig}"
    tampered_cursor = (
        base64.urlsafe_b64encode(tampered_token.encode()).decode().rstrip("=")
    )

    resp_tampered = client.get(f"/api/v1/busca?uf=BA&cursor={tampered_cursor}")
    assert resp_tampered.status_code == 400
    assert "Cursor inválido" in resp_tampered.json()["detail"]


def test_pagination_end():
    """Testa o comportamento ao chegar ao fim dos resultados."""
    # Vamos usar um município/CNAE com poucos registros para chegar ao fim rápido
    # Ex: UF=AC, CNAE 9492800 (conforme check_ba_data.py vimos alguns códigos)
    # Na verdade, vamos apenas filtrar algo bem específico.
    resp = client.get("/api/v1/busca?uf=AC&limit=100")
    data = resp.json()

    if not data["next_cursor"]:
        pytest.skip("Não há registros suficientes em AC para testar fim de paginação")

    # Navega até o fim (se possível) ou apenas valida que next_cursor some se pegarmos tudo
    total = data["total_count"]
    if total <= 100:
        assert data["next_cursor"] is None or len(data["data"]) < 100
