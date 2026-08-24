# V1 architecture decisions

## ADR-V1-001 — Extend canonical connector primitives

MISA, Outlook and Zalo reuse tenant connector configuration, cursor, inbox deduplication,
failure/dead-letter, audit and outbox primitives. `Communication.provider` remains the single email
model. MISA maps external IDs/versions to existing Customer/Invoice entities and is read-only until
a specific tenant entitlement and write-back contract are approved.

## ADR-V1-002 — Fixed roles over centralized permissions

V1 keeps fixed default roles plus legacy MVP aliases, but endpoints authorize permission strings.
Unknown roles have zero permissions. This permits a future custom-role table without rewriting API
policy. Backend/RLS enforce tenant scope; UI visibility is not trusted.

## ADR-V1-003 — Declarative customer rules

Rules are Pydantic-validated JSON, never executable code. Safety checks are hard-coded; tenant
policy outranks customer rules, which outrank defaults. Publish is maker-checker and stored workflow
inputs retain evaluated versions.

## ADR-V1-004 — Baseline forecast before ML

The released forecast is deterministic due-date/promise/history logic with uncertainty and temporal
backtest. Advanced ML is explicitly disabled until a time-split dataset beats the baseline release
criterion. Forecast output cannot transition financial state.

## ADR-V1-005 — Metadata-only LLM analytics

Online operational events and offline evaluation rows are stored separately. Pricing is
effective-dated and external to business code; unknown pricing is valid. No raw prompt, email,
document or secret is retained for analytics.

## Migration strategy

`f19c7a4d2e10` creates new V1 tables and nullable/additive reconciliation fields, avoiding rewrites
of existing large tables. Post-deploy sync/forecast jobs backfill incrementally. Roll forward is
preferred; downgrade requires stopping writers and verifying V1 tables are safe to remove.
