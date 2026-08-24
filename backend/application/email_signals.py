from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

DATE_PATTERN = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
DISPUTE_TERMS = ("tranh chấp", "không đồng ý", "sai hóa đơn", "dispute")
PROMISE_TERMS = ("cam kết thanh toán", "sẽ thanh toán", "promise to pay")


@dataclass(frozen=True, slots=True)
class EmailSignals:
    summary: str
    disputed: bool
    promise_date: date | None
    evidence_quote: str


def extract_email_signals(body: str, *, today: date | None = None) -> EmailSignals:
    del today
    compact = " ".join(body.split())
    lowered = compact.casefold()
    disputed = any(term in lowered for term in DISPUTE_TERMS)
    promise_date = None
    if any(term in lowered for term in PROMISE_TERMS):
        match = DATE_PATTERN.search(compact)
        if match:
            promise_date = datetime.strptime(match.group(0), "%d/%m/%Y").date()
    return EmailSignals(compact[:240], disputed, promise_date, compact[:500])
