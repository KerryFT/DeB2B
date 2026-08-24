# Production Readiness Audit và triển khai `deb2b.id.vn`

Bạn là principal engineer, security-minded production owner và SRE chịu trách nhiệm đánh giá toàn bộ AR Operations Agent hiện tại, sửa các điểm chưa đạt, thiết kế hạ tầng phù hợp với codebase thực tế và triển khai một production release an toàn tại domain:

https://deb2b.id.vn

Đây là yêu cầu thực thi end-to-end, không chỉ review. Hãy audit → đưa ra GO/CONDITIONAL GO/NO-GO có bằng chứng → sửa các blocker có thể sửa → chuẩn bị hạ tầng và CI/CD → deploy → cấu hình domain/TLS → chạy production-safe verification → bàn giao runbook. Có thể thay đổi, giản lược hoặc bổ sung yêu cầu kỹ thuật bên dưới khi codebase thực tế cho thấy phương án khác tốt hơn, nhưng phải ghi rõ lý do và không được hạ thấp các invariant về an toàn, dữ liệu tài chính, tenant isolation hoặc external actions.

# 1. Kiểm tra đầu vào trước tiên

1. Xác nhận thư mục hiện tại đúng là repository chứa MVP, V1 và V2 đã hoàn thiện. Đọc toàn bộ `AGENTS.md` áp dụng, README, architecture docs, ADR, API docs, migrations, deployment files, CI, runbooks và các plan trước đây.
2. Kiểm tra git status và bảo toàn mọi thay đổi của người dùng. Không reset, restore, xóa hoặc ghi đè thay đổi không thuộc nhiệm vụ.
3. Xác định chính xác stack, package manager, services, worker/workflow engine, database, object storage, authentication, email/connectors, observability và cloud/IaC đã tồn tại. Không áp một template cloud chung lên codebase mà chưa hiểu hệ thống.
4. Chạy baseline validation hiện có và ghi lỗi có trước: lint, formatting, type checks, unit/integration/E2E, build, migrations, evals và security checks.
5. Nếu repository không có source code ứng dụng, V2 thực tế chưa hoàn thiện, hoặc đang ở sai thư mục, dừng và báo bằng chứng. Không xây lại dự án từ đầu dưới tên “production deployment”.
6. Kiểm tra công cụ/cloud CLI/account đã đăng nhập bằng thao tác read-only. Không in token, API key, connection string hoặc secret vào log/chat.

# 2. Quyền thực thi và ranh giới phê duyệt

Người dùng cho phép:

- Đọc và đánh giá toàn bộ repository.
- Sửa source code, config, tests, migrations, Docker/IaC, CI/CD và tài liệu để đạt production readiness.
- Tạo hoặc cập nhật hạ tầng trong tài khoản/project đã được người dùng đặt trong phạm vi cho deployment này.
- Deploy production cho dự án và cấu hình domain `deb2b.id.vn` nếu credential/công cụ hợp lệ đã có.
- Tạo DNS records cần thiết cho domain này nếu có quyền quản trị DNS và thay đổi không ảnh hưởng dịch vụ khác.
- Chạy smoke test an toàn, dùng synthetic production test tenant và fake/sandbox external integrations.

Phải dừng và xin xác nhận trước khi:

- Mua gói/dịch vụ mới, bật resource có chi phí đáng kể hoặc cam kết kỳ hạn.
- Xóa database, bucket, deployment, DNS record hoặc resource đang tồn tại.
- Thay đổi nameserver toàn domain hoặc record đang phục vụ hệ thống khác mà chưa xác minh.
- Import dữ liệu khách hàng thật hoặc chạy migration có nguy cơ mất dữ liệu không có backup/rollback đã kiểm chứng.
- Gửi email/Zalo/Outlook thật, bật auto-send production hoặc gọi write-back MISA trên dữ liệu thật.
- Làm thay đổi material ngoài phạm vi production hóa dự án.

Nếu thiếu credential hoặc quyền external, không dừng toàn bộ công việc quá sớm. Hoàn thiện code, IaC, scripts, docs và validation không cần credential; sau đó hỏi đúng thông tin/quyền nhỏ nhất còn thiếu.

