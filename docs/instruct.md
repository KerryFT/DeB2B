Bạn là lead software architect kiêm senior full-stack/AI engineer chịu trách nhiệm đưa dự án AR Operations Agent từ một thư mục gần như rỗng tới một MVP có thể chạy và demo end-to-end.

# Bối cảnh bắt buộc

Thư mục hiện tại là project root. Hiện tại dự án chưa có source code; tài liệu đặc tả chính nằm tại:

outputs/ar-operations-agent-implementation-plan.md

Hãy đọc TOÀN BỘ tài liệu này trước khi đưa ra bất kỳ quyết định nào. Nếu có AGENTS.md hoặc tài liệu hướng dẫn khác trong project root hay thư mục cha, hãy đọc và tuân thủ. Sau đó kiểm tra trạng thái thực tế của workspace để không giả định có sẵn code, dependency hoặc hạ tầng.

Sản phẩm cần xây là AR Operations Agent cho doanh nghiệp B2B: phát hiện nguyên nhân khiến hóa đơn chưa được thanh toán, tìm và đối chiếu hồ sơ, điều phối xử lý, soạn follow-up có bằng chứng, theo dõi promise-to-pay và đối soát thanh toán.

# Mục tiêu của lượt làm việc này

Chỉ nghiên cứu và lập một kế hoạch triển khai MVP đủ chi tiết để một coding agent có thể thực thi tuần tự ở lượt sau.

Tôi cần xem và phê duyệt kế hoạch trước. Vì vậy, trong lượt này:

- Không viết source code.
- Không scaffold ứng dụng.
- Không cài package hoặc dependency.
- Không tạo migration/database/container/cloud resource.
- Không chỉnh config chạy thật và không gọi API có tác dụng thay đổi dữ liệu.
- Không bắt đầu triển khai bất kỳ hạng mục sản phẩm nào.
- Chỉ được thực hiện kiểm tra read-only, nghiên cứu web và tạo/cập nhật tài liệu kế hoạch trong thư mục `docs/` nếu cần.

Khi đã hoàn tất kế hoạch, phải DỪNG LẠI và chờ tôi phê duyệt. Không được tự chuyển sang implementation dù kế hoạch đã rõ.

# Nguyên tắc làm việc

1. Lấy tài liệu `outputs/ar-operations-agent-implementation-plan.md` làm product/architecture brief gốc, nhưng phải kiểm chứng các giả định kỹ thuật có thể thay đổi theo thời gian.
2. Không thực hiện lại bước phỏng vấn hay xác nhận pain point với doanh nghiệp. Pain point và ICP được coi là giả định sản phẩm đã chốt cho MVP này.
3. Được phép và được kỳ vọng tìm kiếm web để kiểm tra tài liệu kỹ thuật, API, giới hạn, SDK, license và phương án tích hợp hiện hành.
4. Với thông tin kỹ thuật thay đổi theo thời gian, ưu tiên nguồn chính thức/primary source: tài liệu của Gmail API, Temporal, PostgreSQL, Docling, PaddleOCR, OpenAI, Google Gemini, Anthropic và các thư viện được chọn. Ghi URL nguồn và ngày truy cập trong kế hoạch.
5. Không sao chép dataset chứa dữ liệu cá nhân, bí mật kinh doanh, hóa đơn thật hoặc email thật không có quyền sử dụng. Chỉ đề xuất dùng dữ liệu synthetic, dữ liệu công khai có license phù hợp, hoặc dữ liệu đã được ẩn danh hợp pháp. Phải lưu provenance/license cho mọi nguồn dữ liệu thu thập.
6. Nếu internet hoặc một tài liệu bị chặn, ghi rõ khoảng trống cần xác minh nhưng vẫn tiếp tục lập kế hoạch bằng giả định hợp lý.
7. Tập trung vào con đường ngắn nhất tạo ra MVP end-to-end đáng tin cậy. Chỉ so sánh nhiều công nghệ khi quyết định đó thực sự ảnh hưởng lớn tới tốc độ, độ chính xác, chi phí hoặc khả năng vận hành.
8. Không hỏi tôi các câu hỏi có thể giải quyết bằng việc đọc plan, kiểm tra workspace, nghiên cứu tài liệu hoặc đưa ra giả định có thể đảo ngược. Chỉ nêu câu hỏi ở cuối nếu câu trả lời thực sự làm thay đổi kiến trúc/phạm vi hoặc chặn triển khai.

