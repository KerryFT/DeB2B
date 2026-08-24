from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BulkItem:
    approval_id: UUID
    case_id: UUID
    version: int
    expected_version: int
    channel: str
    recipient: str
    amount_minor: int
    attachment_count: int
    risk_flags: tuple[str, ...] = ()
    permitted: bool = True
    policy_valid: bool = True


@dataclass(frozen=True, slots=True)
class BulkPreview:
    eligible: tuple[BulkItem, ...]
    excluded: tuple[tuple[UUID, str], ...]
    total_minor: int
    channel: str | None


def preview_bulk(items: list[BulkItem], *, limit: int = 100) -> BulkPreview:
    if len(items) > limit:
        raise ValueError(f"bulk selection exceeds configured limit {limit}")
    eligible: list[BulkItem] = []
    excluded: list[tuple[UUID, str]] = []
    channels = {item.channel for item in items}
    for item in items:
        reason = None
        if len(channels) > 1:
            reason = "mixed_channel"
        elif not item.permitted:
            reason = "permission_denied"
        elif item.version != item.expected_version:
            reason = "stale_version"
        elif not item.policy_valid:
            reason = "policy_block"
        elif item.risk_flags:
            reason = "risk_review_required"
        if reason:
            excluded.append((item.approval_id, reason))
        else:
            eligible.append(item)
    return BulkPreview(
        tuple(eligible),
        tuple(excluded),
        sum(item.amount_minor for item in eligible),
        next(iter(channels)) if len(channels) == 1 else None,
    )
