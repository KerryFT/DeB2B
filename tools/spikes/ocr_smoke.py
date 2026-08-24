from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from paddleocr import PaddleOCR
from PIL import Image, ImageDraw, ImageFont


def main() -> None:
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="ar-ocr-") as temp_dir:
        target = Path(temp_dir) / "vi-ocr-smoke.png"
        image = Image.new("RGB", (1400, 260), "white")
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 46)
        expected = "HÓA ĐƠN INV-2026-0107 SỐ TIỀN 120.000.000 VND"
        ImageDraw.Draw(image).text((40, 80), expected, fill="black", font=font)
        image.save(target)
        engine = PaddleOCR(
            lang="vi",
            enable_mkldnn=False,
            cpu_threads=2,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        results = engine.predict(str(target))
        text = " ".join(
            str(item)
            for result in results
            for item in result.json.get("res", {}).get("rec_texts", [])
        )
    normalized = text.upper().replace(" ", "")
    passed = "INV-2026-0107".replace(" ", "") in normalized and "120.000.000" in normalized
    report = {
        "passed": passed,
        "expected": expected,
        "observed": text,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
