from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Iterable

import torch
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from zhconv import convert

from translator_server.exceptions import ConfigurationError, UnsupportedLanguageError

M2M100_SUPPORTED_LANGS = {
    "af", "am", "ar", "ast", "az", "ba", "be", "bg", "bn", "br", "bs", "ca", "ceb", "cs",
    "cy", "da", "de", "el", "en", "es", "et", "fa", "ff", "fi", "fr", "fy", "ga", "gd", "gl",
    "gu", "ha", "he", "hi", "hr", "ht", "hu", "hy", "id", "ig", "ilo", "is", "it", "ja", "jv",
    "ka", "kk", "km", "kn", "ko", "lb", "lg", "ln", "lo", "lt", "lv", "mg", "mk", "ml", "mn",
    "mr", "ms", "my", "ne", "nl", "no", "ns", "oc", "or", "pa", "pl", "ps", "pt", "ro", "ru",
    "sd", "si", "sk", "sl", "so", "sq", "sr", "ss", "su", "sv", "sw", "ta", "th", "tl", "tn",
    "tr", "uk", "ur", "uz", "vi", "wo", "xh", "yi", "yo", "zh", "zu",
}

LANGUAGE_ALIASES = {
    "fil": "tl",
    "nb": "no",
    "nn": "no",
    "zh-cn": "zh",
    "zh-hans": "zh",
    "zh-hk": "zh",
    "zh-mo": "zh",
    "zh-sg": "zh",
    "zh-tw": "zh",
    "zh-hant": "zh",
}


class M2MTranslator:
    def __init__(
        self,
        model_path: Path,
        device: str | None = None,
        max_length: int = 512,
        max_new_tokens: int = 512,
        max_batch_size: int = 8,
        segment_max_chars: int = 400,
        num_beams: int = 1,
    ) -> None:
        if not model_path.exists():
            raise ConfigurationError(f"Translation model directory not found: {model_path}")

        self.model_path = model_path
        self.max_length = max_length
        self.max_new_tokens = max_new_tokens
        self.max_batch_size = max_batch_size
        self.segment_max_chars = segment_max_chars
        self.num_beams = num_beams
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._lock = threading.RLock()

        self.tokenizer = M2M100Tokenizer.from_pretrained(str(model_path), local_files_only=True)
        self.model = M2M100ForConditionalGeneration.from_pretrained(
            str(model_path),
            local_files_only=True,
        ).to(self.device)
        self.model.eval()
        self.model.generation_config.max_length = None

    @property
    def model_name(self) -> str:
        return self.model_path.name

    def normalize_lang(self, lang: str) -> str:
        normalized = LANGUAGE_ALIASES.get(lang.lower().replace("_", "-"), lang.lower().replace("_", "-"))
        if normalized not in M2M100_SUPPORTED_LANGS:
            raise UnsupportedLanguageError(f"Unsupported language: {lang}")
        return normalized

    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        normalized_source = self.normalize_lang(source_lang)
        normalized_target = self.normalize_lang(target_lang)
        if normalized_source == normalized_target:
            return convert(text, "zh-cn") if normalized_target == "zh" else text

        segments = self._prepare_segments(text)
        translated_segments: list[str] = []
        for batch in self._batched(segments, self.max_batch_size):
            translated_segments.extend(
                self._translate_batch(batch, normalized_source, normalized_target)
            )

        output = "".join(translated_segments)
        return convert(output, "zh-cn") if normalized_target == "zh" else output

    def _translate_batch(self, texts: list[str], source_lang: str, target_lang: str) -> list[str]:
        self.tokenizer.src_lang = source_lang
        encoded = self.tokenizer(
            texts,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length,
        ).to(self.device)

        with self._lock, torch.inference_mode():
            generated = self.model.generate(
                **encoded,
                forced_bos_token_id=self.tokenizer.get_lang_id(target_lang),
                max_new_tokens=self.max_new_tokens,
                num_beams=self.num_beams,
                do_sample=False,
            )

        return self.tokenizer.batch_decode(generated, skip_special_tokens=True)

    def _prepare_segments(self, text: str) -> list[str]:
        units = self._split_into_units(text)
        packed: list[str] = []
        current = ""

        for unit in units:
            if not unit:
                continue

            if len(unit) > self.segment_max_chars:
                if current:
                    packed.append(current)
                    current = ""
                packed.extend(self._split_oversized_unit(unit))
                continue

            if current and len(current) + len(unit) > self.segment_max_chars:
                packed.append(current)
                current = unit
            else:
                current += unit

        if current:
            packed.append(current)

        return packed or [text]

    @staticmethod
    def _split_into_units(text: str) -> list[str]:
        units = re.findall(r".+?(?:\r?\n+|[。！？!?\.]+(?:\s+|$)|$)", text, flags=re.S)
        return units or [text]

    def _split_oversized_unit(self, unit: str) -> list[str]:
        pieces: list[str] = []
        remaining = unit
        separators = ["\n", "。", "！", "？", ".", "!", "?", ",", "，", ";", "；", " "]

        while len(remaining) > self.segment_max_chars:
            split_at = -1
            search_window = remaining[: self.segment_max_chars + 1]
            for separator in separators:
                position = search_window.rfind(separator)
                if position > split_at:
                    split_at = position

            if split_at <= 0:
                split_at = self.segment_max_chars
            else:
                split_at += 1

            pieces.append(remaining[:split_at])
            remaining = remaining[split_at:]

        if remaining:
            pieces.append(remaining)

        return pieces

    @staticmethod
    def _batched(items: list[str], batch_size: int) -> Iterable[list[str]]:
        for index in range(0, len(items), batch_size):
            yield items[index:index + batch_size]
