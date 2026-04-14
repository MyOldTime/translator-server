from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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
    basic_auth_username: str
    basic_auth_password: str

    @classmethod
    def load(cls) -> "Settings":
        root_dir = Path(__file__).resolve().parents[2]
        return cls(
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
            device=os.getenv("TRANSLATION_DEVICE"),
            num_beams=int(os.getenv("NUM_BEAMS", "1")),
            basic_auth_username=os.getenv("BASIC_AUTH_USERNAME", "admin"),
            basic_auth_password=os.getenv("BASIC_AUTH_PASSWORD", "Admin@123"),
        )
