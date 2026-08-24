# OCR runtime decision

P0 spike on 2026-08-24 found that PaddleOCR 3.7 imports only after removing the conflicting
`opencv-python 5.0` package, while its transitive Windows/Python 3.13 Torch wheel fails loading
`shm.dll`. The supported MVP path therefore isolates Docling/PaddleOCR in a Linux Python 3.12
worker. API/web development remains Python 3.13/Node 24.

The worker owns its cache inside the container, has no host-home writes, and is validated with
`tools.spikes.ocr_smoke`. A failed worker or low-confidence result routes the document to manual
review; it never blocks API readiness or triggers an external action.

