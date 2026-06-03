from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from openai import OpenAI

from translator_server.exceptions import TranslationError


logger = logging.getLogger(__name__)


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
            f"源语言已明确指定为 {source_lang}。"
            if source_lang
            else "请根据输入文本检测源语言。"
        )

        # if target_lang == 'zh':
        # 直接写死翻译为简体简体中文
        target_lang = 'zh(简体中文)'

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "请准确翻译用户文本，保留原意、格式和换行。"
                            "只能通过调用 return_translation 返回结果。"
                            "detected_source_lang 请使用简洁的小写语言代码。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"{source_instruction}\n"
                            f"请翻译为以下语言代码对应的语言：{target_lang}\n"
                            "待翻译文本：\n"
                            f"{text}"
                        ),
                    },
                ],
                tools=[
                    {
                        "type": "function",
                        "function": {
                            "name": "return_translation",
                            "description": "返回译文和检测到的源语言。",
                            "strict": True,
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "translated_text": {
                                        "type": "string",
                                        "description": "翻译后的文本。",
                                    },
                                    "detected_source_lang": {
                                        "type": "string",
                                        "description": "简洁的小写源语言代码。",
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
            logger.exception("OpenAI 兼容接口请求失败：model=%s 错误=%s", self.model_name, exc)
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
            logger.exception("OpenAI 兼容接口响应解析失败：model=%s 错误=%s", self.model_name, exc)
            raise TranslationError(f"Invalid OpenAI translation response: {exc}") from exc

        return OpenAITranslation(
            translated_text=translated_text,
            detected_source_lang=self.normalize_lang(detected_source_lang),
        )

    @staticmethod
    def normalize_lang(lang: str) -> str:
        return lang.strip().lower().replace("_", "-")
