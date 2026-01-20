"""Custom exceptions for materialcard."""


class MaterialCardError(Exception):
    """Base error for materialcard."""


class NonTextPdfError(MaterialCardError):
    """Raised when a PDF does not contain enough text."""


class ParseError(MaterialCardError):
    """Raised when parsing text fails."""


class ContextError(MaterialCardError):
    """Raised when context loading fails."""


class RenderError(MaterialCardError):
    """Raised when rendering fails."""