# Phạm vi MVP phải khóa

## ICP

- Doanh nghiệp B2B dịch vụ hoặc phân phối.
- Khoảng 100–5.000 hóa đơn/tháng.
- Email là kênh hồ sơ chính thức.
- Nguồn công nợ ban đầu là CSV/XLSX; chưa phụ thuộc API MISA.
- Chỉ một tenant pilot vẫn chấp nhận được, nhưng kiến trúc dữ liệu phải có `tenant_id` và không tạo ngõ cụt cho multi-tenant.

## Năm blocker nghiệp vụ bắt buộc

1. Thiếu hồ sơ thanh toán.
2. Hóa đơn/chứng từ sai thông tin.
3. Thiếu xác nhận nghiệm thu hoặc giao hàng.
4. Hóa đơn đang tranh chấp.
5. Đã có promise-to-pay nhưng chưa thanh toán.

## Luồng end-to-end tối thiểu

1. Import danh sách công nợ từ CSV/XLSX.
2. Tạo Customer, Invoice và PaymentCase bằng dữ liệu chuẩn hóa.
3. Đọc Gmail thread được gắn label cấu hình, bao gồm attachment; có phương án sync an toàn và idempotent.
4. Cho phép upload PDF/ảnh/XLSX và tiếp nhận attachment từ Gmail.
5. Phân loại và trích xuất có cấu trúc cho tối thiểu: hợp đồng/phụ lục, PO, hóa đơn, biên bản giao hàng/nghiệm thu, đề nghị thanh toán.
6. Mọi trường trọng yếu phải liên kết tới EvidenceSpan có thể kiểm tra lại.
7. Ghép document–customer–invoice–case bằng rule deterministic trước, AI chỉ xử lý phần mơ hồ.
8. Xác định một hoặc nhiều blocker, tạo next action/task và đưa case vào manual review khi confidence không đủ.
9. Quản lý vòng đời case bằng durable workflow/state machine; timer và retry phải sống qua restart.
10. Tóm tắt email, phát hiện tranh chấp và promise-to-pay.
11. Soạn follow-up theo blocker, nhưng chỉ tạo Gmail draft sau khi người dùng duyệt. MVP tuyệt đối không tự gửi email.
12. Import bank CSV, gợi ý ghép giao dịch với hóa đơn và chỉ chuyển PAID khi có bằng chứng/quy tắc hợp lệ.
13. Có dashboard, case queue, case detail, evidence viewer và approval inbox đủ dùng để demo.
14. Có audit trail cho state transition, human approval và mọi lần gọi/fallback LLM.
15. Có eval suite tái lập được và demo seed data để chạy luồng end-to-end mà không cần dữ liệu khách hàng thật.

## Ngoài phạm vi — không đưa vào kế hoạch implementation MVP

- MISA API hoặc ghi ngược vào phần mềm kế toán.
- Outlook, Zalo, voice agent.
- Kết nối ngân hàng trực tiếp hoặc bank scraping.
- Tự gửi email.
- Tự thương lượng, giảm nợ, sửa hóa đơn hoặc thay đổi thông tin tài chính.
- Chấm điểm tín dụng, cash-flow forecasting hoặc probability-to-pay.
- Legal notice, khởi kiện hoặc tư vấn pháp lý.
- Multi-agent architecture.
- Fine-tuning model.
- Xây CRM hoặc hệ thống kế toán hoàn chỉnh.
- Các tính năng V1/V2 trong plan gốc.

# Baseline kỹ thuật cần đánh giá và chốt

Ưu tiên baseline sau để phát triển nhanh, chỉ thay nếu nghiên cứu cho thấy có lý do rõ ràng:

