"""Runtime entrypoint for the integrated Knowbase app."""

from __future__ import annotations

import argparse

import bootstrap as bootstrap_module

from internal.utils.config import load_runtime_config
from internal.utils.logger import LoggingConfig, configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Run integrated Knowbase web app")
    parser.add_argument("--config", default="config/app.yaml")
    args = parser.parse_args()
    runtime_cfg = load_runtime_config(args.config)
    configure_logging(
        LoggingConfig(
            level=runtime_cfg.logging.level,
            json_format=runtime_cfg.logging.json_format,
        )
    )
    bootstrap_module.set_runtime_config(runtime_cfg)

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is required to run Knowbase API.") from exc

    uvicorn.run(
        "bootstrap:create_app",
        factory=True,
        host=runtime_cfg.startup.api_server.host,
        port=runtime_cfg.startup.api_server.port,
    )


__all__ = ["main"]


if __name__ == "__main__":
    main()
