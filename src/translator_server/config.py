from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from translator_server.exceptions import ConfigurationError


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value for {name}: {value}")


def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip() or None


@dataclass(slots=True)
class Settings:
    app_name: str
    app_env: str
    host: str
    port: int
    lid_model_path: Path
    translation_model_path: Path
    target_lang: str
    max_batch_size: int
    max_input_chars: int
    segment_max_chars: int
    max_length: int
    max_new_tokens: int
    device: str | None
    num_beams: int
    use_m2m100: bool
    openai_api_key: str | None
    openai_base_url: str | None
    openai_model: str | None
    basic_auth_username: str
    basic_auth_password: str

    @classmethod
    def load(cls) -> "Settings":
        root_dir = Path(__file__).resolve().parents[2]
        settings = cls(
            app_name=os.getenv("APP_NAME", "translator-server"),
            app_env=os.getenv("APP_ENV", "dev"),
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=int(os.getenv("APP_PORT", "8191")),
            lid_model_path=Path(os.getenv("LID_MODEL_PATH", root_dir / "models" / "lid.176.bin")).resolve(),
            translation_model_path=Path(
                os.getenv("TRANSLATION_MODEL_PATH", root_dir / "models" / "m2m100_418M")
            ).resolve(),
            target_lang=os.getenv("DEFAULT_TARGET_LANG", "zh"),
            max_batch_size=int(os.getenv("MAX_BATCH_SIZE", "8")),
            max_input_chars=int(os.getenv("MAX_INPUT_CHARS", "20000")),
            segment_max_chars=int(os.getenv("SEGMENT_MAX_CHARS", "400")),
            max_length=int(os.getenv("MAX_LENGTH", "512")),
            max_new_tokens=int(os.getenv("MAX_NEW_TOKENS", "512")),
            device=os.getenv("TRANSLATION_DEVICE", "auto"),
            num_beams=int(os.getenv("NUM_BEAMS", "1")),
            use_m2m100=_get_bool_env("M2M100", True),
            openai_api_key=_get_optional_env("OPENAI_API_KEY"),
            openai_base_url=_get_optional_env("OPENAI_BASE_URL"),
            openai_model=_get_optional_env("OPENAI_MODEL"),
            basic_auth_username=os.getenv("BASIC_AUTH_USERNAME", "admin"),
            basic_auth_password=os.getenv("BASIC_AUTH_PASSWORD", "Admin@123"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.use_m2m100:
            return
        if not self.openai_api_key:
            raise ConfigurationError("OPENAI_API_KEY is required when M2M100=false")
        if not self.openai_model:
            raise ConfigurationError("OPENAI_MODEL is required when M2M100=false")
