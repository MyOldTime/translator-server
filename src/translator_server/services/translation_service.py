from __future__ import annotations

import time
from dataclasses import dataclass

from translator_server.config import Settings
from translator_server.exceptions import UnsupportedLanguageError
from translator_server.services.language_detector import LanguageDetector
from translator_server.services.m2m_translator import M2MTranslator


@dataclass(slots=True)
class TranslationResult:
    translated_text: str
    detected_source_lang: str
    source_lang: str
    target_lang: str
    model_name: str
    took_ms: int


class TranslationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.detector = LanguageDetector(settings.lid_model_path)
        self.translator = M2MTranslator(
            model_path=settings.translation_model_path,
            device=settings.device,
            max_length=settings.max_length,
            max_new_tokens=settings.max_new_tokens,
            max_batch_size=settings.max_batch_size,
            segment_max_chars=settings.segment_max_chars,
            num_beams=settings.num_beams,
        )

    def translate(self, text: str, source_lang: str | None, target_lang: str | None) -> TranslationResult:
        if len(text) > self.settings.max_input_chars:
            raise ValueError(
                f"Input text too long: {len(text)} characters, limit is {self.settings.max_input_chars}"
            )

        start = time.perf_counter()
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
            took_ms=took_ms,
        )

    def _normalize_detected_lang(self, lang: str) -> str:
        try:
            return self.translator.normalize_lang(lang)
        except UnsupportedLanguageError:
            return lang
