# V2 implementation tracker

| ID | Capability | Depends on | Acceptance evidence | Status |
|---|---|---|---|---|
| V2-00 | V1 audit, baseline, threat/model risk | V1 | V1 suites/build green; risks documented | done |
| V2-08 | Point-in-time features and model governance | V2-00 | future events excluded; versioned snapshots/runs/registry; RLS | done |
| V2-03 | Dispute root cause | V2-08 | taxonomy, evidence, correction/lifecycle, aggregate API/UI | done |
| V2-06 | Customer behavior | V2-08 | rolling as-of profile, neutral labels, provenance API/UI | done |
| V2-04 | Probability to pay | V2-08 | 7/14/30 baseline, censoring, calibration tests/API/UI | done |
| V2-05 | Cash-flow forecast | V2-04 | P10/P50/P90, currency aggregation, reconciliation/backtest | done |
| V2-02 | Escalation strategy | V2-03,V2-06 | evidence-backed human-only recommendations/fallback | done |
| V2-07 | Account-manager benchmark | V2-06 | raw/adjusted metrics, attribution, cohort suppression | done |
| V2-01 | Low-risk email automation | V2-08 | disabled default, shadow/canary, caps, kill/revalidation/idempotency | done |
| V2-09 | Cross-feature validation and operations | all | migrations, full tests/build, demo seed, rollback runbook | done |

“Done” means the vertical slice has schema/domain/API/UI/test coverage; it does not mean live email
delivery was enabled or verified.