- Monorepo.
- Frontend: Next.js + TypeScript.
- Backend/API: FastAPI + Python.
- Database: PostgreSQL; pgvector chỉ khi retrieval thực sự cần.
- Durable workflow: Temporal Python SDK; local Temporal cho development, thiết kế sẵn đường lên Temporal Cloud.
- Local development: Docker Compose.
- Object storage: local S3-compatible storage trong development và adapter cho S3/GCS ở deployment.
- Document parsing: parser native trước, Docling cho PDF có cấu trúc, PaddleOCR/PP-Structure cho scan/ảnh, vision LLM chỉ là fallback có kiểm soát.
- Gmail: OAuth, chỉ đọc label được cấu hình, tạo draft chứ không gửi.
- Auth: chọn phương án MVP hợp lý nhưng vẫn đảm bảo tenant context và role cơ bản.
- Observability: structured logs, OpenTelemetry/Sentry hoặc phương án tương đương phù hợp MVP.
- CI: lint, type check, unit/integration tests, migration check và build.

Hãy xác minh compatibility/version hiện hành trước khi chốt. Pin version hoặc version range có chủ đích; giải thích chiến lược upgrade. Không hardcode tên model có thể lỗi thời.

# Yêu cầu bắt buộc về LLM đa provider

Business logic không được phụ thuộc SDK của một hãng. MVP phải có provider abstraction và cấu hình cho tối thiểu:

- OpenAI
- Google Gemini
- Anthropic

Có thể chỉ bật một provider trong môi trường demo đầu tiên, nhưng interface, routing config, normalized response, schema validation, timeout, retry, fallback, usage/cost metadata và audit logging phải được thiết kế ngay từ đầu.

Trong kế hoạch phải làm rõ:

- Interface/port chung cho structured output và text generation.
- Adapter riêng cho từng provider.
- Model ID lấy từ environment/config, không nhúng cố định vào business code.
- Capability-based routing theo task, không theo tên model viết rải rác.
- JSON Schema/Pydantic validation độc lập với provider.
- Giới hạn repair và fallback; không tạo vòng lặp vô hạn.
- Không fallback với lỗi policy, input sai hoặc case bắt buộc human review.
- Ghi lại provider, model, prompt version, latency, token usage, lỗi và schema-validity.
- Mock/fake provider để test offline và CI không cần API key.
- Contract test dùng chung cho ba adapter.
- Phương án bảo vệ dữ liệu nhạy cảm và giảm lượng context gửi tới provider.

# Dataset và eval — Codex phải tự chuẩn bị trong giai đoạn implementation

Không được phụ thuộc vào việc tôi cung cấp dữ liệu thật. Hãy lập kế hoạch để Codex ở lượt implementation có thể tự tạo hoặc thu thập hợp pháp bộ dữ liệu cần thiết.

Benchmark tối thiểu theo plan gốc:

- 100 hóa đơn.
- 50 hợp đồng/phụ lục.
- 100 PO/biên bản giao hàng hoặc nghiệm thu.
- 100 email thread.
- 50 case tranh chấp.
- 50 case promise-to-pay.
- 50 giao dịch ngân hàng.
Dataset plan phải mô tả cụ thể:

1. Schema/annotation format và gold labels cho từng loại dữ liệu.
2. Cách tạo synthetic data có seed cố định, tái lập được và không chứa PII thật.
3. Template tiếng Việt là chính, có một phần song ngữ Việt–Anh.
4. Biến thể thực tế: scan rõ/mờ, xoay, perspective, nhiễu, nhiều font, dấu tiếng Việt, bảng nhiều trang, chữ ký thiếu, số hóa đơn gần giống, số tiền lệch, PO/hợp đồng không khớp, email forward/reply lộn xộn, thanh toán gộp/tách và promise date mơ hồ.
5. Negative/adversarial cases, gồm prompt injection nằm trong email/attachment; hệ thống phải coi toàn bộ nội dung tài liệu là untrusted data.
6. Cách chia train/dev/test hoặc build/calibration/held-out test để tránh leakage. Không cần fine-tuning trong MVP; “train” ở đây chỉ dùng cho phát triển rule/prompt.
7. Data manifest ghi nguồn, license, checksum, generator version và seed.
8. Nếu thu thập dữ liệu công khai, chỉ dùng nguồn có quyền sử dụng rõ ràng; liệt kê URL/license và quy trình loại PII.
9. Script/generator dự kiến sẽ tạo ở đâu, output đặt ở đâu, dung lượng ước tính và dữ liệu nào được commit vào Git.
10. Quy trình human spot-check và cách sửa gold label có versioning.

