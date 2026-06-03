from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import cast

from translator_server.config import Settings
from translator_server.exceptions import UnsupportedLanguageError
from translator_server.services.language_detector import LanguageDetector
from translator_server.services.m2m_translator import M2MTranslator
from translator_server.services.openai_translator import OpenAITranslator


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TranslationResult:
    translated_text: str
    detected_source_lang: str
    source_lang: str
    target_lang: str
    model_name: str
    device: str
    took_ms: int


class TranslationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.detector: LanguageDetector | None = None
        logger.info("初始化翻译服务：use_m2m100=%s", settings.use_m2m100)
        if settings.use_m2m100:
            logger.info("开始加载本地语种识别模型：path=%s", settings.lid_model_path)
            self.detector = LanguageDetector(settings.lid_model_path)
            logger.info("本地语种识别模型加载完成")
            logger.info(
                "开始加载本地翻译模型：path=%s device=%s max_batch_size=%s segment_max_chars=%s",
                settings.translation_model_path,
                settings.device,
                settings.max_batch_size,
                settings.segment_max_chars,
            )
            self.translator = M2MTranslator(
                model_path=settings.translation_model_path,
                device=settings.device,
                max_length=settings.max_length,
                max_new_tokens=settings.max_new_tokens,
                max_batch_size=settings.max_batch_size,
                segment_max_chars=settings.segment_max_chars,
                num_beams=settings.num_beams,
            )
            logger.info(
                "本地翻译模型加载完成：model_name=%s device=%s",
                self.translator.model_name,
                self.translator.device,
            )
        else:
            logger.info(
                "初始化 OpenAI 兼容翻译器：base_url=%s model=%s",
                settings.openai_base_url,
                settings.openai_model,
            )
            self.translator = OpenAITranslator(
                api_key=settings.openai_api_key or "",
                base_url=settings.openai_base_url,
                model=settings.openai_model or "",
            )
            logger.info("OpenAI 兼容翻译器初始化完成：model=%s", self.translator.model_name)

    def translate(self, text: str, source_lang: str | None, target_lang: str | None) -> TranslationResult:
        if len(text) > self.settings.max_input_chars:
            logger.warning(
                "翻译输入过长：text_length=%s max_input_chars=%s",
                len(text),
                self.settings.max_input_chars,
            )
            raise ValueError(
                f"Input text too long: {len(text)} characters, limit is {self.settings.max_input_chars}"
            )

        start = time.perf_counter()
        if not self.settings.use_m2m100:
            return self._translate_with_openai(text, source_lang, target_lang, start)

        if self.detector is None:
            raise RuntimeError("Language detector is not initialized")
        detected_source = source_lang or self.detector.detect(text)
        effective_source = source_lang or detected_source
        effective_target = target_lang or self.settings.target_lang

        normalized_source = self.translator.normalize_lang(effective_source)
        normalized_target = self.translator.normalize_lang(effective_target)

        if normalized_source == normalized_target:
            translated_text = text
            if normalized_target == "zh":
                translated_text = self.translator.translate(text, normalized_source, normalized_target)
        else:
            translated_text = self.translator.translate(text, normalized_source, normalized_target)

        took_ms = int((time.perf_counter() - start) * 1000)
        return TranslationResult(
            translated_text=translated_text,
            detected_source_lang=self._normalize_detected_lang(detected_source),
            source_lang=normalized_source,
            target_lang=normalized_target,
            model_name=self.translator.model_name,
            device=self.translator.device,
            took_ms=took_ms,
        )

    def _normalize_detected_lang(self, lang: str) -> str:
        try:
            return self.translator.normalize_lang(lang)
        except UnsupportedLanguageError:
            return lang

    def _translate_with_openai(
            self,
            text: str,
            source_lang: str | None,
            target_lang: str | None,
            start: float,
    ) -> TranslationResult:
        translator = cast(OpenAITranslator, self.translator)
        effective_source = translator.normalize_lang(source_lang) if source_lang else None
        effective_target = translator.normalize_lang(target_lang or self.settings.target_lang)
        translation = translator.translate(text, effective_source, effective_target)
        detected_source = effective_source or translation.detected_source_lang
        took_ms = int((time.perf_counter() - start) * 1000)

        return TranslationResult(
            translated_text=translation.translated_text,
            detected_source_lang=detected_source,
            source_lang=detected_source,
            target_lang=effective_target,
            model_name=translator.model_name,
            device=translator.device,
            took_ms=took_ms,
        )
