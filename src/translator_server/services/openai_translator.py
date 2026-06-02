from __future__ import annotations

import json
import os
from dataclasses import dataclass

from openai import OpenAI

from translator_server.exceptions import TranslationError


@dataclass(slots=True)
class OpenAITranslation:
    translated_text: str
    detected_source_lang: str


class OpenAITranslator:
    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self._model_name = model

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def device(self) -> str:
        return "remote"

    def translate(self, text: str, source_lang: str | None, target_lang: str) -> OpenAITranslation:
        source_instruction = (
            f"The source language is explicitly specified as {source_lang}."
            if source_lang
            else "Detect the source language from the input text."
        )
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the user's text accurately. Preserve meaning, formatting, and line breaks. "
                            "Return the result only by calling return_translation. "
                            "Use a concise lowercase language code for detected_source_lang."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{source_instruction}\n"
                            f"Translate into language code: {target_lang}\n"
                            "Text to translate:\n"
                            f"{text}"
                        ),
                    },
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "return_translation",
                            "description": "Return the translated text and detected source language.",
                            "strict": True,
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "translated_text": {
                                        "type": "string",
                                        "description": "The translated text.",
                                    },
                                    "detected_source_lang": {
                                        "type": "string",
                                        "description": "The concise lowercase source language code.",
                                    },
                                },
                                "required": ["translated_text", "detected_source_lang"],
                                "additionalProperties": False,
                            },
                        },
                    }
                ],
                tool_choice={"type": "function", "function": {"name": "return_translation"}},
                parallel_tool_calls=False,
                extra_body={
                    "enable_thinking": False,
                    "chat_template_kwargs": {
                        "enable_thinking": False,
                    },
                },
            )
        except Exception as exc:
            raise TranslationError(f"OpenAI translation request failed: {exc}") from exc

        try:
            tool_calls = completion.choices[0].message.tool_calls or []
            tool_call = next(
                call for call in tool_calls if call.function.name == "return_translation"
            )
            arguments = json.loads(tool_call.function.arguments)
            translated_text = arguments["translated_text"]
            detected_source_lang = arguments["detected_source_lang"]
            if not isinstance(translated_text, str) or not translated_text.strip():
                raise ValueError("translated_text must be a non-empty string")
            if not isinstance(detected_source_lang, str) or not detected_source_lang.strip():
                raise ValueError("detected_source_lang must be a non-empty string")
        except (AttributeError, IndexError, KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TranslationError(f"Invalid OpenAI translation response: {exc}") from exc

        return OpenAITranslation(
            translated_text=translated_text,
            detected_source_lang=self.normalize_lang(detected_source_lang),
        )

    @staticmethod
    def normalize_lang(lang: str) -> str:
        return lang.strip().lower().replace("_", "-")
