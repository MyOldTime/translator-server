from __future__ import annotations

import uvicorn

from translator_server.config import Settings
from translator_server.logging_config import configure_logging


def run() -> None:
    settings = Settings.load()
    configure_logging(settings.log_level)
    uvicorn.run(
        "translator_server.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_config=None,
    )


if __name__ == "__main__":
    run()
