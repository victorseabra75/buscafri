import pandas as pd
import pytest

from scripts.validar_reordenacao_r2 import validate_integrity


@pytest.fixture
def temp_parquets(tmp_path):
    base_df = pd.DataFrame(
        {
            "municipio": ["0001", "0002", "0002"],
            "cnae_fiscal_principal": ["1000000", "2000000", "2000000"],
            "cnpj_basico": ["00000001", "00000002", "00000003"],
            "cnpj_ordem": ["0001", "0001", "0001"],
            "cnpj_dv": ["01", "02", "03"],
            "razao_social": ["Empresa A", "Empresa B", "Empresa C"],
        }
    )

    file_a = tmp_path / "file_a.parquet"
    base_df.to_parquet(file_a)
    return tmp_path, file_a, base_df


def test_validate_integrity_identical_files(temp_parquets):
    _, file_a, _ = temp_parquets
    assert validate_integrity(str(file_a), str(file_a)) is True


def test_validate_integrity_different_schema(temp_parquets):
    tmp_path, file_a, base_df = temp_parquets
    file_b = tmp_path / "different_schema.parquet"

    df_b = base_df.copy()
    df_b["extra_col"] = "test"
    df_b.to_parquet(file_b)

    assert validate_integrity(str(file_a), str(file_b)) is False


def test_validate_integrity_different_count(temp_parquets):
    tmp_path, file_a, base_df = temp_parquets
    file_b = tmp_path / "different_count.parquet"

    df_b = base_df.iloc[:2].copy()
    df_b.to_parquet(file_b)

    assert validate_integrity(str(file_a), str(file_b)) is False


def test_validate_integrity_different_content(temp_parquets):
    tmp_path, file_a, base_df = temp_parquets
    file_b = tmp_path / "different_content.parquet"

    df_b = base_df.copy()
    df_b.loc[0, "razao_social"] = "Empresa Modificada"
    df_b.to_parquet(file_b)

    assert validate_integrity(str(file_a), str(file_b)) is False


def test_validate_integrity_unordered_physical_file(tmp_path):
    # Criar um DataFrame desordenado
    unordered_df = pd.DataFrame(
        {
            "municipio": ["0002", "0001"],
            "cnae_fiscal_principal": ["2000000", "1000000"],
            "cnpj_basico": ["00000002", "00000001"],
            "cnpj_ordem": ["0001", "0001"],
            "cnpj_dv": ["02", "01"],
        }
    )
    ordered_df = unordered_df.sort_values(
        by=[
            "municipio",
            "cnae_fiscal_principal",
            "cnpj_basico",
            "cnpj_ordem",
            "cnpj_dv",
        ]
    ).reset_index(drop=True)

    file_unordered = tmp_path / "unordered.parquet"
    file_ordered = tmp_path / "ordered.parquet"

    unordered_df.to_parquet(file_unordered)
    ordered_df.to_parquet(file_ordered)

    # file_unordered como remote_url deve falhar na checagem de ordenação física
    assert validate_integrity(str(file_ordered), str(file_unordered)) is False
    # file_ordered como remote_url deve passar
    assert validate_integrity(str(file_ordered), str(file_ordered)) is True


def test_validate_integrity_nulls_last_ordering(tmp_path):
    # Testa se NULLS LAST na ordenação é respeitado
    nulls_df = pd.DataFrame(
        {
            "municipio": ["0001", "0001", None],
            "cnae_fiscal_principal": ["1000000", None, "2000000"],
            "cnpj_basico": ["00000001", "00000002", "00000003"],
            "cnpj_ordem": ["0001", "0001", "0001"],
            "cnpj_dv": ["01", "02", "03"],
        }
    )
    file_nulls = tmp_path / "nulls.parquet"
    nulls_df.to_parquet(file_nulls)

    assert validate_integrity(str(file_nulls), str(file_nulls)) is True


def test_validate_integrity_non_existent_file(tmp_path):
    file_a = tmp_path / "file_a.parquet"
    file_non_existent = tmp_path / "ghost.parquet"
    pd.DataFrame({"municipio": ["0001"]}).to_parquet(file_a)

    assert validate_integrity(str(file_a), str(file_non_existent)) is False
