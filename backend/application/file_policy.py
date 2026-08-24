from __future__ import annotations

import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import PurePath

ALLOWED = {
    "application/pdf": (b"%PDF-",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
}
SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class UnsafeUpload(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AcceptedUpload:
    safe_name: str
    sha256: str
    content_type: str
    size: int


def validate_upload(
    content: bytes, *, filename: str, content_type: str, max_bytes: int = 26_214_400
) -> AcceptedUpload:
    if not content or len(content) > max_bytes:
        raise UnsafeUpload("file is empty or exceeds size limit")
    signatures = ALLOWED.get(content_type)
    if not signatures or not any(content.startswith(signature) for signature in signatures):
        raise UnsafeUpload("declared content type does not match file signature")
    base = PurePath(filename).name
    safe_name = SAFE_NAME.sub("_", base)[:200] or "upload"
    if content_type.endswith("spreadsheetml.sheet"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = [name.lower() for name in archive.namelist()]
                if any(
                    "vbaproject" in name or name.endswith((".exe", ".dll", ".js")) for name in names
                ):
                    raise UnsafeUpload("active content is not allowed")
                if len(names) > 10_000:
                    raise UnsafeUpload("archive entry limit exceeded")
        except zipfile.BadZipFile as exc:
            raise UnsafeUpload("invalid XLSX archive") from exc
    return AcceptedUpload(
        safe_name, hashlib.sha256(content).hexdigest(), content_type, len(content)
    )