# 3. Nguyên tắc quyết định linh hoạt

Các yêu cầu sau là production baseline, không phải mệnh lệnh dùng một vendor cụ thể:

- Ưu tiên phương án đơn giản, managed, dễ rollback và chi phí hợp lý cho 1–3 tenant pilot.
- Ưu tiên region Singapore/Đông Nam Á nếu provider và dịch vụ hiện có hỗ trợ, nhưng chọn region dựa trên latency, availability, data policy và account thực tế.
- Tái sử dụng hạ tầng/IaC hợp lý đã có. Không di chuyển cloud hoặc rewrite chỉ để phù hợp một kiến trúc lý tưởng.
- Modular monolith + workers + managed PostgreSQL/Temporal/object storage là chấp nhận được; không cần Kubernetes, Kafka hay microservices nếu tải chưa chứng minh cần thiết.
- Dùng staging khi thay đổi có rủi ro hoặc hạ tầng hiện tại hỗ trợ. Nếu chỉ có production tối giản, phải có preview/local equivalent, backup, canary/rolling strategy và rollback rõ.
- Tự chọn giữa Cloud Run, Vercel, managed container platform hoặc kiến trúc khác theo codebase. Ghi ADR ngắn cho lựa chọn cuối.
- Không gọi hệ thống “production-ready” chỉ vì deploy thành công. Production readiness phải dựa trên bằng chứng kiểm thử, security, recovery và vận hành.

# 4. Deliverable audit bắt buộc

Tạo hoặc cập nhật:

- `docs/PRODUCTION_READINESS_REPORT.md`
- `docs/PRODUCTION_ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docs/RUNBOOK.md`
- `docs/SECURITY_AND_PRIVACY.md`
- `docs/RELEASE_CHECKLIST.md`

Có thể gộp tài liệu nếu repo đã có cấu trúc docs tốt hơn. Tránh tạo tài liệu trùng lặp; cập nhật nguồn sự thật hiện có khi phù hợp.

Readiness report phải có:

- Executive verdict: `GO`, `CONDITIONAL GO` hoặc `NO-GO` trước sửa và sau sửa.
- Ma trận feature MVP/V1/V2: implemented, tested, live-verified, disabled, stub hoặc missing.
- Findings có ID, severity `P0/P1/P2/P3`, evidence cụ thể (file/test/config/runtime), impact và remediation.
- Phân biệt rõ code-complete, tested bằng fake, sandbox-verified và live-verified.
- Danh sách blocker đã sửa, blocker còn lại và lý do.
- Không coi TODO, mock adapter hoặc UI placeholder là tính năng hoàn thành.

Severity:

- `P0`: có thể gây mất/lộ dữ liệu, cross-tenant access, sai số tài chính, external action ngoài ý muốn, credential exposure hoặc outage nghiêm trọng. Cấm deploy.
- `P1`: chức năng cốt lõi không đáng tin, không rollback/recover được, thiếu auth/backup/monitoring quan trọng. Cấm public launch; có thể deploy internal staging nếu an toàn.
- `P2`: ảnh hưởng vận hành/chất lượng nhưng có workaround rõ.
- `P3`: cải thiện hoặc technical debt không chặn release.

# 5. Audit chức năng và correctness

Kiểm tra end-to-end, không chỉ đọc code:

- CSV/XLSX ingestion, Gmail/Outlook, upload/document extraction và evidence.
- Document–invoice–customer matching và năm blocker cốt lõi.
- PaymentCase state machine, Temporal/workflow timers, retry và replay/versioning.
- Approval, draft, recipient/attachment guardrail và audit trail.
- MISA, Outlook, Zalo connectors: thật/fake/sandbox status, auth lifecycle, webhook retry/dedup.
- Bank reconciliation: partial, split, aggregate, fee, duplicate, reversal, ambiguity và financial invariants.
- Customer-specific rules, versioning và conflict handling.
- Bulk approval với stale state, partial failure và idempotency.
- RBAC, tenant isolation và cross-tenant negative cases.
- LLM provider abstraction OpenAI/Gemini/Anthropic, schema validation, routing/fallback và cost/quality telemetry.
- Aging/probability-to-pay/cash-flow forecast: point-in-time correctness, baseline, calibration/backtest và stale behavior.
- Dispute root cause, customer behavior profile và account-manager benchmark có provenance/uncertainty.
- Auto-send: mặc định `disabled` hoặc `shadow`; kill switch, cap, suppression và pre-send revalidation.

