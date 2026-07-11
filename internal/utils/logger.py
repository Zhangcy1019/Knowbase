"""Unified logging utilities for CIAgent."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

TRACE_LEVEL_NUM = 5
_NOISY_THIRD_PARTY_LOGGERS = (
    "websockets",
    "httpx",
    "httpcore",
    "urllib3",
    "elastic_transport",
    "elasticsearch",
)
_PROJECT_LOGGER_PREFIXES = (
    "adapters",
    "agent",
    "app",
    "bus",
    "connectors",
    "core",
    "knowledge",
    "graphs",
    "llm",
    "orchestrator",
    "schemas",
    "session",
    "utils",
    "workflows",
    "openai",
    "knowbase",
    "api",
    "case",
    "events",
    "ingest",
    "partition",
    "query",
    "runtime",
    "skills",
    "tools",
)

_DEFAULT_SENSITIVE_KEYS = {
    "api_key",
    "app_secret",
    "secret",
    "token",
    "authorization",
    "password",
}


@dataclass(frozen=True)
class LoggingConfig:
    """Runtime logging configuration."""

    level: str = "INFO"
    json_format: bool = False

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        return cls(
            level=os.getenv("CIAGENT_LOG_LEVEL", "INFO"),
            json_format=os.getenv("CIAGENT_LOG_JSON", "false").lower() in {"1", "true", "yes", "on"},
        )


class JsonLogFormatter(logging.Formatter):
    """JSON formatter with basic sensitive-field masking."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        standard = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
            "relativeCreated", "thread", "threadName", "processName", "process", "message",
        }
        extras = {
            k: ("***" if k.lower() in _DEFAULT_SENSITIVE_KEYS else self._mask(v))
            for k, v in record.__dict__.items()
            if k not in standard and not k.startswith("_")
        }
        if extras:
            payload["context"] = extras

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)

    def _mask(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {k: ("***" if k.lower() in _DEFAULT_SENSITIVE_KEYS else self._mask(v)) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._mask(v) for v in value]
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat()
        return repr(value)


class ContextLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter for contextual fields."""

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        extra = kwargs.get("extra", {})
        kwargs["extra"] = {**self.extra, **extra}
        return msg, kwargs


def _install_trace_level() -> None:
    if hasattr(logging, "TRACE"):
        return

    logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
    setattr(logging, "TRACE", TRACE_LEVEL_NUM)

    def _trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
        if self.isEnabledFor(TRACE_LEVEL_NUM):
            self._log(TRACE_LEVEL_NUM, message, args, **kwargs)

    setattr(logging.Logger, "trace", _trace)


def _resolve_level(level_name: str) -> int:
    normalized = level_name.upper().strip()
    if normalized == "TRACE":
        return TRACE_LEVEL_NUM
    return getattr(logging, normalized, logging.INFO)


def _set_handler_formatter(handler: logging.Handler, *, json_format: bool) -> None:
    if json_format:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )


def _apply_library_verbosity(level_name: str) -> None:
    normalized = level_name.upper().strip()

    if normalized == "DEBUG":
        for logger_name in _PROJECT_LOGGER_PREFIXES:
            logging.getLogger(logger_name).setLevel(logging.DEBUG)
        for logger_name in _NOISY_THIRD_PARTY_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
        return

    for logger_name in _PROJECT_LOGGER_PREFIXES:
        logging.getLogger(logger_name).setLevel(logging.NOTSET)

    if normalized == "TRACE":
        for logger_name in _NOISY_THIRD_PARTY_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.NOTSET)
    else:
        for logger_name in _NOISY_THIRD_PARTY_LOGGERS:
            logging.getLogger(logger_name).setLevel(logging.WARNING)


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Configure root logger once per process."""
    _install_trace_level()
    cfg = config or LoggingConfig.from_env()
    root_logger = logging.getLogger()
    normalized_level = cfg.level.upper().strip()

    root_level = _resolve_level(normalized_level)
    handler_level = _resolve_level(normalized_level)

    root_logger.setLevel(root_level)

    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setLevel(handler_level)
            _set_handler_formatter(handler, json_format=cfg.json_format)
        _apply_library_verbosity(normalized_level)
        return

    handler = logging.StreamHandler()
    handler.setLevel(handler_level)
    _set_handler_formatter(handler, json_format=cfg.json_format)
    root_logger.addHandler(handler)
    _apply_library_verbosity(normalized_level)


def get_logger(name: str, **context: Any) -> ContextLoggerAdapter:
    """Get logger with optional structured context."""
    base = logging.getLogger(name)
    return ContextLoggerAdapter(base, context)
