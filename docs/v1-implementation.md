# Prompt cho Codex — Triển khai V1 AR Operations Agent

Sao chép toàn bộ prompt bên dưới và gửi cho Codex trong đúng thư mục repository đã hoàn thiện MVP.

```text
Bạn là lead engineer chịu trách nhiệm nâng AR Operations Agent từ MVP đã hoạt động lên V1 production-ready trong phạm vi đã định nghĩa. Hãy audit codebase hiện tại, lập kế hoạch triển khai có thể theo dõi, sau đó trực tiếp sửa code, migration, test và tài liệu cho đến khi V1 hoàn tất.

# Nguồn sự thật và kiểm tra ban đầu

Trước khi thay đổi code:

1. Xác nhận thư mục hiện tại đúng là repository chứa MVP đã hoàn thiện. Đọc toàn bộ `AGENTS.md` áp dụng, README, tài liệu kiến trúc, ADR, kế hoạch MVP, task/eval plan và các file cấu hình liên quan.
2. Đọc bản product plan gốc nếu có tại `outputs/ar-operations-agent-implementation-plan.md`, đặc biệt phần kiến trúc, bảo mật, LLM đa provider và roadmap V1.
3. Kiểm tra cấu trúc repo, git status, migrations, schema, API, UI, workflow, connectors, test suite, CI và các thay đổi chưa commit. Không ghi đè hoặc hoàn tác thay đổi của người dùng.
4. Chạy baseline validation phù hợp để biết MVP đang xanh hay có lỗi sẵn. Ghi rõ lỗi có trước khi triển khai V1.
5. Nếu repository thực tế không chứa source code MVP, hoặc đây là sai thư mục, dừng và báo chính xác bằng chứng; không tự xây lại MVP từ đầu.
6. Tìm kiếm và đọc tài liệu chính thức hiện hành trước khi tích hợp MISA, Microsoft Graph/Outlook và Zalo OA. Kiểm chứng SDK, OAuth scopes, webhook/subscription lifecycle, rate limit, sandbox, chính sách template và khả năng API thực tế. Không suy đoán endpoint hoặc tạo integration giả mang tên production.

# Cách làm việc

- Đây là yêu cầu triển khai, không chỉ lập kế hoạch. Sau audit, hãy tạo/cập nhật kế hoạch task có ID, dependency và acceptance criteria, rồi triển khai liên tục mà không chờ phê duyệt cho các thay đổi local, migration, test hoặc tài liệu nằm trong phạm vi V1.
- Dùng công cụ lập kế hoạch và cập nhật trạng thái khi hoàn thành từng nhóm việc. Giữ tối đa một bước `in_progress`.
- Ưu tiên mở rộng kiến trúc hiện có. Không rewrite MVP trừ khi có lỗi kiến trúc đã chứng minh và migration an toàn.
- Triển khai theo vertical slice có thể demo, không xây chín module cô lập rồi mới tích hợp ở cuối.
- Với ambiguity có thể đảo ngược, chọn giả định hợp lý, ghi vào decision log và tiếp tục. Chỉ hỏi khi thiếu thông tin làm thay đổi lớn kiến trúc hoặc cần quyền thực hiện hành động ngoài hệ thống.
- Không yêu cầu credential để hoàn thành code và test. Cung cấp adapter, fake server/provider, fixtures và contract tests để toàn bộ V1 chạy offline. Credential thật chỉ dùng cho smoke test opt-in.
- Được phép nghiên cứu web. Với API hoặc thư viện thay đổi theo thời gian, ưu tiên tài liệu chính thức và ghi link/ngày truy cập trong tài liệu integration.
- Mọi integration bên ngoài mặc định `dry-run` hoặc sandbox. Không gửi email/Zalo thật, không ghi dữ liệu MISA thật và không thực hiện bulk action trên production nếu chưa có phê duyệt rõ ràng.
- Không làm tính năng V2 hoặc mở rộng sản phẩm ngoài danh sách V1.

# Mục tiêu V1 phải hoàn thiện

V1 gồm đúng chín capability:

1. MISA API.
2. Outlook.
3. Zalo OA notification.
4. Bank reconciliation nâng cao.
5. Customer-specific payment rules.
6. Bulk approval.
7. Aging forecast.
8. Role-based access chi tiết.
9. Dashboard chi phí/chất lượng theo LLM provider.

# Invariant từ MVP phải được giữ

- PostgreSQL là nguồn sự thật nghiệp vụ.
- Workflow/state machine sở hữu vòng đời PaymentCase; LLM không tự ý đổi state.
- Tiền, ngày, quyền, idempotency và transition được xử lý deterministic.
- Mọi dữ liệu AI quan trọng có evidence/provenance.
- Human approval trước hành động ảnh hưởng bên ngoài.
- Không tự gửi email, Zalo hoặc thay đổi số liệu tài chính.
- Không đánh dấu PAID nếu chưa có bằng chứng reconciliation hợp lệ.
- Mọi external action có idempotency key, audit log và trạng thái retry rõ ràng.
- Tenant isolation được cưỡng chế ở backend/database, không chỉ ở frontend.
- Business logic không phụ thuộc trực tiếp SDK của OpenAI, Gemini hoặc Anthropic.
- OpenAI, Gemini và Anthropic tiếp tục dùng chung provider abstraction, schema validation, routing, fallback, usage và quality telemetry.
- Email, webhook, attachment và nội dung từ hệ thống ngoài đều là untrusted input.

# Yêu cầu chi tiết và Definition of Done

## V1-01 — MISA API

Thiết kế connector qua port/adapter để core domain không phụ thuộc MISA SDK hoặc endpoint cụ thể.

Tối thiểu phải có:

- Cấu hình connection theo tenant, secret reference, environment và capability.
- OAuth/token lifecycle hoặc cơ chế authentication đúng theo API chính thức được chọn.
- Đồng bộ customer/invoice/payment-relevant records cần thiết cho AR use case.
- Cursor/checkpoint, incremental sync, pagination, rate-limit handling, retry có backoff và dead-letter/replay.
- Idempotent upsert, external ID mapping, source/version/timestamp và conflict policy.
- Sync status, last-success, lag, lỗi có thể hành động và nút retry an toàn.
- Dữ liệu MISA được normalize qua canonical entities hiện có; không tạo domain model song song.
- Write-back chỉ triển khai nếu API chính thức, plan và phạm vi hiện có cho phép rõ ràng. Nếu có, mặc định tắt, cần approval/capability riêng và audit đầy đủ. Nếu không, ghi nhận read-only limitation thay vì giả lập.
- Fake MISA server/fixtures, contract tests, auth-expiry, pagination, duplicate, throttling và partial-failure tests.
- Hướng dẫn cấu hình và smoke-test sandbox không làm lộ secret.

DoD: một tenant test có thể sync incremental qua fake/sandbox, chạy lại không tạo record trùng, lỗi có thể retry/replay và toàn bộ mapping có audit/provenance.

## V1-02 — Outlook

Tái sử dụng email connector interface của Gmail; không fork business workflow riêng cho Outlook.

Tối thiểu phải có:

- Microsoft identity OAuth theo tenant/user và least-privilege scopes.
- Chọn mailbox/folder/category hoặc cơ chế scope tương đương label `AR-Agent`.
- Initial backfill và incremental synchronization bằng cơ chế chính thức phù hợp.
- Subscription/webhook validation, renewal, lifecycle notification, missed-event recovery và periodic reconciliation.
- Thread/conversation, sender/recipient, body, attachment và stable external IDs được normalize vào model email hiện có.
- Tạo Outlook draft sau approval; không tự gửi.
- Recipient/attachment guardrail, idempotency và duplicate-draft protection.
- Mock Graph server/fixtures và tests cho token expiry, pagination/delta, duplicate webhook, subscription expiry, attachment và draft.

DoD: cùng một PaymentCase workflow hoạt động với Gmail hoặc Outlook qua config; webhook lặp/mất không làm mất email hay tạo draft trùng.

## V1-03 — Zalo OA notification

Chỉ là kênh notification đã kiểm soát, không biến thành kênh thu hồi nợ tự động.

Tối thiểu phải có:

- Connector tách biệt, capability/config theo tenant và mapping người nhận đã xác minh.
- Template registry có version, locale, biến được phép và validation theo policy/API hiện hành.
- Consent/eligibility, recipient validation, rate limit, quiet hours và suppression/unsubscribe nếu áp dụng.
- Không gửi chi tiết công nợ nhạy cảm vào nhóm hoặc recipient chưa xác minh.
- Preview → approval → enqueue → delivery status; mặc định dry-run/sandbox.
- Idempotency, retry có giới hạn, webhook delivery receipt và audit.
- Không cho nội dung email/tài liệu điều khiển template, recipient hoặc tool action.
- Fake Zalo OA adapter và test success, reject, timeout, duplicate, invalid recipient/template và policy block.

DoD: user có thể preview và approve một notification hợp lệ trong môi trường test; mọi trường hợp không đủ quyền/consent/policy bị chặn trước external call.

## V1-04 — Bank reconciliation nâng cao

Mở rộng CSV reconciliation hiện có, không thay thế ledger nguồn bằng output LLM.

Phải hỗ trợ tối thiểu:

- Thanh toán một phần và nhiều lần cho một invoice.
- Một giao dịch trả cho nhiều invoice.
- Nhiều giao dịch gộp thành một khoản thanh toán.
- Bank fee, rounding/tolerance cấu hình, overpayment/underpayment.
- Duplicate transaction/import, reversal/refund và transaction correction.
- Khác currency chỉ khi có dữ liệu FX/tỷ giá có provenance; nếu thiếu thì manual review.
- Matching dựa trên amount, date window, transfer reference, invoice/customer identifiers và lịch sử; deterministic candidates trước, AI chỉ hỗ trợ dữ liệu mô tả mơ hồ.
- Confidence/calibration, giải thích từng feature, auto-match threshold nghiêm ngặt và review queue cho ambiguity.
- Allocation model rõ ràng; invariant tổng allocation không vượt transaction/invoice theo policy.
- Re-run an toàn khi rule thay đổi; không làm mất quyết định đã duyệt.

DoD: test suite bao phủ one-to-one, split, aggregate, partial, fee, duplicate, reversal, ambiguous và unmatched; không có double allocation hoặc state PAID sai.

## V1-05 — Customer-specific payment rules

Không thực thi code do người dùng nhập. Dùng rule model/DSL khai báo có schema validation.

Phải có:

- Rule theo tenant/customer, type, priority, effective date, expiry và version.
- Các loại rule tối thiểu: required documents, due-date calculation, grace period, tolerance, contact/escalation route, allowed channel và reminder cadence.
- Precedence rõ: system safety invariant > tenant policy > customer rule > default.
- Draft/publish/retire lifecycle, maker-checker hoặc quyền publish riêng, audit và rollback version.
- Simulator/preview chạy rule trên case mẫu trước publish.
- Conflict detection, invalid-rule rejection và deterministic evaluation.
- Temporal workflow xử lý thay đổi rule có version mà không phá workflow đang chạy.

DoD: hai customer trong cùng tenant có thể có quy tắc khác nhau; kết quả có explanation và rule version; rule xung đột/không hợp lệ không được publish.

## V1-06 — Bulk approval

Bulk approval phải an toàn hơn thao tác lặp thủ công, không chỉ là nút “approve all”.

Phải có:

- Chọn nhiều item với filter và select-all có phạm vi hiển thị rõ.
- Preview số lượng, tổng giá trị liên quan, channel, recipient, attachment, risk flags và item bị loại.
- Revalidate quyền, version, recipient, attachment, policy và case state tại thời điểm commit.
- Chỉ batch các action đồng nhất/đủ điều kiện; item rủi ro cao hoặc stale phải tách review.
- Batch có limit cấu hình, confirmation rõ, idempotency và per-item result.
- Partial failure không rollback mù các external action đã thành công; có retry/replay từng item.
- Không dùng một database transaction kéo dài qua external API calls.
- Audit batch và từng approval/action; export kết quả.

DoD: concurrent update, stale selection, mixed permission, partial failure, double click và retry đều có test; không tạo action trùng hoặc bypass approval.

## V1-07 — Aging forecast

Forecast phải có baseline đáng tin trước khi dùng mô hình phức tạp.

Phải có:

- Forecast dòng tiền thu theo tuần/tháng và aging bucket từ outstanding invoices.
- Deterministic baseline dựa trên due date, promise-to-pay và lịch sử payment delay.
- Nếu dữ liệu lịch sử đủ, thêm phương pháp thống kê/ML đơn giản, có backtest và so sánh với baseline; nếu chưa đủ thì không giả vờ có độ chính xác ML.
- Không leakage từ payment xảy ra sau thời điểm forecast.
- Customer/segment behavior, partial payment và broken promise được xử lý rõ.
- Prediction snapshot có `as_of`, horizon, model/rule version, inputs, confidence/interval và provenance.
- Metrics tối thiểu: MAE/WAPE hoặc metric phù hợp, calibration/coverage của interval, bias theo horizon và backtest theo thời gian.
- UI phân biệt amount contractual, expected và confidence; có warning khi data sparse/stale.
- Forecast chỉ hỗ trợ quyết định, không tự kích hoạt escalation hay thay đổi trạng thái tài chính.

DoD: seed dataset có backtest tái lập; baseline luôn chạy; mô hình nâng cao chỉ được bật khi vượt release criterion đã định nghĩa và không tệ hơn baseline.

## V1-08 — Role-based access chi tiết

Thiết kế permission theo action/resource và tenant scope; frontend visibility chỉ là UX, backend là enforcement.

Tối thiểu cân nhắc các role mặc định:

- Tenant admin.
- AR manager.
- AR specialist/collector.
- Account owner.
- Approver.
- Auditor/read-only.

Phải có permission matrix cho:

- View/edit case và financial fields.
- View/download documents và sensitive email.
- Manage connectors/secrets.
- Create/publish customer rules.
- Approve single/bulk action.
- Trigger/retry external action.
- View LLM cost/quality dashboard.
- Manage users/roles.
- Export/delete data.

Yêu cầu:

- Server-side policy check ở mọi API/activity có tác động.
- Tenant/resource ownership validation chống IDOR.
- PostgreSQL RLS hoặc lớp bảo vệ tương đương tiếp tục hoạt động.
- Custom role nếu kiến trúc hiện có phù hợp; nếu không, role cố định + permission mapping có đường nâng cấp rõ.
- Deny by default, separation of duties cho rule publish/bulk approval khi cấu hình yêu cầu.
- Role/permission change được audit; session/token cũ được refresh hoặc revoke phù hợp.
- Permission tests dạng matrix và negative tests giữa hai tenant.

DoD: toàn bộ privileged endpoint/action có policy test; user tenant A không đọc hoặc tác động tenant B; UI và API phản ánh cùng permission nhưng API không tin UI.

## V1-09 — Dashboard chi phí/chất lượng theo LLM provider

Tận dụng telemetry LLM gateway hiện có; không log raw prompt/document nhạy cảm chỉ để làm dashboard.

Phải có:

- Metrics theo tenant, time range, task type, provider, model, prompt version và route/fallback.
- Requests, success/error, schema-validity, fallback rate, latency p50/p95, input/output tokens và estimated cost.
- Quality metrics từ eval/human review: field accuracy, blocker F1 hoặc task-specific score, evidence faithfulness, unsupported output, edit/reject rate.
- Tách rõ online operational metrics và offline eval metrics; không trộn denominator.
- Pricing/config có currency, effective date và version vì giá model thay đổi; cost là estimate nếu provider không trả chi phí thực.
- Không hardcode giá hoặc model catalog trong business code. Cho phép unknown pricing mà không làm hỏng ingestion.
- Drill-down tới request metadata/audit an toàn, đã redaction; không hiển thị secret/raw sensitive content.
- RBAC cho dashboard và tenant isolation.
- Charts/table có empty/loading/error state, timezone và export phù hợp.
- Test aggregation, effective-dated pricing, missing usage, fallback chain và cross-tenant leakage.

DoD: dashboard trả lời được provider/model nào đang được dùng, chi phí ước tính, latency, fallback và chất lượng theo task trong một khoảng thời gian, với dữ liệu seed tái lập.

# Kiến trúc tương tác cần duy trì

Luồng connector:

MISA / Outlook / Zalo webhook
→ connector adapter
→ validation + deduplication
→ canonical event
→ domain service / Temporal signal
→ PostgreSQL + immutable audit
→ UI/read model.

Luồng external action:

Rule/case đề xuất action
→ policy + RBAC
→ preview
→ human approval
→ revalidation
→ idempotent activity/outbox
→ connector
→ delivery/sync result
→ audit + retry/review.

Luồng reconciliation:

Bank transaction
→ normalized ledger record
→ candidate generation
→ deterministic scoring/allocation
→ auto-match hoặc review
→ approved allocation
→ invoice/case transition
→ immutable reconciliation evidence.

Luồng LLM telemetry:

Provider-neutral gateway
→ normalized usage/latency/result metadata
→ redacted telemetry event
→ pricing/eval join theo version và thời điểm
→ aggregate read model
→ RBAC-protected dashboard.

# Thứ tự triển khai khuyến nghị

Điều chỉnh theo codebase thực tế nếu dependency khác, nhưng ghi lý do:

1. Audit, baseline, ADR và migration plan.
2. RBAC/permission foundation và shared connector/outbox primitives.
3. Customer-specific payment rules.
4. Advanced bank reconciliation.
5. Outlook vertical slice.
6. MISA vertical slice.
7. Zalo OA notification vertical slice.
8. Bulk approval trên các action đã có guardrail.
9. LLM provider cost/quality telemetry và dashboard.
10. Aging forecast, backtest và UI.
11. Cross-feature E2E, security, resilience, migration/rollback, docs và release gate.

Không ép tất cả thành một migration hoặc PR khổng lồ. Giữ thay đổi theo module và commit-ready; không tự commit nếu người dùng chưa yêu cầu.

# Dataset, fixtures và môi trường test

Mở rộng generator/fixtures MVP thay vì tạo dữ liệu thủ công không tái lập. Tối thiểu thêm:

- MISA pages/deltas, duplicate records, token expiry và throttling.
- Outlook conversations, attachments, delta tokens, duplicate/missed webhooks và expired subscription.
- Zalo template/recipient/delivery outcomes.
- Bank transactions cho split, aggregate, partial, fee, duplicate, reversal, refund, FX và ambiguous matching.
- Nhiều customer có payment rules khác nhau và rule version/conflict.
- Nhiều role, permission và hai tenant để test isolation.
- LLM calls đa provider/model/prompt version với usage, fallback, quality labels và effective-dated pricing.
- Lịch sử invoice/payment đủ để backtest aging forecast theo thời gian.

Generator phải có seed cố định, manifest/version và không chứa PII thật. CI phải chạy hoàn toàn offline bằng fake adapters; integration smoke test thật là opt-in.

# Chất lượng, migration và bảo mật

- Mọi schema change có forward migration, backfill strategy, index/concurrency consideration và rollback/roll-forward note.
- Với table lớn, tránh migration khóa dài; nếu quy mô chưa lớn vẫn ghi đường production-safe.
- Giữ backward compatibility cho workflow đang chạy và event payload đã lưu. Dùng versioning/patching phù hợp với workflow engine.
- Mọi network call có timeout, retry classification, rate-limit handling và observability.
- Dùng transactional outbox/inbox hoặc primitive hiện có để tránh mất/nhân đôi event.
- Secret không được commit, log hoặc trả về UI. Cập nhật `.env.example` bằng placeholder và tài liệu secret setup.
- Log phải redaction; attachment/email/webhook không được phép inject tool action.
- Thực hiện threat review cho OAuth, webhook authenticity, IDOR, confused deputy, replay, mass approval, data export và cross-tenant aggregation.
- Không dùng dữ liệu production để phát triển hoặc test.

# Validation bắt buộc

Sau mỗi vertical slice, chạy validation liên quan. Trước khi hoàn tất, chạy bộ kiểm tra rộng nhất khả dụng:

- Formatter/lint.
- Static type checks.
- Backend và frontend unit tests.
- Database/migration tests.
- Provider/connector contract tests.
- Temporal workflow replay/versioning tests nếu hệ thống dùng Temporal.
- Integration tests với fake services.
- RBAC matrix và cross-tenant negative tests.
- Reconciliation property/invariant tests.
- Forecast backtest/regression tests.
- Frontend component/E2E tests cho permission, bulk approval và dashboards.
- Build production.
- Minimal end-to-end demo smoke test.
- Security/dependency scan nếu repo đã có công cụ.

Không giảm hoặc xóa test chỉ để làm CI xanh. Nếu test hiện có phản ánh yêu cầu cũ, cập nhật test cùng lý do nghiệp vụ. Nếu không thể chạy một validation do thiếu hệ thống/credential, dùng fake/sandbox phù hợp, ghi command chính xác cho smoke test thật và nêu phần chưa được xác minh.

# Release gate V1

Chỉ tuyên bố V1 hoàn tất khi:

- Chín capability đều có code, migration, UI/API phù hợp, tests và tài liệu vận hành.
- Không có regression đã biết trong luồng MVP.
- Local/demo environment khởi động được bằng quy trình tài liệu hóa.
- Không cần credential thật để chạy automated test và demo seed flow.
- Không có external send/write thật trong default configuration.
- Không có test thất bại, build failure hoặc migration failure chưa giải thích.
- RBAC và tenant isolation vượt negative tests.
- Duplicate webhook/retry/double click không tạo external action hoặc allocation trùng.
- Reconciliation không vi phạm invariant tài chính.
- Forecast có baseline/backtest và hiển thị uncertainty.
- LLM dashboard tách online metrics khỏi offline quality và không lộ dữ liệu nhạy cảm.
- README/runbook/config reference/API docs/ADR được cập nhật.
- Có báo cáo phần nào đã kiểm thử bằng fake, sandbox hoặc live credential.

# Phạm vi bị loại trừ

Không triển khai trong lượt này:

- Tự gửi email hoặc Zalo không qua approval.
- Voice AI.
- Tự thương lượng, discount hoặc legal notice.
- Credit scoring.
- Fine-tuning.
- Multi-agent business architecture.
- Xây CRM/accounting system riêng.
- Bank credential scraping.
- Tính năng V2 không cần thiết cho chín capability V1.

# Cách báo cáo cuối

Kết quả cuối phải ngắn gọn nhưng có bằng chứng:

1. Chín capability và trạng thái/đường dẫn implementation tương ứng.
2. Quyết định kiến trúc quan trọng và migration đã thực hiện.
3. Test/build/eval đã chạy, command và kết quả.
4. External integration nào đã test bằng fake, sandbox hoặc live.
5. Rủi ro/giới hạn còn lại; không gọi V1 “hoàn tất” nếu còn hạng mục bắt buộc chưa làm.
6. Hướng dẫn ngắn để chạy local demo và cấu hình credential opt-in.

Hãy bắt đầu bằng việc kiểm tra repository và baseline hiện tại, tạo kế hoạch triển khai có thể theo dõi, rồi thực hiện V1 end-to-end.
```

## Lưu ý sử dụng

Prompt này dành cho repository thực sự chứa source code MVP. Nếu Codex báo chỉ nhìn thấy các file plan hoặc thư mục rỗng, hãy chuyển task sang đúng repository thay vì cho phép nó xây lại MVP.
