from __future__ import annotations

from datetime import date, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class RuleType(StrEnum):
    REQUIRED_DOCUMENTS = "required_documents"
    DUE_DATE = "due_date"
    GRACE_PERIOD = "grace_period"
    TOLERANCE = "tolerance"
    CONTACT_ROUTE = "contact_route"
    ALLOWED_CHANNEL = "allowed_channel"
    REMINDER_CADENCE = "reminder_cadence"


class RuleScope(StrEnum):
    DEFAULT = "default"
    CUSTOMER = "customer"
    TENANT = "tenant"


class RuleDefinition(BaseModel):
    rule_type: RuleType
    scope: RuleScope
    priority: int = Field(default=100, ge=0, le=10_000)
    effective_from: date
    expires_on: date | None = None
    value: dict[str, Any]
    version: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_definition(self) -> RuleDefinition:
        if self.expires_on is not None and self.expires_on < self.effective_from:
            raise ValueError("rule expiry precedes effective date")
        required: dict[RuleType, tuple[str, ...]] = {
            RuleType.REQUIRED_DOCUMENTS: ("documents",),
            RuleType.DUE_DATE: ("days", "basis"),
            RuleType.GRACE_PERIOD: ("days",),
            RuleType.TOLERANCE: ("amount_minor",),
            RuleType.CONTACT_ROUTE: ("contacts",),
            RuleType.ALLOWED_CHANNEL: ("channels",),
            RuleType.REMINDER_CADENCE: ("days",),
        }
        missing = [key for key in required[self.rule_type] if key not in self.value]
        if missing:
            raise ValueError(f"rule value missing: {', '.join(missing)}")
        if "days" in self.value and (
            not isinstance(self.value["days"], int) or self.value["days"] < 0
        ):
            raise ValueError("days must be a non-negative integer")
        if self.rule_type == RuleType.ALLOWED_CHANNEL:
            allowed = {"gmail", "outlook", "zalo"}
            if not set(self.value["channels"]) <= allowed:
                raise ValueError("unsupported communication channel")
        return self


class RuleEvaluation(BaseModel):
    values: dict[str, Any]
    applied_versions: list[int]
    explanation: list[str]


def detect_conflicts(rules: list[RuleDefinition]) -> list[str]:
    conflicts: list[str] = []
    for index, left in enumerate(rules):
        for right in rules[index + 1 :]:
            overlap = left.expires_on is None or right.effective_from <= left.expires_on
            reverse_overlap = right.expires_on is None or left.effective_from <= right.expires_on
            if (
                left.rule_type == right.rule_type
                and left.scope == right.scope
                and left.priority == right.priority
                and overlap
                and reverse_overlap
                and left.value != right.value
            ):
                conflicts.append(
                    f"conflicting {left.scope.value}/{left.rule_type.value} rules at priority "
                    f"{left.priority}"
                )
    return conflicts


_SCOPE_PRECEDENCE = {RuleScope.DEFAULT: 0, RuleScope.CUSTOMER: 1, RuleScope.TENANT: 2}


def evaluate_rules(rules: list[RuleDefinition], *, as_of: date) -> RuleEvaluation:
    active = [
        rule
        for rule in rules
        if rule.effective_from <= as_of and (rule.expires_on is None or as_of <= rule.expires_on)
    ]
    conflicts = detect_conflicts(active)
    if conflicts:
        raise ValueError("; ".join(conflicts))
    winners: dict[RuleType, RuleDefinition] = {}
    # Tenant policy outranks customer, which outranks defaults. Within a scope, lower numeric
    # priority wins; version breaks a same-value tie deterministically.
    for rule in sorted(
        active,
        key=lambda item: (
            _SCOPE_PRECEDENCE[item.scope],
            -item.priority,
            item.version,
        ),
    ):
        winners[rule.rule_type] = rule
    return RuleEvaluation(
        values={kind.value: rule.value for kind, rule in winners.items()},
        applied_versions=[rule.version for rule in winners.values()],
        explanation=[
            f"{kind.value}=v{rule.version} ({rule.scope.value}, priority {rule.priority})"
            for kind, rule in winners.items()
        ],
    )


def calculate_due_date(issue_date: date, evaluation: RuleEvaluation) -> date:
    due = evaluation.values.get(RuleType.DUE_DATE.value, {"days": 30, "basis": "issue_date"})
    if due["basis"] != "issue_date":
        raise ValueError("selected due-date basis requires manual evidence")
    return issue_date + timedelta(days=int(due["days"]))
