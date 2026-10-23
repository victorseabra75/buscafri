import json
import logging
import logging.handlers
import re
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from app.core.config import settings

# Logger específico e isolado para eventos de acesso HTTP em JSONL
ACCESS_LOGGER_NAME = "buscafri.http_access"
# Logger específico e isolado para eventos de interação da UI em JSONL
METRICS_LOGGER_NAME = "buscafri.metrics"

# Regex para validação de formato seguro de UF (exatamente 2 letras)
UF_PATTERN = re.compile(r"^[A-Za-z]{2}$")
# Regex para validação de CNAE e Município (apenas dígitos alfanuméricos simples)
ALPHANUM_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,20}$")

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_log_file_path() -> Path:
    """Resolve o caminho absoluto do arquivo de log baseado na raiz do projeto."""
    log_dir_path = Path(settings.LOG_DIR)
    if not log_dir_path.is_absolute():
        log_dir_path = ROOT_DIR / log_dir_path
    return log_dir_path / settings.LOG_FILE_NAME


class JsonLineFormatter(logging.Formatter):
    """Formata registros de log diretamente para uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        if isinstance(record.msg, dict):
            return json.dumps(record.msg, ensure_ascii=False)
        return json.dumps({"message": super().format(record)}, ensure_ascii=False)


def setup_access_logger(
    log_file_path: Path | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
) -> logging.Logger:
    """Configura o logger de observabilidade HTTP com rotação e sem propagação."""
    logger = logging.getLogger(ACCESS_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Evita adicionar múltiplos handlers na reinicialização
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # noqa: BLE001, S110
            pass

    target_path = log_file_path or get_log_file_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    bytes_limit = max_bytes if max_bytes is not None else settings.LOG_MAX_BYTES
    backups = backup_count if backup_count is not None else settings.LOG_BACKUP_COUNT

    file_handler = logging.handlers.RotatingFileHandler(
        target_path,
        maxBytes=bytes_limit,
        backupCount=backups,
        encoding="utf-8",
    )
    file_handler.setFormatter(JsonLineFormatter())
    logger.addHandler(file_handler)

    return logger


def extract_search_metadata(
    request: Request, normalized_route: str
) -> dict[str, Any] | None:
    """
    Extrai e normaliza exclusivamente os critérios de busca analíticos permitidos.
    Separa parâmetros analíticos de controle de paginação (page, limit, cursor).
    Nunca registra query strings brutas, CNPJ, dados de contato ou campos não autorizados.
    """
    if normalized_route not in {"/api/v1/busca", "/api/v1/exportar/{formato}"}:
        return None

    query_params = request.query_params

    # 1. Filtros analíticos permitidos
    uf_raw = query_params.get("uf")
    uf_clean: str | None = None
    if uf_raw:
        uf_stripped = uf_raw.strip().upper()
        if UF_PATTERN.match(uf_stripped):
            uf_clean = uf_stripped

    municipio_raw = query_params.get("municipio")
    municipio_clean: str | None = None
    if municipio_raw:
        mun_stripped = municipio_raw.strip()
        if ALPHANUM_CODE_PATTERN.match(mun_stripped):
            municipio_clean = mun_stripped

    cnae_raw = query_params.get("cnae")
    cnae_clean: str | None = None
    if cnae_raw:
        cnae_stripped = cnae_raw.strip()
        if ALPHANUM_CODE_PATTERN.match(cnae_stripped):
            cnae_clean = cnae_stripped

    # Trata booleanos preservando valores padrão quando não enviados
    def parse_bool(param_name: str, default: bool) -> bool:
        if param_name not in query_params:
            return default
        val = query_params.get(param_name, "").strip().lower()
        return val in {"true", "1", "t", "yes"}

    ativa_val = parse_bool("ativa", default=True)
    com_telefone_val = parse_bool("com_telefone", default=False)
    com_email_val = parse_bool("com_email", default=False)

    # Identificadores operacionais de navegação (sem classificar cursor como filtro)
    has_cursor = bool(query_params.get("cursor"))

    # Monta exclusivamente o dicionário sanitizado
    filters: dict[str, Any] = {
        "uf": uf_clean,
        "municipio": municipio_clean,
        "cnae": cnae_clean,
        "ativa": ativa_val,
        "com_telefone": com_telefone_val,
        "com_email": com_email_val,
        "has_cursor": has_cursor,
    }

    return filters


def log_consolidated_metric(
    event: str,
    **metadata: Any,
) -> None:
    """Registra uma métrica consolidada no logger de métricas."""
    logger = logging.getLogger(METRICS_LOGGER_NAME)
    logger.info(
        {
            "event": event,
            **metadata,
        }
    )


def log_ui_event(
    event: str | dict[str, Any],
    **metadata: Any,
) -> None:
    """Registra eventos de interação da interface."""
    if isinstance(event, dict):
        payload = event.copy()
        payload.setdefault("source", "ui")
    else:
        payload = {
            "event": event,
            "source": "ui",
            **metadata,
        }

    logger = logging.getLogger(METRICS_LOGGER_NAME)
    logger.info(payload)


def resolve_normalized_route(request: Request) -> str:
    """Resolve a rota normalizada a partir do roteador do FastAPI para evitar alta cardinalidade."""
    app = request.app
    for route in app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL and hasattr(route, "path"):
            return route.path

    # Se não houver correspondência exata de rota FastAPI, retorna o path original do request
    return request.url.path


class HttpObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware ASGI que emite exatamente 1 log estruturado em JSON Lines por requisição HTTP.
    Preserva a resposta da API e não expõe segredos nem dados sensíveis.
    """

    def __init__(self, app: Any, logger: logging.Logger | None = None) -> None:
        super().__init__(app)
        self.logger = logger or logging.getLogger(ACCESS_LOGGER_NAME)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Se observabilidade estiver desabilitada nas configurações, repassa diretamente
        if not settings.LOG_JSON_ENABLED:
            return await call_next(request)

        # Gera ID único sem confiar cegamente em cabeçalhos do cliente
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()

        # Determina rota normalizada inicial
        normalized_route = resolve_normalized_route(request)

        # Captura os filtros permitidos caso a rota seja de busca
        search_metadata = extract_search_metadata(request, normalized_route)

        status_code = 500
        error_class: str | None = None
        result = "error"

        try:
            http_response: Response = await call_next(request)

            status_code = http_response.status_code
            result = "success" if status_code < 400 else "error"

            http_response.headers["X-Request-ID"] = request_id
            return http_response

        except Exception as exc:
            # Registra somente a classe da exceção, sem sua mensagem.
            error_class = type(exc).__name__
            status_code = 500
            result = "error"
            raise

        finally:
            duration_ms = round(
                (time.perf_counter() - start_time) * 1000,
                2,
            )
            timestamp_utc = datetime.now(UTC).isoformat().replace("+00:00", "Z")

            log_entry = {
                "timestamp": timestamp_utc,
                "request_id": request_id,
                "method": request.method,
                "route": normalized_route,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "result": result,
                "error_class": error_class,
                "search": search_metadata,
            }

            try:
                self.logger.info(log_entry)
            except (OSError, ValueError, TypeError, RuntimeError) as log_error:
                # Uma falha no logger não deve mascarar a resposta
                # nem a exceção original da requisição.
                sys.stderr.write(
                    "[WARN] Falha ao registrar log de acesso HTTP: "
                    f"{type(log_error).__name__}\n"
                )
