from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    CASE_VIEW = "case:view"
    CASE_EDIT = "case:edit"
    FINANCIAL_EDIT = "financial:edit"
    DOCUMENT_VIEW = "document:view"
    DOCUMENT_DOWNLOAD = "document:download"
    EMAIL_SENSITIVE_VIEW = "email_sensitive:view"
    CONNECTOR_MANAGE = "connector:manage"
    RULE_CREATE = "rule:create"
    RULE_PUBLISH = "rule:publish"
    APPROVAL_SINGLE = "approval:single"
    APPROVAL_BULK = "approval:bulk"
    EXTERNAL_ACTION_TRIGGER = "external_action:trigger"
    EXTERNAL_ACTION_RETRY = "external_action:retry"
    LLM_DASHBOARD_VIEW = "llm_dashboard:view"
    USER_MANAGE = "user:manage"
    DATA_EXPORT = "data:export"
    DATA_DELETE = "data:delete"
    AUTOMATION_MANAGE = "automation:manage"
    AUTOMATION_AUDIT = "automation:audit"
    MODEL_GOVERNANCE_MANAGE = "model_governance:manage"
    DISPUTE_CORRECT = "dispute:correct"
    BENCHMARK_VIEW = "benchmark:view"


ALL_PERMISSIONS: frozenset[Permission] = frozenset(Permission)
READ_PERMISSIONS: frozenset[Permission] = frozenset(
    {Permission.CASE_VIEW, Permission.DOCUMENT_VIEW, Permission.EMAIL_SENSITIVE_VIEW}
)

# Fixed roles are deliberately centralized. Custom roles can later reference the same permissions
# without changing endpoint policy. Legacy MVP roles remain aliases during token/session migration.
ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "tenant_admin": ALL_PERMISSIONS,
    "ar_manager": ALL_PERMISSIONS - frozenset({Permission.USER_MANAGE, Permission.DATA_DELETE}),
    "ar_specialist": READ_PERMISSIONS
    | {
        Permission.CASE_EDIT,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.RULE_CREATE,
        Permission.EXTERNAL_ACTION_RETRY,
        Permission.DISPUTE_CORRECT,
    },
    "account_owner": READ_PERMISSIONS | {Permission.CASE_EDIT, Permission.DOCUMENT_DOWNLOAD},
    "approver": READ_PERMISSIONS
    | {
        Permission.DOCUMENT_DOWNLOAD,
        Permission.APPROVAL_SINGLE,
        Permission.APPROVAL_BULK,
        Permission.EXTERNAL_ACTION_TRIGGER,
        Permission.AUTOMATION_AUDIT,
    },
    "auditor": READ_PERMISSIONS
    | {
        Permission.DOCUMENT_DOWNLOAD,
        Permission.DATA_EXPORT,
        Permission.AUTOMATION_AUDIT,
        Permission.BENCHMARK_VIEW,
    },
    "admin": ALL_PERMISSIONS,
    "operator": READ_PERMISSIONS
    | {
        Permission.CASE_EDIT,
        Permission.FINANCIAL_EDIT,
        Permission.DOCUMENT_DOWNLOAD,
        Permission.RULE_CREATE,
        Permission.EXTERNAL_ACTION_RETRY,
    },
    "viewer": READ_PERMISSIONS,
}


def permissions_for_role(role: str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def is_allowed(role: str, permission: Permission) -> bool:
    return permission in permissions_for_role(role)
