"""Renderer tests (placeholder)."""

import pytest

from materialcard.models import ApprovalContext, ApprovalRequestData, MaterialData
from materialcard.renderer_docx import render_docx


@pytest.mark.xfail(reason="not implemented")
def test_render_docx_not_implemented(tmp_path) -> None:
    template = tmp_path / "template.docx"
    template.write_text("placeholder", encoding="utf-8")
    data = ApprovalRequestData(material=MaterialData(), context=ApprovalContext())
    render_docx(data, template, tmp_path / "out.docx")
