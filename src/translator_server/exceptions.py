class TranslationError(Exception):
    """Base exception for translation failures."""


class ConfigurationError(TranslationError):
    """Raised when the application configuration is invalid."""


class UnsupportedLanguageError(TranslationError):
    """Raised when the requested language is not supported."""
