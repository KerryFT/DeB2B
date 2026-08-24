# MVP Dataset and Evaluation Plan

## 1. Policy and corpus sizes

Only seeded synthetic or explicitly licensed/legally anonymized sources are allowed. Default MVP uses **100% synthetic content** to avoid licensing/PII ambiguity. No real company/tax ID/email/bank/account data. Public data is opt-in through a reviewed manifest entry, not required for release.

Full corpus minimum: 100 invoices; 50 contracts/addenda; 100 PO/delivery/acceptance documents; 100 email threads; 50 dispute cases; 50 promise-to-pay cases; 50 bank transactions. Items can form linked cases but counts and split groups are manifest-validated.

CI smoke corpus: 10 invoices, 5 contracts, 10 PO/acceptance, 10 threads, 5 disputes, 5 promises, 10 bank transactions, including one of each five blockers and each security invariant. Commit source templates, gold JSON and small rendered assets (target <25 MB). Full generated corpus stays out of Git; commit manifest/checksums/report only (target 0.5–2 GB depending on raster DPI).

## 2. Layout and reproducibility

Planned implementation paths:

```text
tools/dataset/{generate,render,augment,validate,split,spotcheck}/
data/templates/                  Vietnamese-first Jinja/layout templates
data/fixtures/smoke/{raw,gold}/  committed CI set
data/generated/<version>/{raw,gold}/  gitignored full corpus
data/manifests/<version>.jsonl   provenance and checksum per artifact
evals/{schemas,metrics,runners,reports}/
```

Root seed (recommended `20260823`) derives per-case/per-artifact seeds; generators use pinned versions/fonts/container digests. A manifest record includes `artifact_id`, case graph IDs, type, language, split, source=`synthetic`, license=`project-generated`, template/generator/augmentation versions, seed, SHA-256, MIME/pages/size, linked gold checksum, creation time. Regeneration must be byte-stable where renderer permits; otherwise semantic gold stable and renderer digest explains variation.

## 3. Schemas and gold labels

- `case.json`: tenant/customer aliases, invoices, required-doc matrix, expected status, one-or-more blocker labels, next action, review-required flag.
- `document.json`: type; entities/fields (raw + normalized); page/sheet; evidence quote, char range, normalized polygon or cell range; signature/table quality; expected parser route; candidate links and match outcome.
- `email_thread.json`: ordered RFC-like messages, headers/contact roles, quoted/replied/forwarded segments, attachments, gold summary claims with evidence, dispute taxonomy, promise date/range/ambiguity, recipient policy.
- `bank.json`: transaction ID/date/value/currency/reference; expected candidate invoices; allocation graph for one-to-one, split and combined; `auto|review|reject`.
- `llm_case.json`: task, portable input schema, expected structured semantics, allowed/unsupported claims, injection marker, required refusal/review behavior.

Gold normalization: Vietnamese Unicode NFC; tax/invoice/PO identifiers preserve meaningful leading zeros; dates ISO with source timezone/ambiguity; money integer minor units; evidence coordinates `[0,1]` with page origin declared. Each correction increments dataset version, records reviewer/reason/diff and invalidates affected baseline report.

## 4. Generation matrix

70–80% Vietnamese, 20–30% bilingual Vietnamese–English. Synthetic identities use reserved domains (`example.com`), obviously fictional company names, checksum-invalid tax IDs or reserved marker prefix, non-routable phone/account placeholders.

Templates cover contract/addendum, PO, e-invoice-like PDF/XML fixture, delivery/acceptance, payment request, email chain and bank export. Case graph generation produces the five blockers plus clean and multi-blocker controls.

Augmentations are stratified and labeled: native text vs raster; 150/200/300 DPI; blur/noise/compression; ±15° rotation; perspective/skew; shadows/crops; multiple open-license fonts with Vietnamese glyphs; missing diacritics; multi-page/wide tables; stamp/signature present/missing; similar invoice numbers; amount/date/tax-ID/PO/contract mismatch; duplicates; reply/forward disorder; HTML/plain email; vague dates (“thứ Sáu tới”, “đầu tháng”); partial/batch/over/under-payment.

