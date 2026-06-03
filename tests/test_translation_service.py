from __future__ import annotations

import unittest
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from translator_server.config import Settings
from translator_server.services.openai_translator import OpenAITranslation
from translator_server.services.translation_service import TranslationService


def _settings(use_m2m100: bool) -> Settings:
    return Settings(
        app_name="translator-server",
        app_env="test",
        log_level="INFO",
        host="127.0.0.1",
        port=8191,
        lid_model_path=Path("lid.bin"),
        translation_model_path=Path("m2m100"),
        target_lang="zh",
        max_batch_size=8,
        max_input_chars=20000,
        segment_max_chars=400,
        max_length=512,
        max_new_tokens=512,
        device="cpu",
        num_beams=1,
        use_m2m100=use_m2m100,
        openai_api_key="secret" if not use_m2m100 else None,
        openai_base_url="https://example.com/v1" if not use_m2m100 else None,
        openai_model="test-model" if not use_m2m100 else None,
        basic_auth_username="admin",
        basic_auth_password="password",
        translate_max_concurrency=1,
        translate_queue_size=10,
        translate_queue_timeout_seconds=30,
    )


class TranslationServiceTests(unittest.TestCase):
    @patch("translator_server.services.translation_service.OpenAITranslator")
    @patch("translator_server.services.translation_service.M2MTranslator")
    @patch("translator_server.services.translation_service.LanguageDetector")
    def test_m2m100_mode_does_not_initialize_openai(
        self,
        detector_class: Mock,
        m2m100_class: Mock,
        openai_class: Mock,
    ) -> None:
        detector_class.return_value.detect.return_value = "en"
        m2m100 = m2m100_class.return_value
        m2m100.normalize_lang.side_effect = lambda lang: lang
        m2m100.translate.return_value = "你好"
        m2m100.model_name = "m2m100"
        m2m100.device = "cpu"

        result = TranslationService(_settings(True)).translate("Hello", None, None)

        openai_class.assert_not_called()
        self.assertEqual(result.translated_text, "你好")
        self.assertEqual(result.detected_source_lang, "en")
        self.assertEqual(result.target_lang, "zh")

    @patch("translator_server.services.translation_service.OpenAITranslator")
    @patch("translator_server.services.translation_service.M2MTranslator")
    @patch("translator_server.services.translation_service.LanguageDetector")
    def test_openai_mode_does_not_initialize_local_models_and_accepts_extra_language(
        self,
        detector_class: Mock,
        m2m100_class: Mock,
        openai_class: Mock,
    ) -> None:
        translator = openai_class.return_value
        translator.normalize_lang.side_effect = lambda lang: lang.strip().lower().replace("_", "-")
        translator.translate.return_value = OpenAITranslation("translated", "sat")
        translator.model_name = "test-model"
        translator.device = "remote"

        result = TranslationService(_settings(False)).translate("input", None, None)

        detector_class.assert_not_called()
        m2m100_class.assert_not_called()
        translator.translate.assert_called_once_with("input", None, "zh")
        self.assertEqual(result.detected_source_lang, "sat")
        self.assertEqual(result.source_lang, "sat")
        self.assertEqual(result.device, "remote")
        self.assertEqual(
            set(asdict(result)),
            {
                "translated_text",
                "detected_source_lang",
                "source_lang",
                "target_lang",
                "model_name",
                "device",
                "took_ms",
            },
        )

    @patch("translator_server.services.translation_service.OpenAITranslator")
    def test_openai_mode_prefers_explicit_source_language(self, openai_class: Mock) -> None:
        translator = openai_class.return_value
        translator.normalize_lang.side_effect = lambda lang: lang.strip().lower().replace("_", "-")
        translator.translate.return_value = OpenAITranslation("translated", "en")
        translator.model_name = "test-model"
        translator.device = "remote"

        result = TranslationService(_settings(False)).translate("input", "KLINGON", "FR")

        translator.translate.assert_called_once_with("input", "klingon", "fr")
        self.assertEqual(result.detected_source_lang, "klingon")
        self.assertEqual(result.source_lang, "klingon")
        self.assertEqual(result.target_lang, "fr")


if __name__ == "__main__":
    unittest.main()
