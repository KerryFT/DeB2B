import struct
from pathlib import Path

import pytest

from services.document_worker.main import DocumentBudgetExceeded, check_image_budget


def test_image_bomb_is_rejected_before_ocr(tmp_path: Path) -> None:
    path = tmp_path / "too-large.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 101, 101))
    with pytest.raises(DocumentBudgetExceeded, match="pixel budget"):
        check_image_budget(path, max_pixels=10_000)
