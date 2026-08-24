from __future__ import annotations

import argparse
import json
import struct
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class DocumentBudgetExceeded(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class OCRLine:
    text: str
    confidence: float
    polygon: list[list[float]]


def check_image_budget(path: Path, *, max_pixels: int = 40_000_000) -> None:
    header = path.read_bytes()[:24]
    if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) == 24:
        width, height = struct.unpack(">II", header[16:24])
        if width <= 0 or height <= 0 or width * height > max_pixels:
            raise DocumentBudgetExceeded(f"image exceeds {max_pixels} pixel budget")
        return
    from PIL import Image

    with Image.open(path) as image:
        width, height = image.size
        if width <= 0 or height <= 0 or width * height > max_pixels:
            raise DocumentBudgetExceeded(f"image exceeds {max_pixels} pixel budget")


def ocr_image(path: Path, *, timeout_seconds: float = 120.0) -> list[OCRLine]:
    check_image_budget(path)
    started = time.monotonic()
    from paddleocr import PaddleOCR

    engine = PaddleOCR(
        lang="vi",
        enable_mkldnn=False,
        cpu_threads=2,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
    lines = []
    for result in engine.predict(str(path)):
        payload: dict[str, Any] = result.json.get("res", {})
        texts = payload.get("rec_texts", [])
        scores = payload.get("rec_scores", [])
        polygons = payload.get("dt_polys", [])
        for text, score, polygon in zip(texts, scores, polygons, strict=False):
            lines.append(
                OCRLine(
                    str(text),
                    float(score),
                    [[float(point[0]), float(point[1])] for point in polygon],
                )
            )
        if time.monotonic() - started > timeout_seconds:
            raise TimeoutError("OCR time budget exceeded")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    lines = ocr_image(args.path, timeout_seconds=args.timeout)
    print(json.dumps([asdict(line) for line in lines], ensure_ascii=False))


if __name__ == "__main__":
    main()
