# V1 external integration reference

Research verified on 2026-08-24. Automated tests use fakes; no default path sends or writes data.

## Outlook / Microsoft Graph

- Delegated `offline_access` plus `Mail.ReadWrite` supports long-lived sync and draft creation;
  `Mail.Send` is intentionally not requested.
- Message delta is per folder. The connector persists opaque `@odata.nextLink`/`@odata.deltaLink`
  values and periodically reconciles even when webhooks are missed.
- Subscription endpoints echo the URL-decoded validation token as `text/plain`, verify
  `clientState`, deduplicate notification IDs and renew before expiry. Lifecycle `missed`,
  `subscriptionRemoved`, and `reauthorizationRequired` events trigger reconciliation/recovery.
- Sources: Microsoft Graph [message delta](https://learn.microsoft.com/en-us/graph/delta-query-messages),
  [webhook delivery/validation](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks),
  [permissions](https://learn.microsoft.com/en-us/graph/permissions-reference), and
  [delegated OAuth](https://learn.microsoft.com/en-us/graph/auth-v2-user).

## MISA meInvoice

MISA products and customer entitlements expose different contracted API surfaces. V1 therefore
requires an HTTPS record URL supplied from the tenant's approved MISA documentation and keeps the
adapter read-only. It never invents a write-back endpoint. The normalized page contract requires
kind, stable external ID, version, update timestamp, records, continuation cursor and checkpoint.

Official starting points: MISA meInvoice Open API for
[input invoices](https://www.misa.vn/154997/tai-lieu-open-api-tich-hop-hoa-don-dien-tu-misa-meinvoice-dau-vao/)
and [output invoices](https://www.misa.vn/154989/tai-lieu-open-api-tich-hop-hoa-don-dien-tu-misa-meinvoice-dau-ra/).
The exact auth/endpoint contract must be attached to each tenant configuration before enablement.

## Zalo OA / ZBS template messages

V1 treats Zalo only as an approved notification channel. A published template version, exact
allowlisted variables, verified/consented non-suppressed recipient, quiet-hours check and approval
are required. Debt-sensitive content cannot target groups. Default mode is dry-run.

Official reference: [Zalo Developers documentation](https://developers.zalo.me/docs). Template
approval/eligibility and production send URL must be verified in the tenant's Zalo console before
enabling external delivery; the repository does not claim an unverified production endpoint.
