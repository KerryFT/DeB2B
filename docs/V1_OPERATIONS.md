# V1 local operations and sandbox smoke tests

## Offline demo

1. Copy `.env.example` to `.env`; keep `EXTERNAL_CONNECTORS_DRY_RUN=true`.
2. Start dependencies with `docker compose up -d postgres temporal minio`.
3. Run `.venv/Scripts/alembic upgrade head` on Windows (or `uv run alembic upgrade head`).
4. Run `.venv/Scripts/python -m tools.seed_demo`, start the API and run `pnpm dev`.
5. Open Forecast, LLM quality, Payment rules, Reconciliation and Settings. No credential is needed.

## Opt-in vendor smoke tests

- Outlook: create a dedicated test mailbox/folder, register the callback/subscription HTTPS URLs,
  grant delegated `offline_access Mail.ReadWrite`, then verify initial delta, renewal, a duplicate
  webhook, missed-event reconciliation and one unsent draft. Do not grant `Mail.Send`.
- MISA: obtain the exact sandbox/contracted read endpoint and auth from MISA, set
  `MISA_RECORDS_URL`, sync two pages, repeat the same checkpoint and verify zero duplicates. Keep
  write-back absent.
- Zalo: use an approved non-sensitive sandbox template and verified test recipient; preview first,
  obtain approval, then explicitly disable dry-run only in the isolated sandbox. Verify receipt and
  duplicate idempotency. Restore dry-run immediately.

Never store tokens in the database/UI as plaintext: environment values point to secret references.
Logs contain correlation IDs and redacted metadata only.

## Release validation

Run Python lint/type/tests, frontend lint/type/test/build, Alembic upgrade/downgrade/upgrade,
workflow replay/time-skipping tests, fake connector contracts, cross-tenant RLS tests and the demo
smoke test. A failed vendor live smoke test is reported separately; it never causes CI to call a
real external service.
