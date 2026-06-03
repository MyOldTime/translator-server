from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from translator_server.config import Settings
from translator_server.exceptions import ConfigurationError


class SettingsTests(unittest.TestCase):
    def test_defaults_to_m2m100_without_openai_configuration(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.load()

        self.assertTrue(settings.use_m2m100)
        self.assertIsNone(settings.openai_api_key)
        self.assertIsNone(settings.openai_model)
        self.assertEqual(settings.log_level, "INFO")
        self.assertEqual(settings.translate_max_concurrency, 1)
        self.assertEqual(settings.translate_queue_size, 1)
        self.assertEqual(settings.translate_queue_timeout_seconds, 2)

    def test_openai_mode_requires_api_key(self) -> None:
        with patch.dict(os.environ, {"M2M100": "false", "OPENAI_MODEL": "test-model"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "OPENAI_API_KEY"):
                Settings.load()

    def test_openai_mode_requires_model(self) -> None:
        with patch.dict(os.environ, {"M2M100": "false", "OPENAI_API_KEY": "secret"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "OPENAI_MODEL"):
                Settings.load()

    def test_openai_mode_rejects_blank_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {"M2M100": "false", "OPENAI_API_KEY": "  ", "OPENAI_MODEL": "test-model"},
            clear=True,
        ):
            with self.assertRaisesRegex(ConfigurationError, "OPENAI_API_KEY"):
                Settings.load()

    def test_rejects_invalid_boolean(self) -> None:
        with patch.dict(os.environ, {"M2M100": "sometimes"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "Invalid boolean value"):
                Settings.load()

    def test_rejects_invalid_log_level(self) -> None:
        with patch.dict(os.environ, {"LOG_LEVEL": "verbose"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "LOG_LEVEL"):
                Settings.load()

    def test_rejects_invalid_translate_max_concurrency(self) -> None:
        with patch.dict(os.environ, {"TRANSLATE_MAX_CONCURRENCY": "0"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "TRANSLATE_MAX_CONCURRENCY"):
                Settings.load()

    def test_rejects_invalid_translate_queue_size(self) -> None:
        with patch.dict(os.environ, {"TRANSLATE_QUEUE_SIZE": "-1"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "TRANSLATE_QUEUE_SIZE"):
                Settings.load()

    def test_rejects_invalid_translate_queue_timeout(self) -> None:
        with patch.dict(os.environ, {"TRANSLATE_QUEUE_TIMEOUT_SECONDS": "0"}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "TRANSLATE_QUEUE_TIMEOUT_SECONDS"):
                Settings.load()


if __name__ == "__main__":
    unittest.main()