Phải đề xuất dataset nhỏ dùng cho smoke test/CI và dataset đầy đủ dùng cho eval cục bộ. Không để CI gọi LLM trả phí hoặc phụ thuộc internet.

# Ngưỡng chất lượng MVP

Dùng ngưỡng trong plan gốc làm mục tiêu, nhưng phân biệt rõ:

- Release gate bắt buộc về safety/correctness.
- Target chất lượng cần đạt nếu dataset cho phép.
- Metric cần calibration thêm thay vì hứa chắc không có bằng chứng.

Ít nhất phải đo:

- Document classification accuracy.
- Exact match/field-level F1 cho MST, số hóa đơn, ngày, số tiền.
- Payment-term extraction với evidence.
- Document–invoice matching precision/recall và calibration theo threshold.
- Blocker macro-F1.
- Promise-date extraction.
- Evidence faithfulness/coverage.
- JSON/schema validity.
- Hallucination/unsupported claim rate.
- Cross-provider quality, latency và chi phí.
- Email wrong-recipient = 0 trong test suite.
- Duplicate draft/external action = 0 trong idempotency tests.
- Unauthorized state mutation = 0.

# Những nội dung kế hoạch phải trả lời

Hãy lập kế hoạch có thể thực thi, không viết một roadmap chung chung. Tài liệu phải bao gồm:

1. Tóm tắt điều hành và định nghĩa “MVP hoàn thành”.
2. Bảng traceability: mỗi yêu cầu MVP được giải quyết ở component, phase, test và acceptance criterion nào.
3. Assumptions đã chọn và các điểm khác biệt/điều chỉnh so với plan gốc.
4. Scope in/out đã khóa.
5. Quyết định stack cuối cùng, version dự kiến, lý do và nguồn chính thức hỗ trợ quyết định quan trọng.
6. Sơ đồ kiến trúc và data flow từ CSV/Gmail/document tới PaymentCase, blocker, approval, Gmail draft và bank reconciliation.
7. Boundary giữa deterministic code, OCR/document AI, LLM, workflow engine và human approval.
8. Cấu trúc monorepo dự kiến đến cấp thư mục/module; nêu trách nhiệm từng phần.
9. Domain model, bảng dữ liệu chính, khóa/index, tenant isolation, audit/event model và retention.
10. State machine/event catalog; event nào do rule, người dùng, connector hoặc LLM đề xuất; invariant và illegal transition.
11. API contract/module contract cần thiết giữa frontend, backend, worker, workflow, storage và connectors.
12. Thiết kế ingestion cho CSV/XLSX, Gmail và file; idempotency, deduplication, retry, backfill, pagination và failure recovery.
13. Document pipeline: preprocessing, parser selection, OCR fallback, structured extraction, evidence coordinates, cache theo hash và manual review.
14. Matching/blocker engine: features, rule priority, threshold, calibration, ambiguity handling và giải thích kết quả.
15. Temporal workflows/activities/signals/queries/timers, retry policy và versioning strategy.
16. Approval workflow và guardrail trước khi tạo Gmail draft; recipient/attachment validation và chống draft trùng.
17. LLM multi-provider architecture theo yêu cầu ở trên.
18. Dataset generation/collection plan và eval harness.
19. UX scope theo từng màn hình, các loading/empty/error/review state và responsive baseline.
20. Security/threat model: OAuth token, secret, file upload, malware/content-type, RLS, prompt injection, log redaction, encryption, data deletion/export và least privilege.
21. Local development, environment variables, secret handling, seed/demo procedure và một lệnh hoặc chuỗi lệnh tối thiểu để chạy demo.
22. Test pyramid: unit, contract, integration, workflow, connector mock, E2E, security, load, backup/restore và regression eval.
23. Deployment topology cho demo/staging và production-ready path, nhưng không over-engineer MVP.
24. Observability, SLO/health checks, failure queues và runbook tối thiểu.
25. Risk register: xác suất, tác động, dấu hiệu phát hiện, mitigation và fallback.
26. Ước lượng effort/critical path theo giả định 1–2 developer; chỉ ra hạng mục có thể song song và hạng mục bắt buộc tuần tự.
27. Các quyết định cần tôi phê duyệt trước khi implementation.

