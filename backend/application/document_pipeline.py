from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from enum import StrEnum


class ProcessingRoute(StrEnum):
    NATIVE_TEXT = "NATIVE_TEXT"
    DOCLING_LAYOUT = "DOCLING_LAYOUT"
    PADDLE_OCR = "PADDLE_OCR"
    MANUAL_REVIEW = "MANUAL_REVIEW"


@dataclass(frozen=True, slots=True)
class PageProfile:
    page: int
    character_count: int
    has_native_text: bool
    route: ProcessingRoute


def choose_page_route(
    *, character_count: int, has_complex_layout: bool, image_quality: float = 1.0
) -> ProcessingRoute:
    if character_count >= 40 and not has_complex_layout:
        return ProcessingRoute.NATIVE_TEXT
    if character_count >= 10 or has_complex_layout:
        return ProcessingRoute.DOCLING_LAYOUT
    if image_quality >= 0.2:
        return ProcessingRoute.PADDLE_OCR
    return ProcessingRoute.MANUAL_REVIEW


def profile_pdf(content: bytes, *, native_threshold: int = 40) -> list[PageProfile]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    profiles = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        route = choose_page_route(
            character_count=len(text),
            has_complex_layout=False,
            image_quality=1.0,
        )
        profiles.append(PageProfile(page_number, len(text), bool(text), route))
    return profiles


def processing_cache_key(*, sha256: str, pipeline_version: str, route: ProcessingRoute) -> str:
    source = f"{sha256}:{pipeline_version}:{route.value}"
    return hashlib.sha256(source.encode()).hexdigest()