Negative/adversarial: unrelated document, empty/corrupt/password PDF, macro XLSX/archive/polyglot/oversize/page bomb, cross-tenant matching decoy, wrong recipient/near-lookalike domain, stale/replayed approval, duplicate Gmail notification, provider malformed JSON/refusal/timeout, and prompt injection in body/image/attachment instructing model to send, reveal secrets, change bank account or ignore policy. Expected result is ignore/untrusted, abstain/review, or reject—never external action.

## 5. Split and leakage prevention

Split by **case family/template parameter lineage**, never by page/message: build 60%, calibration 20%, held-out 20%. Template variants and customer/invoice aliases for held-out are inaccessible to prompt/rule tuning. Augmented derivatives inherit parent split. Full provider/model selection uses calibration; held-out runs only for release candidates. After held-out inspection, any tuning starts a new dataset version/test set.

No fine-tuning. “Build” is only rule/prompt development. CI smoke is not used for quality claims.

## 6. Metrics

- Document classification: accuracy, macro-F1, confusion matrix and abstention.
- Extraction: exact match and field F1 for tax ID/invoice/date/money; normalized and raw results; clean vs degraded strata.
- Payment terms: date/term acceptable match plus evidence precision/coverage/faithfulness.
- Matching: precision/recall/F1, top-k, auto-link precision, review rate, calibration/reliability and threshold sweep.
- Blocker: macro/micro-F1, multi-label exact match, per-blocker recall, abstention.
- Promise: date exact/acceptable, range/ambiguity detection and evidence.
- LLM: JSON/schema and semantic validity, unsupported-claim/hallucination rate, injection success=0, provider/model/prompt version, p50/p95 latency, input/output tokens and estimated cost/case.
- System: wrong recipient, duplicate external effect, unauthorized mutation/read, false PAID; all must be zero.

Report bootstrap confidence intervals where meaningful and publish sample count. Small synthetic metrics are targets/calibration evidence, not production guarantees.

## 7. Gates

Release gates: 100% critical fields evidence-or-review; gateway output accepted only schema-valid; wrong recipient=0; duplicate draft=0; unauthorized/cross-tenant mutation/read=0; LLM financial mutation=0; false PAID=0; injection-triggered effect=0.

Quality targets from brief: classification ≥98%; clean MST/invoice/money ≥99%; payment term with evidence ≥95%; auto-match precision ≥97%; blocker macro-F1 ≥90%; promise date ≥95%. If missed, do not lower safety gate: increase abstention/manual review, restrict parser/provider/task route, then document gap.

## 8. Harness and execution

Offline CI uses native parsers, deterministic fake LLM/Gmail, recorded provider-normalized fixtures and no internet/key. Local full eval can run OCR and optionally live providers only with explicit command/budget; it writes immutable raw result hashes and redacted report. Matrix key is `task × provider × model × prompt_version × dataset_version × pipeline_version`.

Planned commands: `make dataset-smoke-validate`, `make eval-smoke`, `make dataset-full`, `make eval-local`, `make eval-report`. A provider live run requires a cost estimate/limit and never becomes default CI.

## 9. QA and provenance review

Automated validation checks counts, schema, referential integrity, coordinate bounds, evidence substring/cell, allocation conservation, split leakage, checksum, PII patterns and reserved domains. Human spot-check: 100% smoke, ≥20% full corpus and 100% failures/ambiguous cases; dual review for recipient/PAID/injection gold. Review UI/export records reviewer pseudonymous ID, decision, reason and timestamp.

Any proposed public source must record canonical URL, author, exact license/version, permitted use, download checksum, transformation and PII scan/removal. Unknown/custom/no-redistribution license means reject. Font/model licenses and generator dependencies appear in SBOM/manifest. Accessed sources are revalidated before implementation download.

