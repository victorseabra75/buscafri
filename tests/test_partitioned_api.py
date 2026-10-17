import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

# Certificar que o caminho de teste é o particionado
os.environ["ESTAB_PATH"] = str(Path("data/particionado/estabelecimentos").resolve())

client = TestClient(app)


def test_busca_uf_ba():
    response = client.get("/api/v1/busca?uf=BA")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["total_count"] > 0
    for item in data["data"]:
        assert item["uf"] == "BA"


def test_busca_uf_sp():
    response = client.get("/api/v1/busca?uf=SP")
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert item["uf"] == "SP"


def test_busca_uf_inexistente():
    response = client.get("/api/v1/busca?uf=ZZ")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 0
    assert data["data"] == []


def test_busca_uf_municipio():
    response = client.get("/api/v1/busca?uf=BA&municipio=292740")
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert item["uf"] == "BA"
        assert item["municipio"] == "292740"


def test_busca_uf_cnae():
    response = client.get("/api/v1/busca?uf=BA&cnae=8630503")
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]:
        assert item["uf"] == "BA"
        assert item["cnae_fiscal_principal"] == "8630503"


def test_busca_paginacao():
    response = client.get("/api/v1/busca?uf=BA&page=1&limit=10")
    assert response.status_code == 200
    data1 = response.json()
    assert len(data1["data"]) <= 10
    assert "next_cursor" in data1

    if data1["next_cursor"]:
        response = client.get(
            f"/api/v1/busca?uf=BA&limit=10&cursor={data1['next_cursor']}"
        )
        assert response.status_code == 200
        data2 = response.json()
        assert "data" in data2
        # Verifica se o cursor realmente avançou (não é igual ao anterior)
        assert data2["data"][0]["cnpj_basico"] != data1["data"][0]["cnpj_basico"]


def test_exportar_csv():
    response = client.get("/api/v1/exportar/csv?uf=BA")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert len(response.content) > 0


def test_exportar_xlsx():
    response = client.get("/api/v1/exportar/xlsx?uf=BA")
    assert response.status_code == 200
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in response.headers["content-type"]
    )
    assert len(response.content) > 0
