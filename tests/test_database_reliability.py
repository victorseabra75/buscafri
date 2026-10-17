from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.core.database import DuckDBClient


def test_query_attempts_reconnection_on_failure() -> None:
    """Verifica se query() reconecta quando a conexão está nula."""
    client = DuckDBClient()
    client.conn = None

    expected_result = pd.DataFrame({"value": [1]})

    def side_effect_connect() -> None:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.df.return_value = expected_result
        client.conn = mock_conn

    client.connect = MagicMock(side_effect=side_effect_connect)

    result = client.query("SELECT 1")

    client.connect.assert_called_once_with()
    pd.testing.assert_frame_equal(result, expected_result)


def test_query_propagates_sql_execution_error() -> None:
    """Verifica se erros durante a execução SQL são propagados."""
    client = DuckDBClient()
    mock_conn = MagicMock()
    mock_conn.execute.side_effect = RuntimeError("SQL Execution Error")
    client.conn = mock_conn

    with pytest.raises(RuntimeError, match="SQL Execution Error"):
        client.query("SELECT * FROM tabela_inexistente")


def test_connect_failures_do_not_retry_indefinitely() -> None:
    """Verifica se query() falha quando a conexão não é estabelecida."""
    client = DuckDBClient()
    client.conn = None
    client.connect = MagicMock(return_value=None)

    with pytest.raises(
        RuntimeError,
        match="Não foi possível conectar ao DuckDB.",
    ):
        client.query("SELECT 1")

    client.connect.assert_called_once_with()
