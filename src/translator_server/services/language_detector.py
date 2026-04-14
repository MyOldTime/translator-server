from __future__ import annotations

from pathlib import Path

import fasttext

from translator_server.exceptions import ConfigurationError


class LanguageDetector:
    def __init__(self, model_path: Path):
        if not model_path.exists():
            raise ConfigurationError(f"Language detection model not found: {model_path}")
        self.model = fasttext.load_model(str(model_path))

    def detect(self, text: str) -> str:
        labels, _ = self.model.predict(text.replace("\n", " "), k=1)
        return labels[0].replace("__label__", "").lower()
