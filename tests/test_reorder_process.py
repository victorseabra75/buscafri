import os

import pandas as pd
import pytest

from scripts.reorder_parquet import reorder_parquet, validate_integrity


@pytest.fixture
def temp_data(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    os.makedirs(input_dir / "uf=AC")

    # Criar parquet de teste
    df = pd.DataFrame(
        {
            "cnpj_basico": ["06507307", "04800933"],
            "cnpj_ordem": ["0001", "0001"],
            "cnpj_dv": ["60", "14"],
            "municipio": ["0145", "0139"],
            "cnae_fiscal_principal": ["9492800", "4712100"],
        }
    )
    df.to_parquet(input_dir / "uf=AC" / "test.parquet")

    return input_dir, output_dir


def test_reorder_and_validate(temp_data):
    input_dir, output_dir = temp_data
    assert reorder_parquet(str(input_dir), str(output_dir))
    success, msg = validate_integrity(str(input_dir), str(output_dir))
    assert success, msg

    # Valida ordenação
    df = pd.read_parquet(output_dir / "uf=AC" / "data_0.parquet")
    assert df.iloc[0]["municipio"] < df.iloc[1]["municipio"] or (
        df.iloc[0]["municipio"] == df.iloc[1]["municipio"]
        and df.iloc[0]["cnae_fiscal_principal"] <= df.iloc[1]["cnae_fiscal_principal"]
    )


def test_refuse_overwrite(temp_data):
    input_dir, output_dir = temp_data
    os.makedirs(output_dir)
    with pytest.raises(ValueError):
        reorder_parquet(str(input_dir), str(output_dir))
