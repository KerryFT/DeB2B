import io
import zipfile

import pytest

from backend.application.file_policy import UnsafeUpload, validate_upload


def xlsx_like(*names: str) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for name in names:
            archive.writestr(name, "fixture")
    return stream.getvalue()


def test_pdf_signature_and_filename_are_enforced() -> None:
    accepted = validate_upload(
        b"%PDF-1.7 fixture", filename="../../invoice?.pdf", content_type="application/pdf"
    )
    assert accepted.safe_name == "invoice_.pdf"
    with pytest.raises(UnsafeUpload):
        validate_upload(b"not a pdf", filename="invoice.pdf", content_type="application/pdf")


def test_xlsx_macro_is_rejected() -> None:
    with pytest.raises(UnsafeUpload, match="active content"):
        validate_upload(
            xlsx_like("xl/workbook.xml", "xl/vbaProject.bin"),
            filename="invoice.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
