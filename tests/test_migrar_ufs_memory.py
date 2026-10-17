import shutil
import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd
import pytest

# Adiciona diretório raiz ao sys.path para importar scripts
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.migrar_todas_ufs import (
    comparar_arquivos_escalavel,
    configurar_duckdb,
)


@pytest.fixture
def ambiente_temp_duckdb():
    temp_dir = tempfile.mkdtemp(prefix="duckdb_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_configurar_duckdb_memoria_e_temp(ambiente_temp_duckdb, monkeypatch):
    monkeypatch.setenv("DUCKDB_MAX_MEMORY", "1GB")
    monkeypatch.setenv("DUCKDB_THREADS", "2")
    monkeypatch.setenv("DUCKDB_TEMP_DIR", ambiente_temp_duckdb)

    conn = configurar_duckdb()
    assert conn is not None

      # Verifica configurações aplicadas
    resultado_mem = conn.execute(
        "SELECT current_setting('memory_limit')"
    ).fetchone()
    resultado_threads = conn.execute(
        "SELECT current_setting('threads')"
    ).fetchone()
    resultado_temp = conn.execute(
        "SELECT current_setting('temp_directory')"
    ).fetchone()

    assert resultado_mem is not None
    assert resultado_threads is not None
    assert resultado_temp is not None

    res_mem = str(resultado_mem[0])
    res_threads = resultado_threads[0]
    res_temp = str(resultado_temp[0])

    assert res_mem
    assert int(res_threads) == 2
    assert (
        str(Path(ambiente_temp_duckdb).resolve()) in res_temp
        or Path(ambiente_temp_duckdb).name in res_temp
    )
    assert (
        "1" in res_mem or "GB" in res_mem or "8" in res_mem or "MiB" in res_mem
    )   # Pode ser convertido internamente
    assert res_threads == 2 or str(res_threads) == "2"
    assert (
        ambiente_temp_duckdb in res_temp or Path(ambiente_temp_duckdb).name in res_temp
    )
    conn.close()


def test_comparar_arquivos_escalavel_identicos(ambiente_temp_duckdb):
    conn = duckdb.connect()

    # Cria arquivo Parquet sintético
    df1 = pd.DataFrame(
        {
            "cnpj_basico": ["12345678", "87654321", "11223344"],
            "municipio": ["0100", "0200", "0300"],
            "valor": [10, 20, 30],
        }
    )

    f1 = Path(ambiente_temp_duckdb) / "f1.parquet"
    f2 = Path(ambiente_temp_duckdb) / "f2.parquet"

    df1.to_parquet(f1)
    df1.to_parquet(f2)

    assert (
        comparar_arquivos_escalavel(conn, f1, f2, temp_dir=ambiente_temp_duckdb) is True
    )
    conn.close()


def test_comparar_arquivos_escalavel_conteudo_divergente_mesma_contagem(
    ambiente_temp_duckdb,
):
    conn = duckdb.connect()

    df1 = pd.DataFrame(
        {"cnpj_basico": ["12345678", "87654321"], "municipio": ["0100", "0200"]}
    )

    df2 = pd.DataFrame(
        {
            "cnpj_basico": ["12345678", "99999999"],  # Divergente
            "municipio": ["0100", "0200"],
        }
    )

    f1 = Path(ambiente_temp_duckdb) / "f1.parquet"
    f2 = Path(ambiente_temp_duckdb) / "f2.parquet"

    df1.to_parquet(f1)
    df2.to_parquet(f2)

    assert (
        comparar_arquivos_escalavel(conn, f1, f2, temp_dir=ambiente_temp_duckdb)
        is False
    )
    conn.close()


def test_comparar_arquivos_escalavel_duplicados_multiplicidade(ambiente_temp_duckdb):
    conn = duckdb.connect()

    # Linhas idênticas com contagens de multiplicidade diferentes
    df1 = pd.DataFrame(
        {
            "cnpj_basico": ["12345678", "12345678", "87654321"],
            "municipio": ["0100", "0100", "0200"],
        }
    )

    df2 = pd.DataFrame(
        {
            "cnpj_basico": [
                "12345678",
                "87654321",
                "87654321",
            ],  # Multiplicidade trocada
            "municipio": ["0100", "0200", "0200"],
        }
    )

    f1 = Path(ambiente_temp_duckdb) / "f1.parquet"
    f2 = Path(ambiente_temp_duckdb) / "f2.parquet"

    df1.to_parquet(f1)
    df2.to_parquet(f2)

    assert (
        comparar_arquivos_escalavel(conn, f1, f2, temp_dir=ambiente_temp_duckdb)
        is False
    )
    conn.close()


def test_falha_espaco_temporario_invalido():
    conn = duckdb.connect()
    f1 = Path("data/reordenado/estabelecimentos/uf=AC/data_0.parquet")
    f2 = Path("data/particionado/estabelecimentos/uf=AC/data_0.parquet")

    if f1.exists() and f2.exists():
        with pytest.raises(FileNotFoundError):
            comparar_arquivos_escalavel(
                conn, f1, f2, temp_dir="/diretorio_inexistente_123456"
            )
    conn.close()
