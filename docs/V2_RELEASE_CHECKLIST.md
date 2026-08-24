# V2 release checklist

- [x] Seven capabilities have domain, migration, API, UI, synthetic fixtures and tests.
- [x] Every derived table is tenant-owned with RLS/FORCE RLS.
- [x] Probability features are point-in-time; labels handle censoring; calibration is measured.
- [x] Cash-flow components reject duplicates and reconcile to invoice outstanding.
- [x] Dispute/escalation output contains evidence/reason codes and requires human decisions.
- [x] Customer profile labels are neutral; benchmark suppresses small cohorts.
- [x] Automation defaults disabled; tenant/global kill and external delivery default safe.
- [x] Safety tests cover paid, dispute, wrong recipient, duplicate key, stale version and kill switch.
- [ ] Live email send/bounce/complaint verified with tenant sandbox credentials (opt-in, not required).
- [ ] Tenant-specific production backtest and calibration approval (required before business rollout).

Production rollout remains blocked until the two unchecked tenant-specific items are deliberately
completed. Local V2 demo does not send email.
