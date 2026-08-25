# AI Agent runbook

## What is live AI in this application?

The AI Agent is an evidence-grounded assistant for accounts-receivable operations. It does not
replace workflow rules and does not send messages autonomously. Its runtime path is:

1. The operator selects a payment case in `/agent`.
2. The API loads the case, invoice, customer, active blockers and evidence spans from the tenant
   database.
3. Gemini returns schema-constrained analysis or a follow-up draft.
4. The API rejects unknown evidence references and records model, prompt version, latency, token
   usage and fallback state.
5. Drafts become immutable, expiring approval requests. A human must review them before an Outlook
   draft can be created. Email sending remains disabled in the portfolio profile.

The system treats uploaded text as untrusted data, requires evidence IDs in model output, restricts
portfolio recipients to `ALLOWED_PORTFOLIO_EMAILS`, and fails closed when Gemini is unavailable.

## Required deployment configuration

Configure these values in the Render service environment. `GEMINI_API_KEY` is a secret and must
never be committed.

```text
LLM_DEFAULT_PROVIDER=gemini
GEMINI_API_KEY=<Render secret>
GEMINI_MODEL_FAST=gemini-3.5-flash-lite
GEMINI_MODEL_REASONING=gemini-3.7-flash
LLM_TIMEOUT_SECONDS=20
```

Case analysis tries the reasoning model first and falls back to the fast model on a timeout or
provider error. Draft generation uses the fast model for responsive, structured output.

## Operator acceptance flows

### Flow 1 — Analyze a case

1. Sign in and open **AI Agent**.
2. Confirm the status says **Gemini đang hoạt động** and both configured model names are visible.
3. Select a case and choose **Phân tích hồ sơ**.
4. Verify the response shows risk, summary, next action, confidence and evidence IDs.
5. Open the related case and verify the facts match the invoice and blocker data.

Expected: analysis is advisory, no case status or financial value changes, and unsupported evidence
is never displayed.

### Flow 2 — Generate and approve a follow-up draft

1. Complete Flow 1, enter an allowlisted recipient and a clear objective.
2. Choose **Tạo draft cần duyệt**, then open **Approval inbox**.
3. Review the recipient, subject and body; edit if required.
4. Approve the exact content once.

Expected: the item moves from pending to approved and its content hash is preserved. The portfolio
does not send email; any Outlook integration creates a draft only.

### Flow 3 — Reject unsafe or inaccurate output

1. Generate a draft, open **Approval inbox**, and select **Từ chối**.
2. Enter a reason and confirm rejection.
3. Refresh the inbox and case page.

Expected: the approval is rejected, the action cannot be executed, and the case remains unchanged.

### Flow 4 — Approval operations

1. Create two or more pending drafts for allowlisted recipients.
2. Filter by pending status, select multiple rows and use bulk approval.
3. Open one item, alter its content, then attempt to approve the stale version.

Expected: valid selections update with visible feedback; stale or expired content is refused and
must be regenerated/reviewed.

### Flow 5 — End-to-end portfolio data flow

1. Import a synthetic MISA CSV/XLSX file and confirm its preview.
2. Run the import again and verify idempotency (no duplicate invoice/case).
3. Open **Cases**, inspect the new case, analyze it in **AI Agent**, generate a draft, approve or
   reject it, then inspect **Analytics** and AI usage telemetry.

Expected: one traceable workflow from source data through evidence, AI assistance and human
decision; no external delivery occurs.

## Failure checks

- Remove/disable the Render Gemini secret in a non-production test environment: startup/status must
  show unavailable rather than returning fabricated AI output.
- Use a recipient outside `ALLOWED_PORTFOLIO_EMAILS`: draft creation must return 403.
- Cause a reasoning timeout: analysis may take up to the configured timeout, then reports the fast
  model and `fallback_used=true` without losing the request.