# Cách chia phase và task

Tự chọn số phase hợp lý, nhưng kế hoạch phải đi từ foundation đến demo end-to-end theo vertical slices. Tránh để frontend, AI hoặc integration chỉ hội tụ ở cuối.

Mỗi phase phải có:

- Mục tiêu/user-visible outcome.
- Các task theo thứ tự dependency.
- File/thư mục/module dự kiến tạo hoặc sửa.
- Dữ liệu/migration/config liên quan.
- Test và validation command dự kiến.
- Acceptance criteria đo được.
- Failure behavior và rollback/fallback.
- Deliverable demo được ở cuối phase.
- Ước lượng effort và dependency/blocker.

Mỗi task nên đủ nhỏ để Codex thực thi và kiểm tra trong một lượt làm việc hợp lý. Đánh ID ổn định như `P0-T01`, `P1-T01` để lượt implementation có thể tham chiếu và báo cáo tiến độ.

Ưu tiên một vertical slice sớm chứng minh được:

CSV invoice + một Gmail thread + một bộ tài liệu synthetic
→ tạo PaymentCase
→ trích xuất evidence
→ phát hiện một blocker
→ người dùng review
→ tạo Gmail draft giả lập hoặc sandbox
→ ghi audit trail.

Sau đó mới mở rộng đủ năm blocker, bank reconciliation, dashboard và hardening.

# Deliverable của lượt planning

Được phép tạo duy nhất các tài liệu planning sau (không tạo code):

- `docs/MVP_IMPLEMENTATION_PLAN.md` — tài liệu kế hoạch đầy đủ, là nguồn chính.
- `docs/MVP_TASKS.md` — checklist task có ID, dependency, acceptance criteria và trạng thái ban đầu `pending`.
- `docs/MVP_DATASET_AND_EVAL_PLAN.md` — kế hoạch dataset, provenance, generator và eval.
- `docs/MVP_DECISIONS.md` — ADR index/decision log ngắn, gồm assumption và vấn đề cần phê duyệt.

Nếu một tài liệu duy nhất rõ hơn, có thể gộp chúng vào `docs/MVP_IMPLEMENTATION_PLAN.md`, nhưng phải giữ đủ toàn bộ nội dung bắt buộc.

Trong câu trả lời cuối của lượt này:

1. Tóm tắt kiến trúc và đường critical path trong tối đa 12 bullet.
2. Liệt kê các file planning đã tạo.
3. Nêu các assumption quan trọng đã tự chốt.
4. Nêu tối đa 5 quyết định thực sự cần tôi phê duyệt, kèm phương án khuyến nghị đầu tiên và trade-off.
5. Xác nhận rõ rằng chưa có source code, dependency hay infrastructure nào được tạo/thay đổi.
6. Kết thúc bằng câu hỏi xin phê duyệt kế hoạch.

# Stop rule tuyệt đối

Sau khi tạo và trình bày các planning deliverable, dừng công việc. Không thực thi task `P0-T01` hay bất kỳ implementation task nào cho tới khi tôi trả lời rõ ràng rằng kế hoạch đã được duyệt và yêu cầu bắt đầu triển khai.
