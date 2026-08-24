# Security and privacy baseline

## Threat model

Protected assets are tenant financial records, documents/email, connector credentials, recipients,
approvals, audit history and derived predictions. Primary threats are cross-tenant IDOR, forged
identity/webhooks, malicious uploads and prompt injection, duplicate/wrong-recipient sends,
financial allocation corruption, secret leakage and an operator bypassing audit controls.

## Implemented controls

- OIDC JWT issuer/audience/JWKS validation; production dev-auth is rejected at startup.
- Membership plus backend permission checks; forced PostgreSQL RLS; application uses `ar_app`.
- Append-only audit privileges for the application role and transactional outbox/idempotency tables.
- Exact production CORS, trusted hosts, CSP/frame/content-type/referrer/permissions headers and HSTS
  without `includeSubDomains` or preload.
- Upload byte limit, MIME signature checks, safe filenames, XLSX active-content/entry limit,
  fail-closed ClamAV scan, tenant content-addressed keys and optional S3 SSE (provider encryption
  at rest remains a deployment verification gate).
- Metrics require a bearer secret in staging/production; structured logs avoid raw request bodies.
- Auto-send defaults disabled, global and tenant kill switches, recipient/state revalidation,
  caps and idempotency. Initial production config cannot enable external delivery.
- LLM routing can forbid external processing; analytics retain metadata rather than raw prompts.

## Required before public exposure

1. Implement browser authorization-code + PKCE or a server-side secure session. Cookies, if used,
   must be `Secure`, `HttpOnly`, `SameSite=Lax/Strict`, rotated and CSRF-protected for mutations.
2. Add composite tenant ownership constraints and negative cases across every foreign-key relation,
   raw file, derived table, aggregate and export.
3. Put auth, upload, AI/OCR, webhook and external-action routes behind distributed/edge rate limits.
4. Finish Outlook/Gmail webhook verification: secret/client-state/audience, timestamp window, replay
   protection, durable inbox dedup and catch-up reconciliation.
5. Add PDF page/decompression/parser budgets and a durable quarantine/job/manual-review lifecycle.
6. Scan dependencies/images in CI, retain SBOMs, triage critical/high findings and sign release
   images when the registry/deploy path is selected.
7. Verify least-privilege OAuth scopes: Outlook must not receive `Mail.Send` for draft-only use;
   MISA stays read-only; Zalo stays dry-run.

## Secrets

Secrets live only in Railway sealed/generated variables or the selected managed secret store.
Never place them in `NEXT_PUBLIC_*`, Git, images, logs, tickets or chat. Rotate OIDC/client secrets,
S3 keys, metrics tokens and connector tokens independently. Rotation must redeploy runtime services,
not rebuild the frontend. See `RUNBOOK.md` for the order.

## Privacy and retention

- Staging/test uses synthetic data only.
- Do not log raw email, contract/document bodies, prompts, access tokens or full provider responses.
- Minimize LLM context and record provider/model/purpose/provenance without sensitive content.
- Proposed retention: audit 7 years; raw documents 2 years unless legal hold; derived data follows
  source tenant retention; connector credentials delete on disconnect.
- Tenant export/delete must cover relational rows, objects, predictions, caches and job artifacts.
- These are engineering policies, not a legal compliance claim. Vietnamese data/privacy, tax,
  accounting, cross-border transfer and customer-contract requirements require legal review.

## Incident invariants

On suspected tenant leakage, wrong recipient, duplicate send or credential exposure: turn on global
and tenant kills, disable external connector delivery, preserve audit/outbox evidence, revoke the
affected credential, assess scope by tenant-safe IDs and follow `RUNBOOK.md`. Never replay an
external action until current state and idempotency are revalidated.
