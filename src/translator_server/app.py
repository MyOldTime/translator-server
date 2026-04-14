from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request

from translator_server.config import Settings
from translator_server.exceptions import ConfigurationError, TranslationError, UnsupportedLanguageError
from translator_server.schemas import HealthResponse, TranslateRequest, TranslateResponse
from translator_server.security import build_basic_auth_dependency
from translator_server.services.translation_service import TranslationService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.load()
    app.state.settings = settings
    app.state.translation_service = TranslationService(settings)
    yield


def create_app() -> FastAPI:
    settings = Settings.load()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Single translation API service powered by fastText and M2M100.",
        lifespan=lifespan,
    )
    auth_dependency = build_basic_auth_dependency(settings)

    @app.get("/healthz", response_model=HealthResponse, tags=["system"])
    async def health(
        request: Request,
        _: str = Depends(auth_dependency),
    ) -> HealthResponse:
        service: TranslationService = request.app.state.translation_service
        return HealthResponse(
            status="ok",
            app_name=request.app.state.settings.app_name,
            model_name=service.translator.model_name,
        )

    @app.post("/api/v1/translate", response_model=TranslateResponse, tags=["translation"])
    async def translate(
        payload: TranslateRequest,
        request: Request,
        _: str = Depends(auth_dependency),
    ) -> TranslateResponse:
        service: TranslationService = request.app.state.translation_service
        try:
            result = service.translate(
                text=payload.text,
                source_lang=payload.source_lang,
                target_lang=payload.target_lang,
            )
        except UnsupportedLanguageError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (ConfigurationError, TranslationError) as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return TranslateResponse(
            translated_text=result.translated_text,
            detected_source_lang=result.detected_source_lang,
            source_lang=result.source_lang,
            target_lang=result.target_lang,
            model_name=result.model_name,
            took_ms=result.took_ms,
        )

    return app
