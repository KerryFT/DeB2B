# AR Operations Agent — Kế hoạch triển khai

## 1. Định nghĩa sản phẩm

Không xây một bot nhắc nợ đơn thuần. Email nhắc nợ theo ngày đến hạn đã là tính năng phổ biến trong MISA và nhiều phần mềm kế toán.

Sản phẩm được định nghĩa là:

> **AR Operations Agent:** phát hiện vì sao một hóa đơn chưa được thanh toán, tìm tài liệu còn thiếu, điều phối người xử lý, chuẩn bị follow-up và theo dõi đến khi thu được tiền.

Lời hứa sản phẩm:

> **Không chỉ nhắc nợ — tìm và gỡ nguyên nhân khiến hóa đơn chưa được thanh toán.**

Pain point này gắn trực tiếp với dòng tiền. Khảo sát Atradius cho thấy thanh toán trễ ảnh hưởng khoảng 36% hóa đơn B2B tại Việt Nam; thời gian thu tiền kéo dài trung bình một tháng sau hạn. Khoảng 36% doanh nghiệp cho rằng nguyên nhân là sự kém hiệu quả trong quy trình hành chính của khách hàng.

Nguồn tham khảo: [Atradius Vietnam Payment Practices](https://atradius.us/knowledge-and-research/reports/b2b-payment-practices-trends-vietnam-2024)

---

## 2. Phạm vi MVP

### 2.1. ICP mặc định

Doanh nghiệp B2B dịch vụ và phân phối có:

- 100–5.000 hóa đơn mỗi tháng.
- Thời hạn thanh toán 15–90 ngày.
- Dùng Excel, MISA hoặc một phần mềm kế toán phổ biến.
- Email là kênh giao tiếp chính thức.
- Hồ sơ thanh toán gồm hợp đồng, PO, hóa đơn, biên bản giao hàng/nghiệm thu và đề nghị thanh toán.

Không chọn ngành xây dựng trong MVP đầu tiên vì nghiệp vụ khối lượng và hồ sơ nghiệm thu phức tạp hơn đáng kể.

### 2.2. Năm blocker MVP phải xử lý

1. Chưa gửi đủ hồ sơ.
2. Hóa đơn hoặc chứng từ sai thông tin.
3. Khách hàng chưa xác nhận nghiệm thu/giao hàng.
4. Hóa đơn đang tranh chấp.
5. Khách hàng đã hứa thanh toán nhưng chưa thực hiện.

### 2.3. Ngoài phạm vi MVP

- Khởi kiện và tư vấn pháp lý.
- Chấm điểm tín dụng.
- Tự thương lượng giảm nợ.
- Tự thay đổi điều khoản thanh toán.
- Tự gửi email gây áp lực.
- Thu hồi nợ từ người tiêu dùng cá nhân.
- Tích hợp trực tiếp với mọi ngân hàng.

---

## 3. Luồng nghiệp vụ

```text
MISA/Excel/ERP ─┐
Email ──────────┼─> Ingestion ─> Chuẩn hóa dữ liệu ─> AR Case Graph
PDF/ảnh ────────┤                                      │
Bank CSV ───────┘                                      ▼
                                             Blocker & Risk Engine
                                                       │
                                    ┌──────────────────┼────────────────┐
                                    ▼                  ▼                ▼
                              Thiếu hồ sơ       Có tranh chấp      Đã quá hạn
                                    │                  │                │
                                    ▼                  ▼                ▼
                              Tạo task nội bộ    Tóm tắt vấn đề    Soạn follow-up
                                    └──────────────────┼────────────────┘
                                                       ▼
                                                Người dùng duyệt
                                                       ▼
                                                Email/Zalo/CRM
                                                       ▼
                                                Theo dõi phản hồi
                                                       ▼
                                             Cam kết trả / Đã trả / Escalate
```

### 3.1. Ví dụ end-to-end

1. MISA phát sinh hóa đơn 120 triệu, hạn thanh toán ngày 30/8.
2. Agent đọc hợp đồng và xác định điều kiện thanh toán gồm hóa đơn hợp lệ, biên bản nghiệm thu, đề nghị thanh toán và thời hạn 30 ngày kể từ khi khách nhận đủ hồ sơ.
3. Agent tìm trong email và phát hiện hóa đơn cùng đề nghị thanh toán đã gửi, nhưng biên bản nghiệm thu chưa có chữ ký khách hàng.
4. Case được gắn blocker `MISSING_SIGNED_ACCEPTANCE`.
5. Agent giao task cho account manager xin chữ ký.
6. Khi file ký được gửi qua email, agent kiểm tra số hợp đồng, ngày, giá trị và bên ký; sau đó gắn tài liệu vào invoice.
7. Trạng thái chuyển sang `DOCUMENT_SET_COMPLETE`.
8. Agent soạn email gửi lại bộ hồ sơ cho AP của khách hàng.
9. Người dùng duyệt; hệ thống gửi hoặc tạo Gmail draft.
10. Khách hàng trả lời dự kiến thanh toán ngày 12/9.
11. Agent ghi nhận cam kết và đặt timer ngày 12/9.
12. Nếu chưa thấy giao dịch ngân hàng, agent chuẩn bị follow-up tiếp theo.
13. Khi import sao kê và ghép được khoản 120 triệu, case chuyển sang `PAID`.

---

## 4. Kiến trúc dữ liệu cốt lõi

Không để agent đọc lại toàn bộ email và tài liệu từ đầu ở mỗi lần chạy. Dữ liệu lộn xộn phải được chuyển thành mô hình nghiệp vụ ổn định.

### 4.1. Entity chính

| Entity | Nội dung |
|---|---|
| `Customer` | Pháp nhân khách hàng, MST, địa chỉ |
| `Contact` | Kế toán phải trả, người mua hàng, người phê duyệt |
| `Contract` | Hợp đồng và phụ lục |
| `PaymentTerm` | Điều kiện và thời hạn thanh toán |
| `Invoice` | Số hóa đơn, ngày, số tiền, hạn thanh toán |
| `RequiredDocument` | Tài liệu cần có để được thanh toán |
| `Document` | Hợp đồng, PO, biên bản, hóa đơn, đề nghị thanh toán |
| `EvidenceSpan` | Trang, vùng hoặc đoạn nguồn chứng minh một trường dữ liệu |
| `PaymentCase` | Toàn bộ case thu tiền của một hoặc nhiều hóa đơn |
| `Blocker` | Nguyên nhân đang cản thanh toán |
| `PromiseToPay` | Cam kết thanh toán của khách |
| `Communication` | Email, ghi chú cuộc gọi, tin nhắn |
| `Task` | Công việc nội bộ hoặc bên ngoài |
| `Approval` | Quyết định duyệt gửi, sửa hay escalation |
| `ActionLog` | Nhật ký bất biến về mọi hành động |

### 4.2. State machine

```text
IMPORTED
  ├─> DOCUMENT_INCOMPLETE
  ├─> READY_TO_SUBMIT
  └─> SUBMITTED
         ├─> ACCEPTED
         ├─> DISPUTED
         ├─> CORRECTION_REQUIRED
         └─> NO_RESPONSE

ACCEPTED
  ├─> NOT_DUE
  ├─> DUE
  ├─> OVERDUE
  └─> PROMISE_TO_PAY

PROMISE_TO_PAY
  ├─> PAID
  └─> PROMISE_BROKEN

DISPUTED / PROMISE_BROKEN
  ├─> ESCALATED
  ├─> RESOLVED
  └─> CLOSED
```

State do workflow engine quản lý. LLM chỉ đề xuất event hoặc blocker, không trực tiếp chỉnh trạng thái tùy ý.

---

## 5. Kiến trúc AI

Không dùng một “super agent” đọc tất cả rồi tự quyết định. Kiến trúc phù hợp là hệ thống lai:

- Code và rule cho tiền, ngày tháng, trạng thái.
- Document AI cho trích xuất.
- LLM cho hiểu ngôn ngữ, hợp đồng và email.
- Workflow engine cho timer, retry và human approval.
- Con người duyệt trước hành động có ảnh hưởng bên ngoài.

### 5.1. Lớp deterministic extraction

Dùng parser thông thường trước AI:

- PDF có text layer: đọc text trực tiếp.
- XLSX/CSV: đọc cell.
- XML hóa đơn điện tử: parse XML.
- Email: đọc header, body, thread ID và attachment.
- Ngày, số tiền, MST, số hóa đơn: regex và parser chuẩn hóa.

Không dùng LLM để cộng tiền, so ngày hoặc tính số ngày quá hạn.

### 5.2. Lớp OCR và layout

Đối với scan/ảnh:

- Chỉnh xoay, perspective và độ tương phản.
- OCR tiếng Việt.
- Nhận diện bảng, tiêu đề, chữ ký và vùng thông tin.
- Giữ bounding box để truy ngược nguồn.

Khuyến nghị:

- Docling cho PDF có cấu trúc tốt.
- PaddleOCR PP-StructureV3 cho ảnh và scan tiếng Việt.
- Vision model làm fallback cho tài liệu khó.
- Không dùng vision model cho mọi trang vì chậm, đắt và khó kiểm tra.

Nguồn: [PaddleOCR PP-StructureV3](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PP-StructureV3.en.md), [Docling pipeline](https://docling-project.github.io/docling/reference/pipeline_options/)

### 5.3. Structured extraction bằng LLM

LLM nhận text/layout đã parse, ảnh crop vùng quan trọng, schema tài liệu và danh sách field bắt buộc. Output phải dùng JSON Schema.

Ví dụ:

```json
{
  "document_type": "acceptance_record",
  "contract_number": "HD-2026-014",
  "invoice_numbers": ["0000125"],
  "signed_date": "2026-08-22",
  "total_amount": 120000000,
  "parties": [
    {
      "name": "Công ty A",
      "tax_id": "0101234567",
      "role": "buyer"
    }
  ],
  "signature_status": {
    "buyer_signed": true,
    "seller_signed": true
  },
  "evidence": [
    {
      "field": "signed_date",
      "page": 3,
      "text": "Ngày 22 tháng 08 năm 2026"
    }
  ]
}
```

### 5.4. Matching và reconciliation

Không dùng semantic search đơn thuần. Quy trình matching:

1. Blocking theo tenant.
2. MST/người mua.
3. Số hóa đơn, hợp đồng hoặc PO.
4. Số tiền và currency.
5. Khoảng ngày.
6. Fuzzy text matching.
7. Embedding/LLM chỉ xử lý phần còn mơ hồ.

Ví dụ:

```text
match_score =
  0.35 × invoice_number_match
+ 0.25 × tax_id_match
+ 0.20 × amount_match
+ 0.10 × contract_match
+ 0.10 × date_proximity
```

Quy tắc ban đầu:

- `≥0,95`: có thể tự ghép.
- `0,75–0,95`: đưa vào review.
- `<0,75`: không ghép.

Không dùng confidence do LLM tự tuyên bố làm confidence cuối cùng. Ngưỡng phải được hiệu chỉnh trên tập eval.

### 5.5. Blocker classification

```text
MISSING_DOCUMENT
MISSING_SIGNATURE
INCORRECT_INVOICE
PO_MISMATCH
AMOUNT_MISMATCH
CUSTOMER_DISPUTE
PAYMENT_PROCESSING
PROMISE_TO_PAY
NO_RESPONSE
CUSTOMER_CASHFLOW
INTERNAL_APPROVAL_PENDING
UNKNOWN
```

Agent được phép:

- Tìm tài liệu.
- Phân loại blocker.
- Tạo task.
- Đặt timer.
- Soạn email.
- Đề xuất escalation.
- Cập nhật ghi chú sau khi được duyệt.

Agent không được phép:

- Tự gửi email trong phiên bản đầu.
- Thay đổi thông tin ngân hàng.
- Chấp nhận giảm giá/giảm nợ.
- Xóa hoặc điều chỉnh hóa đơn.
- Đe dọa pháp lý.
- Chuyển case sang pháp lý.
- Đánh dấu đã thanh toán khi chưa có bằng chứng.

---

## 6. Cấu hình LLM đa provider

> **Lưu ý bắt buộc:** hệ thống phải hỗ trợ nhiều LLM provider ngay từ lớp abstraction, tối thiểu gồm **OpenAI, Google Gemini và Anthropic**. Không để business logic, schema nghiệp vụ hoặc workflow phụ thuộc trực tiếp vào SDK của một hãng.

### 6.1. Nguyên tắc thiết kế

- Mỗi provider được đóng gói bằng một adapter chung.
- Prompt template và JSON Schema thuộc application, không thuộc provider.
- Model được chọn theo capability, latency, chi phí và data policy.
- Có primary, fallback và retry policy theo từng task.
- Không fallback âm thầm đối với tác vụ nhạy cảm; phải ghi provider/model thực tế vào audit log.
- Output của mọi provider phải qua cùng validation layer.
- Provider không hỗ trợ schema nghiêm ngặt phải được bọc bằng validation và repair có giới hạn.
- Không truyền toàn bộ case khi task chỉ cần một phần dữ liệu.

### 6.2. Interface chung

```python
class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        task_type: str,
        messages: list[Message],
        schema: dict,
        model: str,
        timeout_seconds: int,
        metadata: dict,
    ) -> StructuredLLMResult:
        ...

    async def generate_text(
        self,
        *,
        task_type: str,
        messages: list[Message],
        model: str,
        timeout_seconds: int,
        metadata: dict,
    ) -> TextLLMResult:
        ...
```

Kết quả chuẩn hóa:

```python
class StructuredLLMResult(BaseModel):
    provider: str
    model: str
    data: dict
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int
    request_id: str | None
    schema_valid: bool
    finish_reason: str | None
```

### 6.3. Cấu hình gợi ý

```yaml
llm:
  default_provider: openai

  providers:
    openai:
      enabled: true
      api_key_env: OPENAI_API_KEY
      models:
        fast: gpt-5.6-luna
        balanced: gpt-5.6-terra
        reasoning: gpt-5.6-sol

    gemini:
      enabled: true
      api_key_env: GEMINI_API_KEY
      models:
        fast: ${GEMINI_FAST_MODEL}
        balanced: ${GEMINI_BALANCED_MODEL}
        reasoning: ${GEMINI_REASONING_MODEL}

    anthropic:
      enabled: true
      api_key_env: ANTHROPIC_API_KEY
      models:
        fast: ${ANTHROPIC_FAST_MODEL}
        balanced: ${ANTHROPIC_BALANCED_MODEL}
        reasoning: ${ANTHROPIC_REASONING_MODEL}

  routes:
    document_classification:
      tier: fast
      primary: openai
      fallbacks: [gemini, anthropic]
      timeout_seconds: 20

    email_classification:
      tier: fast
      primary: openai
      fallbacks: [anthropic, gemini]
      timeout_seconds: 20

    payment_term_extraction:
      tier: balanced
      primary: openai
      fallbacks: [anthropic, gemini]
      timeout_seconds: 45

    dispute_analysis:
      tier: reasoning
      primary: openai
      fallbacks: [anthropic, gemini]
      timeout_seconds: 90

    followup_drafting:
      tier: fast
      primary: openai
      fallbacks: [anthropic, gemini]
      timeout_seconds: 30
```

Tên model của Gemini và Anthropic nên để qua biến môi trường hoặc config deployment vì danh mục model thay đổi theo thời gian và theo tài khoản.

### 6.4. Routing policy

| Tác vụ | Cách xử lý |
|---|---|
| Regex, tính tuổi nợ, kiểm tra số tiền | Code, không dùng LLM |
| Phân loại tài liệu/email | Fast tier |
| Viết follow-up chuẩn | Fast tier |
| Điều khoản thanh toán phức tạp | Balanced tier |
| Tranh chấp nhiều tài liệu | Reasoning tier |
| Quyết định gửi/điều chỉnh công nợ | Con người |

### 6.5. Fallback policy

Chỉ fallback khi:

- Provider timeout.
- Rate limit.
- Lỗi 5xx.
- Output không hợp lệ sau tối đa một lần repair.
- Provider từ chối xử lý vì lỗi kỹ thuật không liên quan nội dung.

Không fallback khi:

- Input vi phạm policy.
- Schema hoặc dữ liệu đầu vào sai.
- Business rule không cho phép hành động.
- Case cần human review.

Mỗi lần fallback phải lưu:

```text
task_id
original_provider
original_model
failure_class
fallback_provider
fallback_model
latency
token_usage
schema_validation_result
```

### 6.6. Model evaluation

Chạy cùng bộ eval cho tất cả provider. Không chọn model chỉ dựa trên benchmark công khai.

So sánh:

- Exact match cho ngày, số tiền, MST, số hóa đơn.
- Accuracy/F1 phân loại blocker.
- Tỷ lệ JSON hợp lệ.
- Evidence faithfulness.
- Hallucination rate.
- Draft compliance.
- Latency p50/p95.
- Chi phí trên mỗi case hoàn tất.

Provider/model chỉ được đưa vào production route khi vượt ngưỡng của task tương ứng.

---

## 7. Workflow engine

Một case công nợ có thể tồn tại 30–120 ngày, phải chờ con người, tài liệu, ngày đến hạn, retry API và tiếp tục sau khi server restart.

Khuyến nghị dùng **Temporal Cloud**. Mỗi `PaymentCase` là một durable workflow.

```text
Start case
→ Collect required documents
→ Wait for missing document or deadline
→ Validate document
→ Prepare submission
→ Wait for approval
→ Send
→ Wait for customer response
→ Parse response
→ Wait until promised payment date
→ Reconcile payment
→ Close or escalate
```

LLM/API calls đặt trong Temporal Activities. Activities phải idempotent và có retry policy.

Nguồn: [Temporal documentation](https://docs.temporal.io/)

### 7.1. Idempotency

```text
idempotency_key =
tenant_id
+ case_id
+ action_type
+ document_version
+ approval_id
```

Nếu webhook hoặc worker chạy lại, cùng key không được tạo thêm email hay action bên ngoài.

---

## 8. Tích hợp hệ thống

### 8.1. MVP: Gmail + Excel/CSV

Gmail API hỗ trợ push notification qua Cloud Pub/Sub. Sau notification, dùng `history.list` để lấy thay đổi. Cần gia hạn `watch` định kỳ và có job đồng bộ dự phòng vì push có thể trễ hoặc bị mất.

Nguồn: [Gmail API push notifications](https://developers.google.com/workspace/gmail/api/guides/push)

MVP nên:

1. Cho người dùng tạo label `AR-Agent`.
2. Chỉ đọc email/thread được gắn label.
3. Agent tạo Gmail draft.
4. Người dùng mở Gmail và gửi.

File import tối thiểu:

```text
invoice_number
customer_code
customer_name
tax_id
issue_date
due_date
amount
currency
outstanding_amount
account_owner
status
```

### 8.2. MISA

Thứ tự triển khai:

1. CSV import/export.
2. Đọc dữ liệu qua MISA API.
3. Ghi note/status trở lại nếu API hỗ trợ.
4. Không phụ thuộc hoàn toàn vào API MISA trong MVP.

Nguồn: [MISA meInvoice API đầu vào](https://www.misa.vn/154997/tai-lieu-open-api-tich-hop-hoa-don-dien-tu-misa-meinvoice-dau-vao/), [MISA API đầu ra](https://www.misa.vn/154989/tai-lieu-open-api-tich-hop-hoa-don-dien-tu-misa-meinvoice-dau-ra/)

### 8.3. Outlook

Đưa Outlook vào sau Gmail. Microsoft Graph hỗ trợ webhook nhưng subscription phải được gia hạn và cần xử lý lifecycle notification.

Nguồn: [Microsoft Graph webhooks](https://learn.microsoft.com/en-us/graph/change-notifications-delivery-webhooks)

### 8.4. Zalo

Zalo OA/ZBS chỉ nên triển khai sau khi workflow email ổn định.

- Email là kênh hồ sơ chính thức.
- Zalo dùng nhắc người phụ trách hoặc gửi template đã phê duyệt.
- Không gửi chi tiết công nợ vào nhóm không xác thực.

Nguồn: [Zalo Developers](https://developers.zalo.me/docs)

### 8.5. Ngân hàng

MVP dùng CSV sao kê và matching theo số tiền, nội dung chuyển khoản, ngày và khách hàng. Không bank scraping và không yêu cầu mật khẩu Internet Banking.

---

## 9. Stack kỹ thuật

| Thành phần | Công nghệ |
|---|---|
| Frontend | Next.js + TypeScript |
| API | FastAPI + Python |
| Workflow | Temporal Cloud + Python SDK |
| Database | PostgreSQL |
| Vector search | `pgvector`, chỉ cho clause/email retrieval |
| File storage | Google Cloud Storage hoặc S3 |
| Email events | Google Pub/Sub |
| Document parsing | Docling + PaddleOCR |
| AI gateway | Provider-neutral LLM adapters |
| LLM providers | OpenAI, Gemini, Anthropic |
| Authentication | WorkOS/Auth0/Supabase Auth |
| Secrets | Cloud Secret Manager |
| Observability | OpenTelemetry + Sentry |
| Backend deployment | Cloud Run, Cloud SQL, GCS tại Singapore |
| Frontend hosting | Vercel hoặc Cloud Run |

### 9.1. Không để framework agent sở hữu business state

State công nợ nằm trong:

- PostgreSQL.
- Temporal workflow.
- Event log.

Framework agent chỉ xử lý reasoning/tool call ngắn hạn. Không dùng LangChain/LangGraph làm nguồn sự thật nghiệp vụ.

### 9.2. Không dùng multi-agent trong MVP

Thay vì nhiều agent trò chuyện với nhau, dùng một orchestrator và các task chuyên biệt:

```text
classify_document()
extract_invoice()
extract_payment_terms()
match_document()
classify_blocker()
summarize_thread()
draft_followup()
```

---

## 10. Bảo mật và kiểm soát rủi ro

### 10.1. Tenant isolation

Mọi bảng có `tenant_id`. Bật PostgreSQL Row-Level Security cho dữ liệu tenant.

Nguồn: [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)

### 10.2. Quy tắc bảo mật

- Mã hóa file khi lưu và truyền.
- OAuth token được mã hóa riêng.
- Không log nội dung hợp đồng/email vào application log.
- File có retention policy cấu hình được.
- Audit log không cho người dùng sửa.
- Không dùng dữ liệu khách hàng để fine-tune nếu chưa có đồng ý.
- Cho phép export và xóa dữ liệu.
- Tách development/staging/production.
- Dùng dữ liệu giả hoặc ẩn danh trong staging.
- Ghi provider/model thực tế cho mọi lần gọi LLM.
- Cho phép cấu hình provider theo tenant nếu khách hàng có yêu cầu data policy riêng.

### 10.3. Chống prompt injection

Email và attachment là dữ liệu không đáng tin cậy:

- Tách system policy khỏi document content.
- Không cho nội dung email tự tạo tool call.
- Tool gửi email kiểm tra recipient whitelist.
- Không cho model sửa bank account.
- Gửi file phải qua policy engine.
- Mọi external action có approval ID còn hiệu lực.
- Kiểm tra lại dữ liệu ngay trước lúc gửi.

---

## 11. Màn hình MVP

### Dashboard

- Tổng outstanding.
- Due trong 7 ngày.
- Overdue.
- Blocked by documents.
- Promise broken.
- Giá trị đã thu trong kỳ.

### Case queue

- Giá trị.
- Tuổi nợ.
- Blocker.
- Người phụ trách.
- Lần tương tác gần nhất.
- Next action.

### Case detail

- Timeline.
- Hóa đơn.
- Điều khoản thanh toán.
- Bộ hồ sơ.
- Email liên quan.
- Blocker.
- Task.
- Promise to pay.
- Bằng chứng nguồn.

### Approval inbox

- Draft email.
- Người nhận.
- Tài liệu đính kèm.
- Lý do gửi.
- Nguồn dữ liệu.
- Approve/Edit/Reject.

### Settings

- Import mapping.
- Email connector.
- LLM provider và model routing.
- Template giọng điệu.
- Escalation policy.
- User role.
- Data retention.

---

## 12. Kế hoạch phát triển sáu tuần

### Tuần 1 — Foundation và ingestion

- Thiết kế canonical schema.
- Thiết lập Postgres, object storage và authentication.
- Import Excel/CSV công nợ.
- Upload tài liệu.
- Gmail OAuth và đọc thread được gắn label.
- Event log và tenant isolation.
- Tạo LLM provider interface và config loader.

**Kết quả:** tạo được `PaymentCase` từ CSV và email; có thể đổi provider qua config.

### Tuần 2 — Document intelligence

- Document classifier.
- PDF text extraction.
- PaddleOCR fallback.
- Structured extraction cho hợp đồng, PO, hóa đơn, biên bản và đề nghị thanh toán.
- EvidenceSpan theo trang và đoạn nguồn.
- Cache theo file hash.
- Adapter OpenAI, Gemini và Anthropic.

**Kết quả:** tài liệu được chuyển thành dữ liệu có cấu trúc và kiểm tra được trên nhiều provider.

### Tuần 3 — Matching và blocker engine

- Ghép document–invoice–customer.
- Tính due date.
- Rule engine cho năm blocker MVP.
- Required-document matrix.
- Confidence calibration.
- Manual review queue.

**Kết quả:** hệ thống cho biết từng hóa đơn đang thiếu gì.

### Tuần 4 — Durable workflow

- Temporal workflows.
- Timer theo due date và promise date.
- Retry/idempotency.
- Task assignment.
- Approval state.
- Escalation rules.
- Case timeline.
- Provider fallback và audit log.

**Kết quả:** case chạy qua nhiều ngày mà không mất trạng thái.

### Tuần 5 — Communication agent

- Phân loại email phản hồi.
- Tóm tắt thread.
- Phát hiện promise to pay.
- Draft follow-up theo blocker.
- Tạo Gmail draft.
- Approval inbox.
- Recipient và attachment guardrail.

**Kết quả:** người dùng duyệt và gửi follow-up trong vài giây.

### Tuần 6 — Reconciliation, eval và hardening

- Import bank CSV.
- Ghép payment–invoice.
- Dashboard DSO/outstanding.
- Audit log.
- Error monitoring.
- Security review.
- Cross-provider eval.
- Load test.
- Backup/restore.
- Production deployment.

**Kết quả:** MVP xử lý vòng đời từ invoice đến paid.

---

## 13. Bộ eval kỹ thuật

Tập benchmark tối thiểu:

- 100 hóa đơn.
- 50 hợp đồng/phụ lục.
- 100 PO/biên bản.
- 100 email thread.
- 50 case tranh chấp.
- 50 case promise to pay.
- 50 giao dịch ngân hàng.

### Ngưỡng MVP

| Tác vụ | Ngưỡng |
|---|---:|
| Phân loại tài liệu | ≥98% |
| MST/số hóa đơn/số tiền | ≥99% trên file rõ |
| Trích xuất điều khoản thanh toán | ≥95% exact/acceptable |
| Ghép document–invoice | ≥97% precision |
| Phân loại blocker | ≥90% macro-F1 |
| Phát hiện promise date | ≥95% |
| Email sai người nhận | 0 |
| Gửi email trùng | 0 |
| Tự thay đổi dữ liệu tài chính | 0 |
| Trường trọng yếu có evidence | 100% |

Eval phải chạy theo ma trận:

```text
task × provider × model × prompt_version × dataset_version
```

Không thay model production nếu chưa vượt regression suite.

---

## 14. Roadmap sau MVP

### V1 — tuần 7–10

- MISA API.
- Outlook.
- Zalo OA notification.
- Bank reconciliation nâng cao.
- Customer-specific payment rules.
- Bulk approval.
- Aging forecast.
- Role-based access chi tiết.
- Dashboard chi phí/chất lượng theo LLM provider.

### V2

- Tự gửi email rủi ro thấp sau khi đã xây trust.
- Gợi ý chiến lược escalation.
- Theo dõi dispute root cause.
- Dự báo probability-to-pay.
- Cashflow forecast.
- Customer payment behavior profile.
- Benchmark hiệu quả theo account manager.

### Không làm trước V2

- Tự gọi điện bằng voice AI.
- Tự thương lượng.
- Tự đề nghị discount.
- Tự gửi legal notice.
- Multi-agent.
- Fine-tuning.
- Banking API phức tạp.
- Xây CRM hoặc accounting system riêng.

---

## 15. Nhân lực tối thiểu

- 1 backend/AI engineer.
- 1 full-stack engineer.
- 1 document/ML engineer bán thời gian.
- 1 product/QA nghiệp vụ bán thời gian.

Nếu chỉ có hai người:

- Gmail draft thay vì UI gửi email.
- CSV thay MISA API.
- Bank CSV thay banking API.
- Chỉ hỗ trợ PDF, XLSX và email.
- Chỉ hỗ trợ một tenant ở pilot đầu.
- Bỏ Zalo và Outlook.
- Chỉ làm năm blocker chính.
- Vẫn giữ LLM provider abstraction, nhưng có thể chỉ bật một provider trong deployment đầu tiên.

---

## 16. Quyết định kiến trúc cuối cùng

> **Event-driven, evidence-first, deterministic core, provider-neutral LLM at the edges, Temporal for orchestration, human approval before external action.**

Cụ thể:

- PostgreSQL là nguồn sự thật.
- Temporal sở hữu vòng đời case.
- Rule engine sở hữu tiền, ngày và trạng thái.
- Document AI chuyển file thành schema có evidence.
- LLM hiểu hợp đồng, email và soạn nội dung.
- LLM gateway hỗ trợ OpenAI, Gemini và Anthropic.
- Người dùng sở hữu quyết định gửi và escalation.

Thiết kế này đáp ứng yêu cầu phát triển nhanh nhưng không khóa sản phẩm vào một LLM provider, đồng thời duy trì độ tin cậy cần thiết cho nghiệp vụ liên quan đến tiền và quan hệ khách hàng.