Nếu một tính năng không đủ dữ liệu để chứng minh hiệu quả, ghi “pipeline verified, business accuracy unverified” thay vì tuyên bố đạt production quality.

# 6. Security review và hardening

Thực hiện threat-model và kiểm tra tối thiểu:

## Identity, session và authorization

- Production auth không dùng bypass/dev user/default password.
- Secure cookie/token settings, expiration, rotation/revocation và CSRF khi áp dụng.
- Backend authorization ở mọi privileged endpoint/activity; frontend guard không được coi là security boundary.
- Tenant ownership/RLS/IDOR negative tests trên raw data, files, predictions, aggregates và exports.
- Least privilege cho service accounts, DB roles, OAuth scopes và CI deploy identity.
- Admin/bootstrap process an toàn, không public self-promote thành admin.

## Secrets và supply chain

- Không có secret trong Git, image, frontend bundle, test fixture, log hoặc docs.
- Secret dùng managed secret store hoặc cơ chế production tương đương; rotation/runbook rõ.
- Dependency lockfile, vulnerability scan, image scan/SBOM/signing nếu toolchain hiện tại hỗ trợ hợp lý.
- Pin base image/dependency có chủ đích; loại debug package và dev server khỏi production.

## Web/API

- Strict CORS allowlist cho production origins.
- CSRF, XSS, SQL injection, SSRF, unsafe redirect, mass assignment, request smuggling/proxy header trust và file-path traversal được kiểm tra phù hợp stack.
- Rate limit cho auth, upload, expensive AI/OCR, webhook và external-action endpoints.
- Request/body/file size limits, timeout và concurrency limits.
- Security headers: HSTS chỉ sau khi HTTPS hoạt động đúng, CSP phù hợp, frame/referrer/content-type policies.
- Không lộ stack trace, internal URL, provider response hoặc sensitive metadata cho client.

## Upload/document/email/webhook

- MIME/signature validation, extension mismatch, decompression bomb, oversized/malformed PDF/image và malware scanning/quarantine hoặc policy tương đương.
- Object keys không đoán được; signed URL ngắn hạn; bucket private; server-side encryption và lifecycle/retention.
- Email/document là untrusted content; prompt injection không thể tạo tool/external action.
- Webhook signature/token/audience verification, replay protection, timestamp tolerance, dedup và safe retry.

## Financial/external actions

- State transition, reconciliation allocation và paid status có invariant/property tests.
- Transactional outbox/idempotency bảo vệ retry/double-click/duplicate webhook.
- Mọi external action revalidate quyền, case version, recipient, payment/dispute và policy ngay trước execution.
- Auto-send production giữ `disabled` hoặc `shadow` trong lần deploy đầu, trừ khi người dùng xác nhận bật riêng sau khi xem shadow metrics.
- Global/tenant kill switch hoạt động mà không cần redeploy.

## AI/data privacy

- Không log raw contract/email/document hoặc full prompts chứa dữ liệu nhạy cảm.
- Context minimization, provider/model audit và tenant-specific provider policy.
- Dữ liệu synthetic cho staging/test; không fine-tune bằng dữ liệu khách hàng.
- Data export/delete/retention xử lý cả raw, derived, prediction, cache, object và audit theo policy được thiết kế.
- Kiểm tra yêu cầu pháp lý/quyền riêng tư áp dụng bằng nguồn chính thức; không tự tuyên bố tuân thủ pháp luật nếu chưa có legal review.

# 7. Reliability, database và recovery

