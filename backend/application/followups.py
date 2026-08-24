from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FollowUpProposal:
    subject: str
    body: str
    evidence_ids: tuple[str, ...]
    version: int


def propose_follow_up(
    *, invoice_number: str, blocker: str, supported_facts: dict[str, tuple[str, str]], version: int
) -> FollowUpProposal:
    if not supported_facts:
        raise ValueError("follow-up requires supported facts")
    evidence_ids = tuple(sorted({evidence_id for _, evidence_id in supported_facts.values()}))
    facts = "\n".join(f"- {name}: {value}" for name, (value, _) in supported_facts.items())
    body = (
        f"Kính gửi Quý khách,\n\nLiên quan hóa đơn {invoice_number}, "
        f"hồ sơ đang có blocker {blocker}.\n{facts}\n\nVui lòng phản hồi để chúng tôi cập nhật."
    )
    return FollowUpProposal(
        subject=f"Đối soát hồ sơ {invoice_number}",
        body=body,
        evidence_ids=evidence_ids,
        version=version,
    )
