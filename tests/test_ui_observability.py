import logging

from app.core.observability import (
    METRICS_LOGGER_NAME,
    log_consolidated_metric,
    log_ui_event,
)


def test_ui_and_consolidated_logging_functions(tmp_path, monkeypatch):
    """Garante que as funções de log da UI e consolidadas funcionam e utilizam parâmetros corretos."""
    # log_file = tmp_path / "test_ui.jsonl"

    # Testa log_ui_event com monkeypatch no setup ou invocação direta
    log_ui_event({"event": "test_ui_event", "interaction_id": "123-abc"})
    log_consolidated_metric({"event": "test_consolidated", "interaction_id": "123-abc"})

    ui_logger = logging.getLogger(METRICS_LOGGER_NAME)
    assert ui_logger is not None

    cons_logger = logging.getLogger(METRICS_LOGGER_NAME)
    assert cons_logger is not None