- Production database không public Internet nếu có thể tránh; TLS, credentials riêng, connection pool và statement/idle timeout.
- Migrations phải backward-compatible hoặc có maintenance/rollback plan. Không chạy destructive migration trước backup.
- Kiểm tra index/query plan cho dashboard, queues, tenant filters, event/audit và reconciliation.
- Backup tự động, retention hợp lý, point-in-time recovery nếu provider hỗ trợ.
- Thực hiện restore test vào môi trường tách biệt hoặc chứng minh quy trình bằng provider-supported method an toàn; không chỉ bật checkbox backup.
- Xác định RPO/RTO thực tế cho pilot. Baseline gợi ý để cân nhắc: RPO ≤24 giờ, RTO ≤4 giờ; cải thiện nếu chi phí hợp lý.
- Object storage versioning/retention/restore phù hợp; orphan cleanup và failed-upload recovery.
- Worker/workflow health, stuck workflow detection, dead-letter/replay, webhook catch-up và periodic reconciliation.
- Graceful shutdown, health/readiness probes, bounded retry, circuit breaker và protection chống retry storm.
- Scheduler/timers dùng timezone rõ; business dates hiển thị Asia/Ho_Chi_Minh hoặc timezone tenant, storage dùng UTC.

# 8. Performance, capacity và cost

Thiết lập một workload model dựa trên ICP và codebase; tối thiểu mô phỏng pilot hợp lý thay vì benchmark vô nghĩa.

Đo và ghi:

- API latency p50/p95/p99 cho endpoints chính.
- Concurrent users và case queue/dashboard load.
- CSV import, email webhook burst, document/OCR throughput và worker backlog.
- DB connection/query pressure, memory/CPU và object-storage traffic.
- LLM timeout/fallback/cost; OCR/file size worst cases.
- Forecast/eval jobs không làm nghẽn request path.

Đặt resource limit, autoscaling/min/max instances, concurrency và budget alerts phù hợp. Tránh scale-to-zero nếu gây mất webhook/timer SLA, nhưng không overprovision khi pilot.

Cung cấp ước tính chi phí theo tháng với assumptions và tách fixed/variable cost. Không tự tạo resource đắt tiền nếu chưa được phép.

# 9. Observability và vận hành

Phải có hoặc hoàn thiện:

- Structured logs có correlation/request/tenant-safe IDs và redaction.
- Metrics/traces cho API, DB, workflow, queue, connectors, OCR, LLM, external action và forecast jobs.
- Error tracking không chứa dữ liệu nhạy cảm.
- Health/readiness endpoints kiểm tra đúng dependency nhưng không lộ chi tiết.
- Dashboards và alerts tối thiểu: availability/error rate, latency, DB capacity, worker lag, workflow stuck, webhook failures, connector token expiry, outbox/dead-letter, duplicate prevention, external-send anomaly, LLM cost spike, storage và backup failure.
- Alert có owner, severity, threshold và runbook; không tạo alert không thể hành động.
- Audit log bất biến/append-only theo khả năng hệ thống, retention và export rõ.

SLO pilot có thể điều chỉnh theo hạ tầng/chi phí, nhưng phải được ghi và đo. Gợi ý ban đầu:

- Web/API monthly availability ≥99.5%.
- Không mất accepted webhook/event; recovery qua backfill/reconciliation.
- Wrong recipient, duplicate external send và cross-tenant access = 0.
- P95 interactive API phù hợp UX; tác vụ OCR/AI chạy async với progress rõ.

# 10. Kiến trúc deployment và domain

Sau audit, chọn topology phù hợp và ghi ADR. Baseline tham khảo nếu codebase không có lựa chọn tốt hơn:

- Frontend tại `https://deb2b.id.vn`.
- `https://www.deb2b.id.vn` redirect vĩnh viễn về apex hoặc ngược lại, chỉ chọn một canonical host.
- API tại cùng origin `/api` nếu deployment hỗ trợ đơn giản/an toàn; nếu cần tách, dùng `https://api.deb2b.id.vn` với CORS/cookie/OAuth được cấu hình chính xác.
- Webhook dùng path trên API domain; không cần subdomain riêng nếu không có lý do vận hành.
- Managed PostgreSQL, private object storage, managed secrets và managed workflow service hoặc production-safe workflow deployment tương thích codebase.
- CDN/WAF/rate limiting nếu provider sẵn có và chi phí hợp lý.

