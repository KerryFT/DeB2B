from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, time
from enum import StrEnum


class AutomationMode(StrEnum):
    DISABLED = "disabled"
    SHADOW = "shadow"
    CANARY = "canary"
    ENABLED = "enabled"


@dataclass(frozen=True, slots=True)
class AutomationPolicy:
    mode: AutomationMode = AutomationMode.DISABLED
    policy_version: str = "auto-email-v1"
    value_cap_minor: int = 10_000_000
    max_days_overdue: int = 14
    minimum_historical_approvals: int = 5
    maximum_edit_reject_rate: float = 0.05
    daily_send_cap: int = 10
    frequency_cap_days: int = 7
    canary_percent: int = 0
    quiet_hours_start: time = time(20)
    quiet_hours_end: time = time(8)
    tenant_kill_switch: bool = True


@dataclass(frozen=True, slots=True)
class AutomationCandidate:
    tenant_id: str
    case_id: str
    case_version: int
    outstanding_minor: int
    days_overdue: int
    paid: bool
    disputed: bool
    promise_broken: bool
    manual_review: bool
    ambiguity: bool
    recipient: str
    recipient_verified: bool
    recipient_suppressed: bool
    recipient_opted_out: bool
    attachment_allowlisted: bool
    template_preapproved: bool
    template_has_forbidden_language: bool
    evidence_complete: bool
    historical_approvals: int
    edit_reject_rate: float
    channel_healthy: bool
    sent_today: int
    last_sent_at: datetime | None
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class AutomationDecision:
    eligible: bool
    disposition: str
    exclusions: tuple[str, ...]
    policy_version: str
    idempotency_key: str


def evaluate_automation(
    candidate: AutomationCandidate,
    policy: AutomationPolicy,
    *,
    global_kill_switch: bool = True,
    observed_error_rate: float = 0.0,
    circuit_breaker_threshold: float = 0.05,
) -> AutomationDecision:
    exclusions: list[str] = []
    if policy.mode == AutomationMode.DISABLED:
        exclusions.append("automation_disabled")
    if global_kill_switch or policy.tenant_kill_switch:
        exclusions.append("kill_switch_active")
    if observed_error_rate >= circuit_breaker_threshold:
        exclusions.append("circuit_breaker_open")
    checks = {
        "already_paid": candidate.paid or candidate.outstanding_minor <= 0,
        "active_dispute": candidate.disputed,
        "broken_promise": candidate.promise_broken,
        "manual_review": candidate.manual_review,
        "ambiguous_case": candidate.ambiguity,
        "unverified_recipient": not candidate.recipient_verified,
        "suppressed_recipient": candidate.recipient_suppressed,
        "recipient_opted_out": candidate.recipient_opted_out,
        "attachment_not_allowlisted": not candidate.attachment_allowlisted,
        "template_not_preapproved": not candidate.template_preapproved,
        "forbidden_language": candidate.template_has_forbidden_language,
        "missing_evidence": not candidate.evidence_complete,
        "value_cap_exceeded": candidate.outstanding_minor > policy.value_cap_minor,
        "overdue_window_exceeded": candidate.days_overdue > policy.max_days_overdue,
        "insufficient_approval_history": candidate.historical_approvals
        < policy.minimum_historical_approvals,
        "edit_reject_rate_too_high": candidate.edit_reject_rate > policy.maximum_edit_reject_rate,
        "channel_unhealthy": not candidate.channel_healthy,
        "daily_cap_reached": candidate.sent_today >= policy.daily_send_cap,
    }
    exclusions.extend(name for name, blocked in checks.items() if blocked)
    local_time = candidate.evaluated_at.timetz().replace(tzinfo=None)
    if local_time >= policy.quiet_hours_start or local_time < policy.quiet_hours_end:
        exclusions.append("quiet_hours")
    if candidate.last_sent_at is not None:
        since_last = candidate.evaluated_at - candidate.last_sent_at
        if since_last.days < policy.frequency_cap_days:
            exclusions.append("cooling_period")
    if policy.mode == AutomationMode.CANARY:
        bucket = (
            int(
                hashlib.sha256(f"{candidate.tenant_id}:{candidate.case_id}".encode()).hexdigest()[
                    :8
                ],
                16,
            )
            % 100
        )
        if bucket >= policy.canary_percent:
            exclusions.append("outside_canary")
    idempotency_key = (
        f"{candidate.tenant_id}:{candidate.case_id}:auto-email:"
        f"v{candidate.case_version}:{policy.policy_version}"
    )
    eligible = not exclusions
    if policy.mode == AutomationMode.SHADOW:
        # Shadow computes a counterfactual eligibility but is never dispatchable.
        safety_exclusions = [item for item in exclusions if item not in {"kill_switch_active"}]
        disposition = "SHADOW_ELIGIBLE" if not safety_exclusions else "SHADOW_BLOCKED"
        return AutomationDecision(
            not safety_exclusions,
            disposition,
            tuple(exclusions),
            policy.policy_version,
            idempotency_key,
        )
    disposition = "ENQUEUE" if eligible else "BLOCKED"
    return AutomationDecision(
        eligible, disposition, tuple(exclusions), policy.policy_version, idempotency_key
    )


def revalidate_before_send(
    original: AutomationCandidate,
    current: AutomationCandidate,
    policy: AutomationPolicy,
    *,
    global_kill_switch: bool,
) -> AutomationDecision:
    if original.case_version != current.case_version:
        return AutomationDecision(
            False,
            "BLOCKED",
            ("stale_case_version",),
            policy.policy_version,
            f"{current.tenant_id}:{current.case_id}:stale",
        )
    if original.recipient.casefold() != current.recipient.casefold():
        return AutomationDecision(
            False,
            "BLOCKED",
            ("recipient_changed",),
            policy.policy_version,
            f"{current.tenant_id}:{current.case_id}:recipient-changed",
        )
    return evaluate_automation(current, policy, global_kill_switch=global_kill_switch)
