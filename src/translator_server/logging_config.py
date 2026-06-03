from __future__ import annotations

import logging.config


def configure_logging(level: str) -> None:
    normalized_level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] - %(levelname)-8s - [pid:%(process)d tid:%(thread)d] - [%(name)-25s] %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": normalized_level,
                "handlers": ["console"],
            },
            "loggers": {
                "translator_server": {
                    "level": normalized_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "fastapi": {
                    "level": normalized_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn": {
                    "level": normalized_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": normalized_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "level": normalized_level,
                    "handlers": ["console"],
                    "propagate": False,
                },
            },
        }
    )
