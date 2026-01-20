"""Context loading utilities."""

from __future__ import annotations

import json
from pathlib import Path

from .exceptions import ContextError
from .models import ApprovalContext

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    yaml = None


def load_context(path: Path) -> ApprovalContext:
    """Load approval context from JSON or YAML."""

    if not path.exists():
        raise ContextError(f"Context file not found: {path}")

    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise ContextError("PyYAML is not installed. Install the yaml extra.")
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        else:
            raise ContextError(f"Unsupported context format: {suffix}")
    except json.JSONDecodeError as exc:
        raise ContextError("Invalid JSON context file.") from exc
    except Exception as exc:
        if isinstance(exc, ContextError):
            raise
        raise ContextError("Failed to load context file.") from exc

    if not isinstance(data, dict):
        raise ContextError("Context data must be a mapping.")

    return ApprovalContext(**data)
