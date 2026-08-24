# V2 threat and model-risk review

| Risk | Control and verification |
|---|---|
| Unauthorized automation enable | `AUTOMATION_MANAGE` RBAC, explicit confirmation, audited policy version |
| Kill-switch bypass | global + tenant switches evaluated on every decision and revalidation; tests |
| Stale state / paid or disputed before send | case version, payment/dispute and recipient revalidation immediately before delivery |
| Recipient manipulation | verified-recipient gate and changed-recipient race block |
| Duplicate or mass send | stable idempotency key, tenant unique constraint, daily/frequency caps, circuit breaker |
| Prompt injection / forbidden language | deterministic eligibility and policy filters; LLM never controls policy/tools |
| Cross-tenant IDOR/aggregate leakage | tenant predicates, RLS/FORCE RLS on every derived table, backend RBAC |
| Temporal/model leakage | snapshot accepts only events with `occurred_at <= as_of`; censored labels; time split |
| Model poisoning/staleness | versioned dataset/seed/provenance, champion threshold, stale fallback/rollback |
| Benchmark privacy/unfairness | minimum cohort suppression, attribution share, portfolio adjustment, warnings |

Residual limitations: the baseline is calibrated only on synthetic data and must be re-evaluated on
approved tenant history before business use. Live provider delivery/bounce/complaint ingestion is
not credential-verified; fake adapters and deterministic decision paths are the release evidence.
