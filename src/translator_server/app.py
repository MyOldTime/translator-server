from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import fields

from fastapi import Depends, FastAPI, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from translator_server.capacity_limiter import (
    TranslationCapacityLimiter,
    TranslationQueueFullError,
    TranslationQueueTimeoutError,
)
from translator_server.config import Settings
from translator_server.exceptions import ConfigurationError, TranslationError, UnsupportedLanguageError
from translator_server.logging_config import configure_logging
from translator_server.schemas import HealthResponse, TranslateRequest, TranslateResponse
from translator_server.security import build_basic_auth_dependency
from translator_server.services.translation_service import TranslationService


logger = logging.getLogger(__name__)


def _log_startup_configuration(settings: Settings) -> None:
    for field in fields(settings):
        logger.info("服务配置：%s=%s", field.name, getattr(settings, field.name))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.load()
    configure_logging(settings.log_level)
    app.state.settings = settings
    _log_startup_configuration(settings)
    app.state.translation_service = TranslationService(settings)
    app.state.translate_capacity_limiter = TranslationCapacityLimiter(
        max_concurrency=settings.translate_max_concurrency,
        queue_size=settings.translate_queue_size,
        queue_timeout_seconds=settings.translate_queue_timeout_seconds,
    )
    logger.info(
        "服务启动完成：model_mode=%s translate_max_concurrency=%s translate_queue_size=%s translate_queue_timeout_seconds=%s",
        "m2m100" if settings.use_m2m100 else "openai",
        settings.translate_max_concurrency,
        settings.translate_queue_size,
        settings.translate_queue_timeout_seconds,
    )
    yield
    logger.info("服务关闭完成")


def create_app() -> FastAPI:
    settings = Settings.load()
    configure_logging(settings.log_level)
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Single translation API service powered by M2M100 or an OpenAI-compatible API.",
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
        capacity_limiter: TranslationCapacityLimiter = request.app.state.translate_capacity_limiter
        try:
            async with capacity_limiter.slot():
                result = await run_in_threadpool(
                    service.translate,
                    text=payload.text,
                    source_lang=payload.source_lang,
                    target_lang=payload.target_lang,
                )
        except (TranslationQueueFullError, TranslationQueueTimeoutError) as exc:
            logger.warning(
                "翻译请求被限流拒绝：原因=%s",
                exc.__class__.__name__,
            )
            raise HTTPException(
                status_code=429,
                detail="Too many translation requests. Please retry later.",
                headers={"Retry-After": "5"},
            ) from exc
        except UnsupportedLanguageError as exc:
            logger.warning("翻译请求失败：不支持的语言 错误=%s", exc)
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            logger.warning("翻译请求失败：参数校验错误 错误=%s", exc)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (ConfigurationError, TranslationError) as exc:
            logger.exception("翻译请求失败：内部翻译错误 错误=%s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            logger.exception("翻译请求失败：未预期异常 错误=%s", exc)
            raise HTTPException(status_code=500, detail="Internal server error") from exc

        logger.info(
            "翻译请求完成：detected_source_lang=%s source_lang=%s target_lang=%s model_name=%s device=%s took_ms=%s",
            result.detected_source_lang,
            result.source_lang,
            result.target_lang,
            result.model_name,
            result.device,
            result.took_ms,
        )
        return TranslateResponse(
            translated_text=result.translated_text,
            detected_source_lang=result.detected_source_lang,
            source_lang=result.source_lang,
            target_lang=result.target_lang,
            model_name=result.model_name,
            device=result.device,
            took_ms=result.took_ms,
        )

    return app
