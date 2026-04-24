"""Custom exceptions for materialcard."""


class MaterialCardError(Exception):
    """Base error for materialcard."""


class NonTextPdfError(MaterialCardError):
    """Raised when a PDF does not contain enough text."""

    def __init__(self, message: str, *, extracted_text: str = "") -> None:
        super().__init__(message)
        self.extracted_text = extracted_text


class ParseError(MaterialCardError):
    """Raised when parsing text fails."""


class ContextError(MaterialCardError):
    """Raised when context loading fails."""


class TemplateNotFoundError(MaterialCardError):
    """Raised when a DOCX template is missing."""


class RenderError(MaterialCardError):
    """Raised when rendering fails."""


class DataValidationError(MaterialCardError):
    """Raised when input data fails validation."""

