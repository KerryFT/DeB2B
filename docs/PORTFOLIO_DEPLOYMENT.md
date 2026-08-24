# Portfolio deployment: `app.deb2b.id.vn`

## Release decision

`CONDITIONAL GO` applies only to the constrained portfolio profile. The full production topology
remains `NO-GO`. The portfolio release stores synthetic/anonymized data only and deliberately
removes document upload/OCR, Temporal timers, MISA API/write-back, Outlook webhooks and email send.

## Topology and cost boundary

- `deb2b.id.vn`: existing WordPress; unchanged.
- `app.deb2b.id.vn`: Next.js on Vercel Hobby.
- `api.deb2b.id.vn`: FastAPI Docker web service on Render Free.
- PostgreSQL: Neon Free; schema revision `d8f31a6c4b20`.
- Authentication and Outlook: Microsoft authorization-code + PKCE, delegated `Mail.ReadWrite`.

Render can scale to zero and cold-start. Therefore Outlook uses user-triggered delta sync, not a
webhook or timer SLA. Vercel and Render must provision TLS before the DNS records are considered
complete because the existing apex publishes HSTS with `includeSubDomains`.

## Enabled capabilities

- Microsoft account allowlist and revocable database session.
- HttpOnly session cookie, OAuth state/nonce/PKCE and CSRF protection for mutations.
- Encrypted Outlook refresh token, manual inbox delta cursor and deduplicated communication import.
- Outlook draft preview, content-hash approval, recipient allowlist and idempotency record.
- MISA-style CSV/XLSX preview and idempotent invoice/case import.
- Tenant RLS plus composite `(tenant_id, id)` foreign keys on tenant-owned relationships.
- Synthetic seed that can recreate the portfolio state.

## Permanently disabled in this profile

`Settings` rejects startup if any of these are enabled: document upload, Temporal, MISA API or
Outlook webhook. It also rejects `OUTLOOK_SEND_ENABLED=true`, external delivery, a disabled global
kill switch, development authentication, HTTP origins, a local database or missing secrets.

## Deployment sequence

1. Run `ruff`, strict `mypy`, Python tests, frontend lint/typecheck/test/build and Docker builds.
2. Run `alembic upgrade head` against Neon and execute `tools/seed_demo.py`.
3. Deploy `render.yaml` as a Render Blueprint; enter every `sync: false` value in the dashboard.
4. Verify the Render URL `/live`, `/ready`, protected `/metrics`, OAuth login redirect and 401 data.
5. Deploy the root Vercel project using `vercel.json`, with:
   - `NEXT_PUBLIC_API_URL=https://api.deb2b.id.vn`
   - `NEXT_PUBLIC_DEV_AUTH_ENABLED=false`
6. Add the custom domains in each provider before changing DNS.
7. Add only provider-returned CNAME/TXT records for `app` and `api`; never change apex,
   nameservers or unrelated records.
8. Verify HTTPS, CSP/HSTS, CORS with credentials, Microsoft callback, session/logout/CSRF, MISA file
   import, Outlook sync and allowlisted draft creation.

## Recovery

The portfolio contains no authoritative customer data. Recovery is `alembic upgrade head` followed
by the idempotent synthetic seed. Neon Free time travel is helpful but is not represented as a
production backup SLA. Any real customer data, timer SLA, webhook guarantee or external delivery
requires a separate paid/pilot architecture and a new readiness gate.

## P1 closure for the portfolio scope

| Original finding | Portfolio closure |
|---|---|
| Browser auth missing | Microsoft code+PKCE, allowlist, DB session, logout/revoke and CSRF added |
| Temporal shell incomplete | Runtime flag is mandatory false; no portfolio route depends on it |
| OCR worker incomplete | Upload endpoint is fail-closed and UI does not advertise upload |
| Outlook webhook unsafe | Subscription validation and notifications return 404 while disabled |
| Backup/restore absent | Only reproducible synthetic state is allowed; migration+seed is recovery |
| Monitoring absent | Structured logs, protected metrics and health checks retained; no SLA claimed |
| Tenant ownership FKs weak | Composite tenant ownership constraints added and negative-tested |
| Billable Railway project absent | Replaced with explicit Vercel/Render/Neon free topology |
| Apex already serves WordPress | Apex preserved; only `app` and `api` are in scope |
