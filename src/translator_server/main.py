from __future__ import annotations

import uvicorn

from translator_server.app import create_app
from translator_server.config import Settings


def run() -> None:
    settings = Settings.load()
    uvicorn.run(
        "translator_server.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    run()
