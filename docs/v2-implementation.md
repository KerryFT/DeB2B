# Prompt cho Codex — Triển khai V2 AR Operations Agent

Sao chép toàn bộ prompt bên dưới và gửi cho Codex trong đúng repository đã hoàn thiện MVP và V1.

```text
Bạn là lead engineer chịu trách nhiệm nâng AR Operations Agent từ V1 đã hoạt động lên V2 an toàn, đo lường được và có thể vận hành thực tế. Hãy audit codebase, lập kế hoạch triển khai có thể theo dõi, rồi trực tiếp sửa code, migrations, workflows, UI, tests, datasets và tài liệu cho đến khi toàn bộ release gate V2 đạt yêu cầu.

# Kiểm tra repository trước khi thay đổi

1. Xác nhận thư mục hiện tại là repository chứa source code MVP và V1 đã hoàn thiện, không phải thư mục chỉ có tài liệu prompt.
2. Đọc toàn bộ `AGENTS.md` áp dụng, README, kiến trúc, ADR, schema, API docs, runbook, kế hoạch MVP/V1, eval plan và roadmap gốc. Nếu có, đọc `outputs/ar-operations-agent-implementation-plan.md`.
3. Kiểm tra git status và bảo toàn mọi thay đổi của người dùng. Không reset, restore hoặc ghi đè thay đổi không thuộc V2.
4. Audit trạng thái thực tế của bảy nền tảng V1 liên quan trực tiếp: workflow/outbox, email connectors, approval/policy engine, RBAC, customer rules, reconciliation/aging forecast, LLM telemetry và audit log.
5. Chạy baseline lint, type check, unit/integration/E2E tests, build và migration check phù hợp. Ghi rõ lỗi có trước V2.
6. Nếu không có code MVP/V1, V1 chưa đủ nền để mở rộng, hoặc đang ở sai repository, dừng và báo bằng chứng cùng phần prerequisite còn thiếu; không tự xây lại toàn bộ MVP/V1 dưới tên V2.

# Quyền tự chủ và cách làm việc

- Đây là yêu cầu triển khai. Sau audit, hãy tạo/cập nhật kế hoạch task có ID, dependency, acceptance criteria và trạng thái; sau đó thực thi liên tục, không chờ phê duyệt cho thay đổi local, migrations, tests, fixtures và tài liệu nằm trong phạm vi.
- Chỉ một bước ở trạng thái `in_progress`; cập nhật kế hoạch sau từng vertical slice.
- Tái sử dụng kiến trúc hiện có, tránh rewrite và tránh thêm data platform/framework lớn nếu PostgreSQL, worker và workflow engine hiện tại đáp ứng được.
- Chọn giả định có thể đảo ngược và ghi decision log. Chỉ hỏi khi thiếu thông tin thực sự chặn kiến trúc hoặc khi cần thực hiện external write/production rollout.
- Được phép nghiên cứu web; ưu tiên tài liệu chính thức/primary source cho thư viện, email delivery, privacy, model evaluation và các API hiện hành.
- Không cần credential thật để hoàn thành code và automated tests. Dùng fake adapters, synthetic data và offline evaluation. Live/sandbox smoke test là opt-in.
- Không tự bật automation trên production, không gửi email thật và không thay đổi dữ liệu thật. Có thể xây đầy đủ cơ chế auto-send, nhưng mặc định toàn hệ thống phải ở `disabled` hoặc `shadow` cho đến khi tenant admin bật có chủ đích.
- Không tuyên bố hoàn tất nếu chỉ dựng UI hoặc stub. Mỗi capability phải đi xuyên schema → service/workflow → API → UI cần thiết → audit/observability → tests → docs.

# Phạm vi V2 được phép triển khai

V2 gồm đúng bảy capability:

1. Tự gửi email follow-up rủi ro thấp sau khi hệ thống đã xây đủ trust và tenant chủ động bật.
2. Gợi ý chiến lược escalation.
3. Theo dõi và phân tích dispute root cause.
4. Dự báo probability-to-pay.
5. Cash-flow forecast.
6. Customer payment behavior profile.
7. Benchmark hiệu quả theo account manager.

Các capability dùng chung một nền dữ liệu point-in-time-correct, model/rule governance, audit và tenant isolation. Không tạo bảy pipeline dữ liệu độc lập.

# Invariant không được phá vỡ

- PostgreSQL/domain ledger là nguồn sự thật; prediction và LLM output không phải financial truth.
- Workflow/state machine sở hữu vòng đời PaymentCase.
- LLM không tự sửa invoice, payment, contact, bank account, rule hoặc state tài chính.
- External action có policy, idempotency, audit, revalidation và kill switch.
- Dispute, discount, legal action, thay đổi điều khoản và dữ liệu ngân hàng luôn cần người có quyền quyết định.
- Dự báo phải có `as_of`, horizon, model/rule version, input provenance và uncertainty.
- Feature/model training không được nhìn dữ liệu xảy ra sau thời điểm dự báo.
- Không dùng protected/sensitive attributes hoặc proxy không phù hợp để gây áp lực thu nợ hay đánh giá nhân sự.
- Tenant isolation/RBAC được cưỡng chế ở backend/database.
- OpenAI, Gemini và Anthropic tiếp tục qua provider abstraction. Không dùng LLM thay mô hình thống kê chỉ vì tiện.
- Prompt/email/document là untrusted input; không được điều khiển tool hoặc policy.

# Yêu cầu chi tiết và Definition of Done

## V2-01 — Auto-send email rủi ro thấp

Mục tiêu là tự động hóa reminder đơn giản đã được phê duyệt về chính sách, không phải thu hồi nợ tự trị.

Phải có:

- Automation policy theo tenant và tùy chọn theo customer: `disabled`, `shadow`, `canary`, `enabled`.
- Tenant admin phải chủ động bật; migration/default config luôn `disabled` hoặc `shadow`.
- Eligibility engine deterministic, versioned và explainable. LLM chỉ tạo nội dung trong template/schema được phép, không quyết định eligibility cuối.
- Phạm vi low-risk mặc định rất hẹp: email reminder lịch sự, không tranh chấp, không promise broken, không legal/escalation language, không thay đổi số tiền/điều khoản/bank detail, không recipient mới chưa xác minh, không attachment ngoài allowlist, không case có ambiguity hoặc manual-review flag.
- Cho phép cấu hình thêm threshold như value cap, days overdue, trusted customer/contact, minimum historical approvals, draft edit/reject rate, channel health và confidence; mọi threshold có default an toàn.
- Pre-approved template/version, locale, tone và biến allowlist. Render phải fail closed khi thiếu evidence hoặc field trọng yếu.
- Recipient verification, suppression list, opt-out/consent khi áp dụng, quiet hours, timezone, frequency cap, cooling period và duplicate prevention.
- Revalidate case version, outstanding amount, payment status, dispute, recipient, attachment, policy và permission ngay trước send.
- Transactional outbox + idempotency key; không giữ DB transaction qua network call.
- Shadow mode tạo quyết định/draft giả và so với human action nhưng không gửi.
- Canary theo tenant/customer percentage hoặc allowlist; daily send cap; circuit breaker theo bounce/error/complaint/duplicate/anomaly.
- Global kill switch và tenant kill switch có hiệu lực ngay, observable và được test.
- Delivery/bounce/complaint/reply tracking, retry classification, dead-letter/replay và audit đầy đủ.
- UI cho policy, preview, shadow metrics, canary progress, exclusions, kill switch và audit trail.
- Rollback từ `enabled` về `shadow/disabled` không làm mất action history.

Release gate riêng:

- Default configuration không thể gửi thật.
- Shadow evaluation trên synthetic/seed cases không có eligible false-positive ở tập safety-critical.
- Wrong recipient, duplicate send, send after paid/disputed, unauthorized enable và bypass kill switch đều bằng 0 trong tests.
- Live send chỉ được ghi là chưa xác minh nếu không có credential/sandbox; không tự gửi để “kiểm thử”.

## V2-02 — Gợi ý chiến lược escalation

Đây là recommendation cho con người, không phải agent tự escalation.

Phải có:

- Taxonomy chiến lược: internal follow-up, account-owner involvement, AP re-submission, document correction, manager review, customer meeting, temporary pause, commercial review và legal-review referral. Legal referral chỉ là đề xuất chuyển người có thẩm quyền, không tạo legal notice.
- Inputs có provenance: aging, amount, blocker, dispute state, communication history, promise behavior, customer rules, contact/owner và payment behavior profile.
- Deterministic constraints loại bỏ action không hợp lệ; ranking/rationale có thể dùng rule, model hoặc LLM qua schema chuẩn.
- Mỗi recommendation có rank, reason codes, evidence, expected outcome, risk, prerequisite, next review date, source/model/rule version và confidence phù hợp.
- Không đề xuất đe dọa, quấy rối, public shaming, gọi người không liên quan, discount, thay đổi điều khoản hoặc nội dung pháp lý tự động.
- Human accept/edit/reject/ignore feedback được lưu để đánh giá, không biến thành training data tự động chưa kiểm soát.
- UI so sánh phương án, evidence và lịch sử quyết định; action bên ngoài vẫn đi qua approval/policy hiện có.
- Offline eval và policy-adversarial suite cho case tranh chấp, customer khó khăn, dữ liệu thiếu và prompt injection.

DoD: mọi gợi ý có bằng chứng và reason code; action bị cấm không xuất hiện trong test; hệ thống vẫn hữu ích khi LLM unavailable bằng fallback rule/manual workflow.

## V2-03 — Dispute root-cause analytics

Phân biệt “root-cause category được suy luận từ bằng chứng” với quan hệ nhân quả đã được chứng minh.

Phải có:

- Versioned taxonomy tối thiểu: pricing/amount mismatch, PO mismatch, missing/invalid document, delivery/quality issue, acceptance/signature, tax/invoice compliance, duplicate invoice, contractual term ambiguity, customer internal approval, payment already made/unmatched, seller operational error, customer cash-flow issue và unknown.
- Hỗ trợ primary cause, contributing causes, confidence, evidence spans, first-detected time, owner, resolution, resolution time và reopen.
- Timeline từ communication/document/event có provenance; không để LLM tạo sự kiện không tồn tại.
- Human correction/merge/split category, taxonomy version migration và audit.
- Root-cause aggregation theo customer, team, product/service nếu dữ liệu hợp lệ, thời gian và value-at-risk.
- Metrics: count/value, time-to-detect, time-to-resolve, reopen rate, recurring pattern và preventable/unknown rate với định nghĩa rõ.
- Drill-down từ chart tới case evidence, có RBAC và tenant isolation.
- Dataset/eval gồm multi-label, unknown, ambiguous và disagreement; đo macro-F1, evidence coverage và human correction rate.

DoD: một dispute có thể được theo dõi end-to-end từ detection đến resolution; aggregate khớp dữ liệu case; không trình bày inference như sự thật tuyệt đối.

## V2-04 — Probability-to-pay

Mục tiêu là ước lượng xác suất thanh toán trong horizon xác định, không tạo một điểm số mơ hồ.

Phải có:

- Định nghĩa label/horizon rõ, tối thiểu xác suất được thanh toán trong 7, 14 và 30 ngày hoặc horizon phù hợp dữ liệu thực tế.
- Snapshot point-in-time với `as_of`; xử lý censoring, partial payment, multiple invoices/cases và reopened case.
- Baseline đơn giản trước: historical segment rate/logistic hoặc survival baseline. Chỉ thêm model phức tạp nếu backtest chứng minh cải thiện.
- Feature pipeline versioned, point-in-time-correct; không leakage. Không dùng nội dung sau `as_of`, protected attributes hoặc proxy không cần thiết.
- Probability calibration; metrics tối thiểu Brier score/log loss, ROC/PR phù hợp class balance, calibration error/reliability curve, lift theo decile và stability theo thời gian/segment.
- Time-based train/validation/test split; champion/challenger và reproducible seed.
- Prediction có model version, feature snapshot, confidence/data-quality flags và reason codes/explanation có giới hạn.
- Threshold là business config, không nhúng vào model; probability không tự kích hoạt aggressive action.
- Fallback khi model unavailable/stale/insufficient data; model registry, rollback và drift monitoring.
- UI hiển thị horizon và uncertainty, tránh nhãn mang tính phán xét.

DoD: backtest tái lập, không leakage, probability được calibration; model nâng cao phải vượt baseline theo tiêu chí đã ghi hoặc baseline được giữ làm production candidate.

## V2-05 — Cash-flow forecast

Mở rộng aging forecast V1 thành forecast thu tiền xác suất, không thay thế accounting cash position.

Phải có:

- Forecast expected collections theo tuần/tháng cho horizon cấu hình, từ invoice outstanding, due date, promise-to-pay, partial payments và probability-to-pay.
- Không double-count invoice, payment allocation hoặc promise. Snapshot/ledger reconciliation rõ ràng.
- P10/P50/P90 hoặc interval/scenario tương đương; base/upside/downside assumptions có version.
- Tách contractual schedule, deterministic baseline và probabilistic forecast.
- Aggregation theo tenant/customer/account owner/currency; FX chỉ khi tỷ giá có source/as-of, nếu không hiển thị từng currency.
- Backtesting rolling-origin theo thời gian; metrics như WAPE/MAE/bias và interval coverage theo horizon.
- Điều chỉnh cho seasonality chỉ khi đủ dữ liệu; cảnh báo sparse/stale/data-quality issue.
- Forecast run có status, as-of, cutoff, model/version, input snapshot và reproducibility.
- Scenario UI cho thay đổi giả định có kiểm soát; scenario không ghi ngược invoice hay payment rule.
- Export/report có timestamp, currency và disclaimer rằng đây là forecast.

DoD: cùng một snapshot tạo kết quả tái lập; tổng forecast reconcile được về invoice-level components; baseline và probabilistic forecast được so sánh bằng backtest.

## V2-06 — Customer payment behavior profile

Profile phải mô tả hành vi thanh toán có bằng chứng, không tạo nhãn xúc phạm hoặc credit score ngầm.

Phải có:

- Metrics theo rolling window và lifetime: invoice count/value, on-time rate, average/median/p90 delay, payment variability, partial-payment frequency, broken-promise rate, dispute frequency/root cause, document completeness friction, response latency và preferred verified channel khi đủ dữ liệu.
- `as_of`, window, sample size, data coverage/quality và provenance cho mọi snapshot.
- Segmentation mô tả như consistent/variable/insufficient-data chỉ khi có định nghĩa minh bạch; tránh “bad customer”, “dishonest” hoặc causal claim không có bằng chứng.
- Không dùng profile để tự từ chối dịch vụ, tự thay điều khoản hoặc gây áp lực khác biệt.
- Customer merge/split/external-ID correction phải trigger recompute an toàn.
- Incremental aggregation có backfill/rebuild và reconciliation với raw events.
- UI timeline/trend và explanation; RBAC và export audit.
- Tests cho new customer, sparse data, merged customer, outlier, dispute, partial payment, currency và late-arriving event.

DoD: profile truy ngược được về source events, cập nhật đúng khi dữ liệu đến muộn và hiển thị rõ khi không đủ mẫu.

## V2-07 — Benchmark hiệu quả account manager

Đây là operational coaching/portfolio insight, không phải hệ thống tự động quyết định nhân sự.

Phải có:

- Metric definitions rõ: response/follow-up timeliness, document completion time, dispute time-to-resolution, promise follow-up, approval turnaround, preventable blocker rate và risk-adjusted collection outcome.
- Không xếp hạng chỉ bằng tổng tiền thu hoặc DSO thô vì portfolio/customer mix khác nhau.
- Chuẩn hóa theo assigned portfolio, invoice value/age, customer payment profile, blocker mix, inherited cases, leave/coverage và observation window khi dữ liệu cho phép.
- Hiển thị raw metric cạnh adjusted metric, sample size, uncertainty/interval và data-quality warning.
- Minimum cohort/sample threshold; suppression khi nhóm quá nhỏ để tránh suy ngược dữ liệu cá nhân.
- Cho phép team benchmark, cohort/peer group hợp lý và trend của chính người dùng; tránh leaderboard gây hiểu sai làm mặc định.
- Attribution rules cho reassignment và multi-owner case; không double credit/blame.
- Drill-down tới case chỉ khi có quyền; audit export và quyền xem riêng.
- Không tự đưa ra quyết định thưởng/phạt, tuyển dụng, sa thải hoặc performance rating chính thức.
- Fairness/sensitivity review: metric có bị chi phối bởi portfolio difficulty, value outlier, new joiner hoặc data missing hay không.

DoD: benchmark tái lập, attribution rõ, adjusted metric không che raw metric; test chứng minh không cross-tenant leakage và không hiển thị cohort dưới minimum threshold.

# Nền tảng dữ liệu và model governance dùng chung

Triển khai tối giản phù hợp codebase, nhưng phải có các khái niệm sau:

- Versioned event/feature definitions.
- Point-in-time feature snapshot keyed theo tenant/entity/as-of.
- Prediction/forecast run và model/rule registry.
- Dataset manifest, code version, seed, split/cutoff và metric artifact.
- Champion/challenger, shadow evaluation, rollback và stale-model behavior.
- Scheduled recompute/backfill idempotent; late-arriving data policy.
- Drift/data-quality monitoring và alert threshold.
- Audit từ UI aggregate → prediction/profile → features → canonical source events.
- Retention/deletion/export phải lan tới derived data, dataset và cached features theo policy.
- Không sao chép raw email/document sang feature store nếu chỉ cần structured fields.

Không bắt buộc dựng warehouse/feature-store service mới. Ưu tiên PostgreSQL tables/materialized views/jobs hiện có nếu đáp ứng đúng correctness, scale MVP/V2 và reproducibility.

# LLM và mô hình dự báo

- Probability-to-pay và cash-flow forecast ưu tiên deterministic/statistical/ML model có thể backtest; không dùng LLM để tạo số xác suất hoặc số tiền forecast.
- LLM phù hợp cho dispute classification, evidence-backed explanation, recommendation drafting và text generation, nhưng output phải có schema validation và policy filter.
- Giữ adapter OpenAI/Gemini/Anthropic, mock provider và cross-provider eval.
- Prompt/model version, usage, latency, cost và quality tiếp tục vào dashboard V1.
- Không fine-tune trong phạm vi này. Nếu model off-the-shelf không đạt, ghi dữ liệu/eval gap thay vì tự mở rộng sang fine-tuning.

# Dữ liệu synthetic và eval cần mở rộng

Mở rộng generator V1 bằng seed/version/manifest; không dùng PII hoặc dữ liệu khách hàng thật. Tối thiểu tạo:

- Case đủ/không đủ điều kiện auto-send, paid/disputed ngay trước send, recipient thay đổi, duplicate timer, suppression, bounce và kill-switch race.
- Chuỗi escalation có outcome, recommendation hợp lệ/bị cấm và dữ liệu thiếu.
- Dispute multi-label có evidence, root cause unknown, correction, reopen và taxonomy migration.
- Lịch sử invoice/payment theo thời gian có censoring, partial payment, seasonality, behavior drift và late-arriving events.
- Customer mới/sparse, stable, variable, dispute-heavy và promise-broken nhưng không gán nhãn đạo đức.
- Account managers có portfolio mix khác nhau để kiểm tra raw vs adjusted benchmark, reassignment và cohort suppression.
- Ít nhất hai tenant để kiểm tra isolation ở raw, feature, prediction, aggregate và export.

CI dùng dataset nhỏ/offline; full backtest dùng dataset đầy đủ cục bộ. Không gọi LLM trả phí hoặc external API trong CI mặc định.

# Thứ tự triển khai khuyến nghị

Điều chỉnh khi codebase cho thấy dependency khác và ghi lý do:

1. Audit V1, baseline, threat/model-risk review và kế hoạch migrations.
2. Shared point-in-time feature/snapshot/model-governance foundation.
3. Dispute root-cause vertical slice.
4. Customer payment behavior profile.
5. Probability-to-pay baseline → backtest → calibrated candidate.
6. Cash-flow forecast và scenario/backtest UI.
7. Escalation recommendation engine với policy guardrails.
8. Account-manager benchmark và privacy/fairness controls.
9. Auto-send shadow mode → safety eval → canary infrastructure; production default vẫn disabled/shadow.
10. Cross-feature E2E, resilience, security, migration/rollback, docs và release review.

Không đợi đến cuối mới làm UI/tests. Mỗi vertical slice phải demo được bằng synthetic seed data.

# Migrations, security và operations

- Mọi migration có forward/backfill/roll-forward note; tránh lock dài và nêu compatibility với workflow/event đang chạy.
- Prediction/derived tables luôn có `tenant_id`; RLS/policy tests bao phủ cả aggregates và exports.
- Jobs/workflows idempotent, có checkpoint, retry classification, dead-letter/replay và concurrency control.
- Không log raw email, contract hoặc sensitive features. Secrets không commit; `.env.example` chỉ chứa placeholder.
- Threat model tối thiểu: unauthorized automation enable, kill-switch bypass, stale pre-send state, recipient manipulation, prompt injection, mass-send amplification, IDOR, cross-tenant aggregate leakage, model poisoning/data leakage và benchmark privacy.
- Observability: automation decisions/sends/blocks, model/version, calibration/drift, forecast errors, recommendation acceptance, dispute correction, job lag và data-quality failure.
- Runbook: disable automation, rollback model, rebuild feature snapshot, replay job, correct taxonomy/profile, investigate duplicate/mis-send và data deletion.

# Validation bắt buộc

Chạy validation liên quan sau mỗi slice và toàn bộ suite trước khi hoàn tất:

- Formatter/lint/type checks.
- Backend/frontend unit tests và production build.
- Migration/backfill/rebuild tests.
- Workflow replay/versioning và outbox/idempotency tests.
- API/contract/integration tests với fake services.
- RBAC/RLS/cross-tenant negative tests.
- Auto-send safety, race, canary, cap, circuit-breaker và kill-switch tests.
- Root-cause classification/evidence eval.
- Point-in-time leakage tests.
- Probability calibration/backtest/regression.
- Cash-flow reconciliation/backtest/interval coverage.
- Profile aggregation/rebuild/late-data tests.
- Benchmark attribution, adjustment, minimum-cohort và fairness sensitivity tests.
- End-to-end demo từ event → profile/prediction → recommendation/forecast → shadow auto-send decision → audit/dashboard.

Không xóa, skip hoặc nới test chỉ để đạt xanh. Nếu không thể chạy live test do thiếu credential, phải chạy fake/sandbox equivalent, cung cấp command opt-in và ghi rõ phần chưa được live-verified.

# Release gate V2

Chỉ tuyên bố V2 hoàn tất khi:

- Bảy capability đều có implementation end-to-end, migrations, tests, UI/API phù hợp, observability và docs.
- MVP/V1 regression suite vẫn xanh.
- Auto-send mặc định không gửi thật; shadow/canary/kill switch/cap/revalidation hoạt động và safety-critical tests bằng 0 lỗi.
- Không có duplicate/wrong-recipient/send-after-paid/send-during-dispute trong automated tests.
- Probability-to-pay point-in-time-correct và calibrated; model nâng cao không tệ hơn baseline theo release criteria.
- Cash-flow forecast reconcile về invoice-level components và có backtest/uncertainty.
- Root-cause/recommendation có evidence, policy filters và human correction.
- Customer profile không tạo nhãn đạo đức hoặc quyết định tín dụng tự động.
- Account-manager benchmark điều chỉnh portfolio mix, hiển thị uncertainty và không tự quyết định nhân sự.
- Tenant isolation/RBAC vượt negative tests trên raw và derived data.
- Local demo chạy hoàn toàn bằng synthetic seed/fake providers, không cần credential thật.
- Có runbook rollback model và tắt automation tức thì.
- Không còn test/build/migration failure chưa giải thích.

# Ngoài phạm vi V2 này

Không triển khai nếu không có yêu cầu riêng:

- Voice AI hoặc tự gọi điện.
- Tự thương lượng với khách hàng.
- Tự đề nghị/áp dụng discount hoặc giảm nợ.
- Tự gửi legal notice, tư vấn pháp lý hoặc chuyển pháp lý tự động.
- Tự thay đổi payment terms, bank account, invoice hoặc accounting entries.
- Fine-tuning.
- Multi-agent business architecture.
- Complex direct banking APIs hoặc bank credential scraping.
- Xây CRM, ERP hoặc accounting platform riêng.
- Credit approval/denial tự động.
- Automated HR performance decision từ account-manager benchmark.

# Báo cáo cuối

Trả lời ngắn gọn nhưng có bằng chứng:

1. Bảng bảy capability, trạng thái và đường dẫn implementation chính.
2. Kiến trúc/migrations/model governance quan trọng đã thêm.
3. Test, build, backtest và eval đã chạy, command cùng kết quả.
4. Baseline/champion metrics cho probability-to-pay và cash-flow forecast.
5. Trạng thái auto-send: disabled/shadow/canary, các safety gate và xác nhận không gửi production ngoài ý muốn.
6. Phần nào dùng fake, sandbox hoặc live integration.
7. Rủi ro/giới hạn còn lại và hướng dẫn chạy local demo/rollback/kill switch.

Hãy bắt đầu bằng audit repository và baseline V1, tạo kế hoạch có thể theo dõi, sau đó triển khai V2 end-to-end trong phạm vi trên.
```

## Lưu ý sử dụng

Prompt này cố ý không coi toàn bộ các mục từng được ghi “không làm trước V2” là phạm vi V2. Voice AI, tự thương lượng, discount, legal notice, multi-agent, fine-tuning và banking API phức tạp vẫn bị loại trừ; mỗi nhóm cần một quyết định sản phẩm và prompt riêng.
