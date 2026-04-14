"""Integration test for building and rendering Wrocław approvals."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from materialcard.builder import build_approval_request
from materialcard.models import ApprovalContext, MaterialData
from materialcard.renderer_docx import render_docx


def _write_minimal_docx_template(path: Path) -> None:
    content_types = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t>{{ investor_name }}</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>{{ project_title }}</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>
"""
    doc_rels = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>
"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>
"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", doc_rels)
        archive.writestr("word/styles.xml", styles_xml)


def test_integration_build_and_render_docx(tmp_path) -> None:
    pytest.importorskip("docxtpl")

    material = MaterialData(
        material_type="Material",
        description="Desc",
        attachments=[],
    )
    context = ApprovalContext(
        investor_name="Investor",
        project_title="Project",
        contractor_name="Contractor",
      manufacturer="Manufacturer",
      estimated_quantity="10",
        planned_delivery_date="2026-03-12",
        planned_installation_date="2026-03-13",
        prepared_by_name="Prepared",
        prepared_by_role="Role",
        attachments=[],
    )

    approval = build_approval_request(material, context)

    template_path = tmp_path / "template.docx"
    output_path = tmp_path / "output.docx"
    _write_minimal_docx_template(template_path)

    render_docx(approval, template_path, output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0

