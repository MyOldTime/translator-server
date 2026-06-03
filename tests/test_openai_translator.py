from __future__ import annotations

import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from translator_server.exceptions import TranslationError
from translator_server.services.openai_translator import OpenAITranslator


def _completion(arguments: str, function_name: str = "return_translation") -> SimpleNamespace:
    function = SimpleNamespace(name=function_name, arguments=arguments)
    tool_call = SimpleNamespace(function=function)
    message = SimpleNamespace(tool_calls=[tool_call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class OpenAITranslatorTests(unittest.TestCase):
    @patch("translator_server.services.openai_translator.OpenAI")
    def test_passes_base_url_and_uses_forced_strict_function(self, openai: Mock) -> None:
        client = openai.return_value
        client.chat.completions.create.return_value = _completion(
            json.dumps({"translated_text": "你好", "detected_source_lang": "EN"})
        )

        translator = OpenAITranslator(api_key="secret", model="test-model", base_url="https://example.com/v1")
        result = translator.translate("Hello", None, "zh")

        openai.assert_called_once_with(api_key="secret", base_url="https://example.com/v1")
        kwargs = client.chat.completions.create.call_args.kwargs
        function = kwargs["tools"][0]["function"]
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["tool_choice"], {"type": "function", "function": {"name": "return_translation"}})
        self.assertFalse(kwargs["parallel_tool_calls"])
        self.assertEqual(
            kwargs["extra_body"],
            {
                "enable_thinking": False,
                "chat_template_kwargs": {
                    "enable_thinking": False,
                },
            },
        )
        self.assertTrue(function["strict"])
        self.assertFalse(function["parameters"]["additionalProperties"])
        self.assertEqual(result.translated_text, "你好")
        self.assertEqual(result.detected_source_lang, "en")
        self.assertEqual(translator.device, "remote")

    @patch("translator_server.services.openai_translator.OpenAI")
    def test_wraps_sdk_errors(self, openai: Mock) -> None:
        openai.return_value.chat.completions.create.side_effect = RuntimeError("offline")
        translator = OpenAITranslator(api_key="secret", model="test-model")

        with self.assertRaisesRegex(TranslationError, "OpenAI translation request failed"):
            translator.translate("Hello", None, "zh")

    @patch("translator_server.services.openai_translator.OpenAI")
    def test_rejects_invalid_function_arguments(self, openai: Mock) -> None:
        openai.return_value.chat.completions.create.return_value = _completion("{invalid")
        translator = OpenAITranslator(api_key="secret", model="test-model")

        with self.assertRaisesRegex(TranslationError, "Invalid OpenAI translation response"):
            translator.translate("Hello", None, "zh")

    @patch("translator_server.services.openai_translator.OpenAI")
    def test_rejects_missing_function_call(self, openai: Mock) -> None:
        openai.return_value.chat.completions.create.return_value = _completion(
            json.dumps({"translated_text": "你好", "detected_source_lang": "en"}),
            function_name="other_function",
        )
        translator = OpenAITranslator(api_key="secret", model="test-model")

        with self.assertRaisesRegex(TranslationError, "Invalid OpenAI translation response"):
            translator.translate("Hello", None, "zh")


if __name__ == "__main__":
    unittest.main()
