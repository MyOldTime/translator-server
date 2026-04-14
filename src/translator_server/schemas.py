from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to translate.")
    source_lang: str | None = Field(default=None, description="Optional source language. If omitted, auto detect.")
    target_lang: str = Field(default="zh", min_length=2, description="Target language.")

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be empty")
        return cleaned

    @field_validator("source_lang", "target_lang")
    @classmethod
    def normalize_language(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().lower().replace("_", "-")


class TranslateResponse(BaseModel):
    translated_text: str
    detected_source_lang: str
    source_lang: str
    target_lang: str
    model_name: str
    took_ms: int


class HealthResponse(BaseModel):
    status: str
    app_name: str
    model_name: str
