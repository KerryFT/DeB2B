# Deployment guide

For the zero-cost, synthetic, fail-closed portfolio release, use `PORTFOLIO_DEPLOYMENT.md` and
`render.yaml`/`vercel.json`. The guide below remains the gate for a full production/pilot release.

This guide is executable only after `RELEASE_CHECKLIST.md` has no open P0/P1 item. Current status is
NO-GO, so the Railway configuration has been prepared but not applied.

## Required decisions and access

- Select an existing Railway project or approve creation of a billable project and monthly budget.
- Select/configure an OIDC provider and dedicated production client. Do not paste secrets into chat.
- Select managed Temporal or explicitly accept self-hosted operational ownership.
- Grant DNS access limited to records under `deb2b.id.vn`; do not change nameservers.
- Provide sandbox credentials only for connectors being verified. Real send/write-back stays off.

## Production variables

Set secrets through Railway variables/sealed values. Values marked `preserve()` in
`.railway/railway.ts` must already exist before a plan/apply succeeds.

| Class | Variables |
|---|---|
| Public build config | `NEXT_PUBLIC_API_URL`; `NEXT_PUBLIC_DEV_AUTH_ENABLED=false` |
| Runtime | `APP_ENV=production`, base URLs, exact CORS/trusted hosts, Temporal target/namespace |
| Database/storage | referenced `DATABASE_URL`; S3 endpoint/bucket/access/secret/region; ClamAV host/port |
| Identity | OIDC issuer/audience/JWKS URI and provider-side client/session secrets |
| Operations | metrics bearer, OTEL/Sentry endpoints, upload limits |
| Safety | global kill `true`, external delivery `false`, connector dry-run `true` |
| AI | non-fake provider/model route and server-side provider key |

The production validator refuses localhost, HTTP identity endpoints, fake LLM routing, missing
storage/scanner/metrics config, dev auth or unsafe automation flags.

## Release sequence

1. From a clean reviewed commit, run `railway project link` and choose the approved project.
2. Run `railway config plan --verbose`; save the redacted plan in the release record. Do not apply
   if it creates unexpected resources, deletes anything, or exceeds the approved budget.
3. Configure preserved variables in the Railway UI/CLI secret path; rerun the plan.
4. Apply to a staging environment first. Railway IaC apply needs explicit confirmation; never use
   `--confirm-destructive` for this release.
5. Build immutable API/web/worker artifacts from the same commit. CI must pass all gates and scans.
6. Take/verify a pre-migration backup. Run `alembic upgrade head` as a pre-deploy task.
7. Deploy API with `/ready`, then private workers, then web. Keep all external delivery disabled.
8. Run the synthetic staging smoke matrix below. Perform a restore drill into a sibling database.
9. Promote the same reviewed commit/artifacts to production and rerun smoke verification.
10. Add custom domains only after service health is green.

## DNS and TLS

Before any change, record `Resolve-DnsName` output for apex, `www`, `api`, CAA and TXT. Railway
returns a routing record and a verification TXT record for every custom domain; both are required.

**Current snapshot (2026-08-24 22:09 ICT):** apex resolves to `103.56.163.10`,
`103.216.118.10`, `103.166.183.10` and `2001:df7:ce00:22::3:0`; it serves an existing WordPress
site, redirects HTTP to HTTPS, and sends HSTS with `includeSubDomains`. `www` and `api` did not
resolve. Do not replace the apex records without explicit confirmation about the existing site.

- Apex: use the DNS provider's CNAME flattening/ALIAS/ANAME to Railway's returned target.
- API: `CNAME api` to the exact Railway target.
- Verification: add exact TXT name/value Railway returns.
- `www`: configure a 308 edge/application redirect to `https://deb2b.id.vn`; do not serve two canonicals.
- TTL: 300 seconds for cutover, then 3600 after 24 hours stable.

Do not invent record values in advance and do not use a static Railway A record. Railway manages
Let's Encrypt certificates and renewal. Verify chain, SAN, expiry, HTTP→HTTPS, canonical redirect,
mixed content and response headers before increasing TTL. Reference:
https://docs.railway.com/networking/domains/working-with-domains

## Smoke matrix (synthetic tenant only)

| Step | Expected result |
|---|---|
| `/`, login/callback/logout | secure authenticated session; revocation works |
| `/live`, `/ready` | 200; response does not expose dependency details |
| two-tenant negative | foreign tenant cases/files/predictions/exports are 404/empty |
| import synthetic CSV/XLSX | preview/commit idempotent; invalid rows blocked |
| upload synthetic PDF/XLSX | quarantine→scan→object→evidence; bad MIME/malware blocked |
| create/review case | blockers/evidence/timeline correct |
| draft | fake/sandbox draft only; no send permission/call |
| reconciliation | partial/split/aggregate/fee/duplicate/reversal invariants hold |
| analytics | forecast/profile/benchmark render with as-of/uncertainty |
| operations | logs/metrics/trace/alert contain correlation IDs, no sensitive body |
| recovery | backup status healthy; restore sibling validates counts/hash |
| safety | global and tenant kill verified; MISA/Zalo/write-back disabled |

Any P0/P1 result triggers rollback/feature disable. Do not leave an uncertain release serving traffic.

## Rollback

Rollback the application image/commit first; additive migrations are kept forward-compatible for
one release. If the migration itself is unsafe, stop writers, preserve a backup, restore a sibling
database and point the previous application at the verified database. Never blindly downgrade a
live financial database. Revert DNS only to the snapshotted values if the prior target was verified.

## Connector status required in release record

Record each of Gmail, Outlook, MISA, Zalo, OpenAI, Gemini and Anthropic as `disabled`, `fake-tested`,
`sandbox-verified` or `live-verified`. For this audit all are disabled/fake-tested only.