Domain/TLS checklist:

- Kiểm tra DNS records hiện có trước khi thay đổi; lưu snapshot/rollback values.
- Không thay nameserver nếu chỉ cần A/AAAA/CNAME/TXT records.
- Cấu hình domain verification, certificate provisioning/renewal và HTTPS redirect.
- Kiểm tra apex, canonical redirect, TLS chain, expiry/auto-renew, HTTP→HTTPS, mixed content và security headers.
- Cập nhật production base URLs, CORS, CSRF trusted origins, cookie domain, OAuth redirect URIs và webhook callback URLs.
- DNS TTL hợp lý cho cutover; không hạ TTL hoặc thay record không liên quan một cách tùy tiện.
- Không phát hành HSTS preload hoặc includeSubDomains nếu chưa xác minh toàn bộ subdomain.

# 11. Environment và secrets

- Tách local/test/staging/production config; fail fast khi thiếu biến bắt buộc.
- Có schema/validator cho env; không dùng production fallback sang localhost, demo tenant hoặc mock provider.
- `.env.example` chỉ chứa tên biến và placeholder.
- Phân loại biến: public frontend, runtime config, secret, connector credential và operational flag.
- Production feature flags an toàn: auto-send disabled/shadow; MISA write-back disabled; Zalo real send disabled; destructive admin/debug endpoints disabled.
- Model IDs, provider routing và pricing nằm trong config/versioned data, không hardcode rải rác.
- Secret rotation không yêu cầu rebuild frontend và có runbook.

# 12. CI/CD, IaC và release strategy

Ưu tiên IaC hoặc deployment config tái lập được. Không chỉ deploy bằng các click không được ghi lại.

Pipeline tối thiểu:

1. Install với lockfile/frozen mode.
2. Lint/format check/type check.
3. Unit/contract/integration/security tests.
4. Build frontend/backend/workers.
5. Migration compatibility/check.
6. Build immutable artifact/image, scan nếu có công cụ.
7. Deploy staging/preview hoặc production candidate.
8. Run smoke tests.
9. Apply production migration theo chiến lược an toàn.
10. Deploy rolling/canary phù hợp.
11. Post-deploy verification.
12. Automatic/manual rollback trigger rõ.

Yêu cầu:

- Artifact/image immutable và có version/commit SHA.
- Không build một source khác giữa staging và production.
- CI identity least privilege; production environment protection phù hợp nền tảng.
- Migration và app deploy order không gây downtime/schema mismatch.
- Rollback app không phụ thuộc rollback database nguy hiểm.
- Ghi release version, migrations, feature flags và deployment timestamp.

# 13. Validation và production-safe smoke test

Trước deployment, chạy rộng nhất có thể:

- Formatter, lint, type checks.
- Backend/frontend unit tests.
- Integration/contract tests với fake providers.
- Migrations từ database rỗng và upgrade path từ version hiện tại.
- Workflow replay/versioning.
- RBAC/RLS/two-tenant negative tests.
- Reconciliation invariant/property tests.
- LLM eval regression và JSON/evidence checks.
- Forecast point-in-time/backtest regression.
- Auto-send safety/kill-switch/idempotency tests.
- E2E critical path và production builds.
- Dependency/image/security scans.
- Backup/restore test hoặc verified recovery exercise.
- Load/resilience tests ở quy mô pilot.

Sau deployment, dùng synthetic production test tenant và không phát sinh external send thật để kiểm tra:

1. Homepage/login/auth callback.
2. Health/readiness và database connectivity.
3. Tenant isolation cơ bản.
4. Import một CSV synthetic.
5. Upload một tài liệu synthetic và chạy pipeline/evidence.
6. Tạo PaymentCase, phát hiện blocker và review.
7. Tạo draft qua fake/sandbox path hoặc dry-run, không gửi.
8. Reconciliation synthetic.
9. Dashboard/forecast/profile render.
10. Audit, metrics, traces và alerts nhận đúng event.
11. Backup job/status và kill switches.

