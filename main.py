"""Runtime entrypoint for the integrated Knowbase app."""

from __future__ import annotations

import argparse
import os

from bootstrap import create_app

from internal.application import configure_runtime_environment
from internal.utils.config import load_runtime_config
from internal.utils.logger import LoggingConfig, configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run integrated Knowbase web app")
    parser.add_argument("--config", default=os.getenv("KNOWBASE_CONFIG_PATH", "config/app.yaml"))
    args = parser.parse_args()
    runtime_cfg = None
    if args.config:
        try:
            runtime_cfg = load_runtime_config(args.config)
            configure_runtime_environment(runtime_cfg)
            configure_logging(
                LoggingConfig(
                    level=runtime_cfg.logging.level,
                    json_format=runtime_cfg.logging.json_format,
                )
            )
        except Exception:
            runtime_cfg = None
            configure_logging()
    else:
        configure_logging()

    resolved_host = runtime_cfg.startup.api_server.host if runtime_cfg is not None else "0.0.0.0"
    resolved_port = runtime_cfg.startup.api_server.port if runtime_cfg is not None else 8000

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run Knowbase API.") from exc

    uvicorn.run("bootstrap:create_app", factory=True, host=resolved_host, port=resolved_port)


__all__ = ["create_app", "main"]


if __name__ == "__main__":
    main()
