import json
import logging
from datetime import datetime
from pathlib import Path

from app.core.observability import TZ_SP, get_metrics_log_path

logger = logging.getLogger(__name__)


def migrate_logs() -> None:
    """Migra logs antigos para o arquivo unificado metrics_logs.jsonl."""
    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / "data" / "logs"
    new_log_path = get_metrics_log_path()

    files_to_migrate = [
        ("http_access.jsonl", "http_request"),
        ("ui_interactions.jsonl", "ui_event"),
        ("consolidated_metrics.jsonl", "consolidated_metric"),
    ]

    count = 0
    invalid_count = 0

    new_log_path.parent.mkdir(parents=True, exist_ok=True)

    with new_log_path.open("a", encoding="utf-8") as out_f:
        for filename, default_event in files_to_migrate:
            file_path = log_dir / filename

            if not file_path.exists():
                logger.info("Arquivo não encontrado: %s", file_path)
                continue

            with file_path.open("r", encoding="utf-8") as in_f:
                for line_number, line in enumerate(in_f, start=1):
                    if not line.strip():
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError as exc:
                        invalid_count += 1
                        logger.warning(
                            "JSON inválido em %s, linha %d: %s",
                            file_path,
                            line_number,
                            exc,
                        )
                        continue

                    if not isinstance(data, dict):
                        invalid_count += 1
                        logger.warning(
                            "Registro JSON não é um objeto em %s, linha %d.",
                            file_path,
                            line_number,
                        )
                        continue

                    timestamp = data.get("timestamp")

                    if isinstance(timestamp, str) and timestamp.endswith("Z"):
                        try:
                            dt = datetime.fromisoformat(timestamp)
                        except ValueError as exc:
                            logger.warning(
                                "Timestamp inválido em %s, linha %d: %s",
                                file_path,
                                line_number,
                                exc,
                            )
                        else:
                            data["timestamp"] = dt.astimezone(TZ_SP).isoformat()

                    data.setdefault("event", default_event)

                    if "duration_ms" in data and "metrics" not in data:
                        data["metrics"] = {"duration_ms": data.pop("duration_ms")}

                    out_f.write(json.dumps(data, ensure_ascii=False) + "\n")
                    count += 1

    logger.info(
        "Migração concluída: %d registros migrados; %d registros inválidos.",
        count,
        invalid_count,
    )
    print(
        f"Migrados {count} registros para {new_log_path}. "
        f"Registros inválidos: {invalid_count}."
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_logs()