Nếu bất kỳ P0/P1 xuất hiện sau deploy, rollback hoặc disable affected feature ngay; không giữ production ở trạng thái không rõ ràng.

# 14. Tiêu chí GO-LIVE

Chỉ kết luận production-ready khi:

- Không còn P0/P1 chưa xử lý hoặc chưa có mitigation được chấp nhận rõ.
- Tất cả test/build/migration bắt buộc xanh hoặc exception được chứng minh không ảnh hưởng release.
- Auth, RBAC, RLS và tenant isolation vượt negative tests.
- Backup tồn tại và restore procedure đã được kiểm chứng ở mức hợp lý.
- Logs/metrics/alerts/runbook hoạt động.
- Domain/TLS/redirect/security headers đúng.
- Secrets nằm ngoài repo/image/client bundle.
- External action mặc định an toàn; auto-send và write-back production không tự bật.
- Critical end-to-end smoke test qua `deb2b.id.vn` thành công.
- Có rollback procedure và release identifier.
- Tình trạng live verification của MISA/Outlook/Zalo/LLM được ghi trung thực.
- Dự báo/AI được trình bày với uncertainty và không thay thế financial truth.

Nếu chưa đạt, có thể triển khai internal/staging hoặc limited pilot an toàn, nhưng verdict phải là `CONDITIONAL GO`/`NO-GO`, kèm đúng blocker và bước tiếp theo. Không dùng từ “production-ready” như một lời trấn an.

# 15. Cách xử lý blocker

- Blocker trong code/config/test/IaC nằm trong phạm vi: tự sửa và kiểm chứng.
- Blocker do thiếu credential/quyền: hoàn thiện mọi phần offline, sau đó yêu cầu đúng secret/quyền nhỏ nhất; không yêu cầu người dùng dán secret vào source hoặc chat nếu có secret manager/CLI login.
- Blocker do lựa chọn cloud chưa có: đưa tối đa 2 phương án, khuyến nghị một phương án dựa trên codebase, chi phí và vận hành; chỉ hỏi quyết định nếu lựa chọn gây chi phí hoặc lock-in đáng kể.
- Blocker do DNS: cung cấp chính xác record name/type/value/TTL và xác minh record hiện tại trước khi thay đổi.
- Blocker pháp lý/data policy: nêu yêu cầu cần legal review; không tự đưa kết luận pháp lý.

# 16. Báo cáo cuối cùng

Trả lời có bằng chứng và dẫn đường dẫn file cụ thể:

1. Verdict trước và sau remediation: GO/CONDITIONAL GO/NO-GO.
2. Findings P0–P3, mục đã sửa và mục còn lại.
3. Kiến trúc deployment thực tế và lý do chọn.
4. Hạ tầng/resource đã tạo hoặc cập nhật; region và chi phí ước tính.
5. Test, build, migration, security, load và recovery checks đã chạy cùng kết quả.
6. URL production/canonical domain, API URL nếu tách, release/version và trạng thái TLS.
7. Production smoke test đã chạy và kết quả từng bước.
8. Trạng thái connector/LLM: fake, sandbox hoặc live-verified.
9. Feature flags nguy hiểm hiện tại, đặc biệt auto-send/MISA write-back/Zalo send.
10. Monitoring/alerts/backups/rollback/kill switch và runbook.
11. Credential, DNS hoặc manual action còn cần người dùng thực hiện, nếu có.

Hãy bắt đầu bằng audit repository và baseline. Lập kế hoạch có thể theo dõi, thực hiện remediation an toàn, sau đó triển khai production cho `deb2b.id.vn` khi release gate cho phép. Linh hoạt điều chỉnh giải pháp theo bằng chứng từ codebase, nhưng không được hạ các tiêu chuẩn an toàn cốt lõi hoặc che giấu phần chưa được xác minh.
