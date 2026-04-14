from __future__ import annotations

import secrets
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from translator_server.config import Settings

basic_security = HTTPBasic()


def verify_basic_auth(
    credentials: HTTPBasicCredentials = Depends(basic_security),
    settings: Settings | None = None,
) -> str:
    current_settings = settings or Settings.load()
    valid_username = secrets.compare_digest(credentials.username, current_settings.basic_auth_username)
    valid_password = secrets.compare_digest(credentials.password, current_settings.basic_auth_password)

    if not (valid_username and valid_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid basic auth credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


def build_basic_auth_dependency(settings: Settings) -> Callable[[HTTPBasicCredentials], str]:
    def dependency(credentials: HTTPBasicCredentials = Depends(basic_security)) -> str:
        return verify_basic_auth(credentials=credentials, settings=settings)

    return dependency
