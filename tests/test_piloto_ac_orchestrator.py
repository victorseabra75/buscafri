import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from scripts.piloto_ac_orchestrator import (
    EXPECTED_SIZE,
    get_remote_info,
    handle_emergency_recovery,
    main,
    perform_rollback,
    verify_preconditions,
)


@pytest.fixture
def mock_run_cmd():
    with patch("scripts.piloto_ac_orchestrator.run_cmd") as mock:
        yield mock


@pytest.fixture
def mock_validate_integrity():
    with patch("scripts.piloto_ac_orchestrator.load_validate_integrity") as mock_load:
        validator_mock = MagicMock()
        mock_load.return_value = validator_mock
        yield validator_mock


def test_scenario_1_object_present_expected_size(mock_run_cmd):
    """Cenário 1: Objeto presente com tamanho esperado."""
    mock_res = MagicMock()
    mock_res.stdout = json.dumps(
        [{"Path": "data_0.parquet", "Size": EXPECTED_SIZE, "IsDir": False}]
    )
    mock_run_cmd.return_value = mock_res

    size, status = get_remote_info()
    assert status == "OK"
    assert size == EXPECTED_SIZE


def test_scenario_2_object_confirmed_absent(mock_run_cmd):
    """Cenário 2: Objeto ausente confirmado."""
    mock_res = MagicMock()
    mock_res.stdout = json.dumps([])
    mock_run_cmd.return_value = mock_res

    size, status = get_remote_info()
    assert status == "AUSENTE"
    assert size is None


def test_scenario_3_auth_connectivity_error(mock_run_cmd, mock_validate_integrity):
    """Cenário 3: Erro de autenticação ou conectividade no rclone."""
    mock_run_cmd.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd=["rclone", "lsjson"], stderr="Unauthorized"
    )

    with pytest.raises(RuntimeError, match="Falha de acesso ao R2"):
        verify_preconditions(mock_validate_integrity)


def test_scenario_4_unexpected_remote_size(mock_run_cmd, mock_validate_integrity):
    """Cenário 4: Tamanho remoto inesperado."""
    mock_res = MagicMock()
    mock_res.stdout = json.dumps(
        [{"Path": "data_0.parquet", "Size": 99999, "IsDir": False}]
    )
    mock_run_cmd.return_value = mock_res

    with pytest.raises(RuntimeError, match="Tamanho remoto inesperado"):
        verify_preconditions(mock_validate_integrity)


def test_scenario_5_upload_failure(mock_run_cmd, mock_validate_integrity):
    """Cenário 5: Falha durante a substituição (copyto do reordenado falha)."""
    mock_ls = MagicMock()
    mock_ls.stdout = json.dumps(
        [{"Path": "data_0.parquet", "Size": EXPECTED_SIZE, "IsDir": False}]
    )

    def side_effect(cmd):
        if "lsjson" in cmd:
            return mock_ls
        if "copyto" in cmd and "reordenado" in cmd[2]:
            raise subprocess.CalledProcessError(1, cmd, stderr="Upload failed")
        if "copyto" in cmd and "particionado" in cmd[2]:
            return MagicMock()
        return MagicMock()

    mock_run_cmd.side_effect = side_effect
    mock_validate_integrity.return_value = True  # Rollback ok

    code = main()
    assert code == 1


def test_scenario_6_post_upload_validation_failure(
    mock_run_cmd, mock_validate_integrity
):
    """Cenário 6: Falha na validação pós-upload."""
    mock_ls = MagicMock()
    mock_ls.stdout = json.dumps(
        [{"Path": "data_0.parquet", "Size": EXPECTED_SIZE, "IsDir": False}]
    )
    mock_run_cmd.return_value = mock_ls

    # Primeira chamada (substituição) = False, segunda (rollback) = True
    mock_validate_integrity.side_effect = [False, True]

    code = main()
    assert code == 1


def test_scenario_7_successful_rollback(mock_run_cmd):
    """Cenário 7: Rollback bem-sucedido."""
    mock_run_cmd.return_value = MagicMock()
    val_mock = MagicMock(return_value=True)

    success = perform_rollback(val_mock)
    assert success is True


def test_scenario_8_failed_rollback(mock_run_cmd):
    """Cenário 8: Rollback malsucedido."""
    mock_run_cmd.return_value = MagicMock()
    val_mock = MagicMock(return_value=False)

    success = perform_rollback(val_mock)
    assert success is False


def test_emergency_recovery_confirmation_yes(mock_run_cmd):
    """Cenário 9: Recuperação de emergência com confirmação 's'."""
    mock_run_cmd.return_value = MagicMock()
    val_mock = MagicMock(return_value=True)

    with patch("builtins.input", return_value="s"):
        code = handle_emergency_recovery(val_mock)
        assert code == 0


def test_emergency_recovery_confirmation_no(mock_run_cmd):
    """Cenário 10: Recuperação de emergência recusada pelo usuário."""
    val_mock = MagicMock()

    with patch("builtins.input", return_value="n"):
        code = handle_emergency_recovery(val_mock)
        assert code == 1
