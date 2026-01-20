"""Parsing tests (placeholder)."""

import pytest

from materialcard.parse_regex import parse_material_from_text


@pytest.mark.xfail(reason="not implemented")
def test_parse_material_from_text_not_implemented() -> None:
    parse_material_from_text("example")
