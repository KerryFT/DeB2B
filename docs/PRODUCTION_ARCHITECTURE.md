# Production architecture and ADR

## ADR-PR-001: Railway pilot topology, deferred apply

**Decision:** prepare Railway Infrastructure as Code for Singapore services, but do not apply it
until the release gate is clear and the user selects an existing project or approves a billable
project. Railway matches the current containerized monolith, supports private service networking,
managed TLS/custom domains, PostgreSQL, buckets and rollback without introducing Kubernetes.

The intended topology is:

```text
Internet
  -> deb2b.id.vn (canonical) -> Next.js web
  -> api.deb2b.id.vn         -> FastAPI
                                   -> private PostgreSQL
                                   -> private ClamAV
                                   -> private S3-compatible bucket
                                   -> Temporal endpoint -> workflow worker
                                   -> OIDC JWKS / approved LLM providers
```

`www.deb2b.id.vn` should redirect 308 to the apex. The API is split because the current client
fetches it directly; CORS is an exact single-origin allowlist. A future same-origin BFF would reduce
CORS and session complexity but is not introduced during this readiness pass.

The apex currently serves WordPress. Therefore this topology is an intended target, not authority
to cut over. If WordPress must remain, the safer revised topology is `app.deb2b.id.vn` for web and
`api.deb2b.id.vn` for API; update base URLs/CORS/OIDC callbacks before building the artifact.

## Resources and placement

| Resource | Proposed placement | Exposure | Initial scale |
|---|---|---|---|
| `web` | Railway `asia-southeast1-eqsg3a` | public apex | 1 replica |
| `api` | Railway Singapore | public API subdomain | 1 replica, health `/ready` |
| `workflow-worker` | Railway Singapore | private only | 1 replica, deployment blocked pending Temporal |
| `postgres` | Railway PostgreSQL | private app access | single node + backups/PITR |
| `documents` | Railway bucket region `sin` | private credentials | SSE objects, tenant prefixes |
| `clamav` | Railway Singapore | private only | 1 replica |
| Temporal | managed endpoint recommended | private/authenticated | namespace/task queue per environment |
| OIDC | external managed provider | HTTPS | authorization code + PKCE/session TBD |

The IaC source is `.railway/railway.ts`. Secret-shaped values use `preserve()` or generated sealed
values; they are never committed. Custom domains are added only after the service exists because
Railway IaC currently treats domains as import-only.

## Data and safety boundaries

- PostgreSQL is authoritative for money, case state, audit/outbox and derived provenance.
- Every tenant request starts a transaction as `ar_app`, sets `app.tenant_id`, and relies on forced RLS.
- Object keys are tenant-prefixed and content-addressed; bucket access is server-side only.
- Email/documents are untrusted input. LLM output cannot execute tools or change financial state.
- Temporal is a durability mechanism, not the financial source of truth.
- External delivery, MISA write-back and Zalo real send remain disabled. Global automation kill is on.

## Availability and recovery targets

- Pilot SLO: 99.5% monthly web/API availability.
- Wrong recipient, duplicate send and cross-tenant access: zero tolerance.
- Accepted webhook loss: zero; do not enable a webhook before durable inbox/backfill exists.
- Target RPO: 24 hours maximum initially; PITR target under 5 minutes after verification.
- Target RTO: 4 hours; actual values must be replaced with restore-drill measurements.

## Capacity and cost model

The existing model assumes 5,000 cases/month, about 167/day and 42 in the peak hour. It estimates
one 30-second worker at that throughput, but production should keep one active worker plus bounded
backlog and manual review. OCR remains separately capacity-limited.

At current Railway list rates referenced in its 2026 docs ($20/vCPU-month and $10/GB RAM-month),
an always-on small API/web/worker/Postgres plus a 2 GB ClamAV process is roughly **$80–130/month**
before subscription offsets, storage, egress, managed Temporal, OIDC, OCR bursts and LLM/OCR usage.
An always-on 2 vCPU/4 GB OCR worker could add about **$80/month**, so on-demand bounded jobs are
preferred. Set a $150 warning and $250 hard review threshold; these are estimates, not a purchase
authorization. Railway pricing: https://docs.railway.com/pricing

## Rejected alternatives

- Kubernetes: unjustified operational burden for 1–3 pilot tenants.
- Self-hosting all services on one VM: weak isolation/recovery and higher SRE burden.
- Deploying only the static web demo: would look live while authenticated functions are unusable.
- Self-hosted Temporal in the application PostgreSQL: possible, but increases failure coupling and
  schema/backup responsibility; decide only if managed Temporal cost is rejected.
