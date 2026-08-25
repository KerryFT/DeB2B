# DeB2B — AI Agent cho vận hành công nợ B2B

DeB2B là nền tảng **Accounts Receivable Operations** giúp đội tài chính theo dõi công nợ,
đối soát thanh toán, phân tích rủi ro thu tiền và tạo follow-up draft có kiểm soát. AI Agent sử dụng
dữ liệu và evidence của từng hồ sơ để đưa ra đề xuất; mọi hành động ảnh hưởng ra bên ngoài đều đi
qua bước phê duyệt của con người.

- Web production: [https://app.deb2b.id.vn](https://app.deb2b.id.vn)
- API production: [https://api.deb2b.id.vn](https://api.deb2b.id.vn)
- API health: [https://api.deb2b.id.vn/live](https://api.deb2b.id.vn/live)
- Nhánh triển khai: `main`

> Bản deploy công khai sử dụng profile `portfolio`: chỉ dùng dữ liệu synthetic/anonymized, không tự
> gửi email và không được xem là topology production đầy đủ cho dữ liệu khách hàng thật.

## AI Agent hoạt động như thế nào?

AI không chỉ là một thành phần giao diện. Luồng inference thật chạy qua Google Gemini:

1. Người dùng chọn một payment case trong **AI Agent Workbench**.
2. API truy vấn customer, invoice, blocker và evidence thuộc đúng tenant.
3. Gemini trả về JSON theo schema cho trước: tóm tắt, risk, blocker, hành động tiếp theo, confidence
   và danh sách evidence ID.
4. Backend từ chối kết quả nếu model tham chiếu evidence không tồn tại.
5. Khi người dùng yêu cầu follow-up, Gemini tạo subject/body nhưng chỉ lưu thành approval
   `PENDING` có thời hạn và content hash.
6. Người có quyền approve/reject nội dung. Portfolio chỉ cho phép tạo Outlook draft tới recipient
   trong allowlist; gửi email tự động luôn bị tắt.

| Nhiệm vụ | Model mặc định | Cơ chế an toàn |
|---|---|---|
| Phân tích case | `gemini-3.7-flash` | Timeout 20 giây, fallback sang fast model |
| Soạn follow-up | `gemini-3.5-flash-lite` | Structured output, evidence validation |
| Thực thi hành động | Deterministic workflow | Human approval, content hash, expiry |

AI runtime ghi lại provider, model, prompt version, latency, token usage, schema validity và trạng
thái fallback. Nội dung tài liệu được đặt trong ranh giới untrusted-data để giảm prompt injection.
Xem thêm [AI Agent runbook](docs/AI_AGENT_RUNBOOK.md).

## Tính năng chính

### Vận hành công nợ

- Hồ sơ công nợ theo customer/invoice, trạng thái và blocker.
- Import CSV/XLSX tương thích MISA với preview và idempotency.
- Đối soát ngân hàng, allocation/reversal và payment rules có version.
- Approval inbox: xem chi tiết, sửa, approve, reject và bulk approve.
- Microsoft OAuth, Outlook delta sync và tạo draft có allowlist.
- RBAC theo permission, tenant isolation và audit trail.

### Phân tích và hỗ trợ quyết định

- Probability-to-pay tại một thời điểm.
- Aging và probabilistic cash-flow forecast.
- Customer payment behavior và dispute root-cause analytics.
- Evidence-backed escalation recommendation và feedback.
- Privacy-aware team benchmark.
- LLM cost/quality analytics.

### Guardrails

- Money, date, trạng thái và reconciliation do deterministic domain logic quản lý.
- AI chỉ đề xuất, không tự sửa số tiền hoặc trạng thái case.
- Approval gắn với exact content hash và có thời hạn.
- Global kill switch bật mặc định; external delivery tắt mặc định.
- Portfolio fail-closed với upload/OCR, Temporal, MISA API, Outlook webhook và email send.
- Production/portfolio config từ chối khởi động khi thiếu secret hoặc bật tổ hợp flag không an toàn.

## Kiến trúc

```text
Next.js 16 / React 19 (Vercel)
              │ HTTPS + session cookie + CSRF
              ▼
FastAPI / Pydantic / SQLAlchemy (Render)
    ├── Deterministic domain services
    ├── AI Agent orchestration ──► Google Gemini
    ├── Microsoft OAuth / Outlook draft
    ├── MISA-compatible import
    └── Metrics, audit and LLM telemetry
              │
              ▼
        PostgreSQL / Neon
```

Các boundary chính:

- `backend/domain`: nghiệp vụ thuần, deterministic và testable.
- `backend/application`: use case, approval, agent orchestration và ports.
- `backend/infrastructure`: database, provider Gemini, connector và runtime config.
- `services/api`: FastAPI routes, auth, permission và API contracts.
- `services/worker`: Temporal/document worker cho topology đầy đủ.
- `apps/web`: Next.js App Router, giao diện nghiệp vụ và AI Agent Workbench.
- `migrations`: Alembic schema migrations.
- `tests`: unit, contract, integration, workflow, security, E2E và load tests.

## Công nghệ

| Layer | Thành phần |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript 5.9, TanStack Query, Zod |
| Backend | Python 3.13, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic |
| AI | Google Gen AI SDK, schema-constrained output, provider-neutral port |
| Workflow | Temporal (full topology), deterministic application services |
| Data | PostgreSQL 18 local, Neon cho portfolio |
| Storage/OCR | S3-compatible/MinIO, ClamAV, PaddleOCR/Docling (full topology) |
| Deploy | Vercel frontend, Render Docker API, Neon PostgreSQL |
| Quality | Ruff, strict mypy, Pytest, ESLint, TypeScript, Vitest |

## Yêu cầu phát triển

- Python `>=3.12,<3.14` — khuyến nghị Python 3.13.
- Node.js `>=24,<25`.
- pnpm `10.15.0` qua Corepack.
- `uv` để quản lý Python dependencies.
- Docker Desktop/Engine và Docker Compose cho PostgreSQL, Temporal, MinIO, ClamAV.

## Chạy local

### 1. Cài dependencies

```bash
cp .env.example .env
make bootstrap
```

Trên Windows PowerShell:

```powershell
Copy-Item .env.example .env
corepack enable
pnpm install --frozen-lockfile
uv sync --all-groups
```

### 2. Khởi động infrastructure và database

```bash
docker compose up -d postgres temporal temporal-ui minio clamav
uv run alembic upgrade head
uv run python -m tools.seed_demo
```

### 3. Chạy API và web

Terminal API:

```bash
uv run uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal web:

```bash
pnpm dev
```

Mở `http://localhost:3000`. Development mặc định dùng dev auth và fake LLM nên không cần external
credential. API docs có tại `http://localhost:8000/docs`.

## Bật Gemini local

Không commit `.env` hoặc API key. Cấu hình:

```dotenv
LLM_DEFAULT_PROVIDER=gemini
GEMINI_API_KEY=<your-secret>
GEMINI_MODEL_FAST=gemini-3.5-flash-lite
GEMINI_MODEL_REASONING=gemini-3.7-flash
LLM_TIMEOUT_SECONDS=20
```

Khởi động lại API, đăng nhập web và mở `/agent`. Endpoint `/api/v1/ai/status` cần authenticated
session; hệ thống không công khai trạng thái/provider config cho anonymous client.

## Kiểm thử và quality gates

```bash
# Backend
uv run ruff check backend services tests
uv run mypy backend services
uv run pytest

# Frontend
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Các nhóm test riêng:

```bash
make test-unit
make test-contract
make test-integration
make test-workflow
```

Integration/workflow tests cần các service Docker tương ứng. Test AI contract dùng fake/mock client và
không tiêu thụ Gemini API key.

## User flow UAT đề xuất

### 1. Import đến AI analysis

1. Đăng nhập Microsoft.
2. Import file synthetic ở **Nhập dữ liệu** và xác nhận preview.
3. Mở case vừa tạo trong **Hồ sơ công nợ**.
4. Chuyển sang **AI Agent**, chọn case và bấm **Phân tích hồ sơ**.
5. Đối chiếu summary, risk, recommendation và evidence với case gốc.

Kỳ vọng: import lại không tạo duplicate; AI không tự thay đổi invoice/case.

### 2. AI draft đến approval

1. Sau khi phân tích, nhập recipient thuộc `PORTFOLIO_ALLOWED_EMAILS`.
2. Tạo draft và mở **Phê duyệt**.
3. Kiểm tra/sửa nội dung, sau đó approve hoặc reject.
4. Xác nhận trạng thái, content hash và feedback cập nhật.

Kỳ vọng: portfolio không gửi email; recipient ngoài allowlist bị trả về 403.

### 3. Bulk approval và stale-content protection

1. Tạo ít nhất hai pending approval.
2. Lọc theo trạng thái, chọn nhiều item và bulk approve.
3. Thử approve nội dung đã hết hạn hoặc bị thay đổi.

Kỳ vọng: thao tác hợp lệ có phản hồi rõ; stale/expired content bị từ chối.

### 4. Analytics và escalation

1. Mở forecast, probability, cash flow, customer behavior và disputes.
2. Kiểm tra escalation recommendation, gửi accept/reject feedback.
3. Mở **Chất lượng AI** để xem telemetry inference.

Kỳ vọng: analytics hiển thị theo tenant; feedback lưu được; telemetry không chứa secret/raw PII.

## Deployment từ `main`

### Frontend — Vercel

- Project root: `apps/web`.
- Config: `apps/web/vercel.json`.
- Production variable: `NEXT_PUBLIC_API_URL=https://api.deb2b.id.vn`.
- Custom domain: `app.deb2b.id.vn`.

### Backend — Render

- Blueprint: `render.yaml`.
- Dockerfile: `services/api/Dockerfile`.
- Service: `deb2b-api`, branch `main`.
- Health check: `/live`.
- Custom domain: `api.deb2b.id.vn`.
- Secret như `DATABASE_URL`, session/encryption keys, OAuth secret và `GEMINI_API_KEY` chỉ được lưu
  trong Render; không được commit.

Mỗi release phải chạy quality gates, deploy cùng một commit từ `main`, kiểm tra `/live`, `/ready`,
OpenAPI route, CORS/auth boundary và một authenticated AI inference trước khi kết luận hoàn tất.
Chi tiết xem [portfolio deployment](docs/PORTFOLIO_DEPLOYMENT.md),
[deployment guide](docs/DEPLOYMENT.md) và [release checklist](docs/RELEASE_CHECKLIST.md).

## Bảo mật và dữ liệu

- Chỉ dùng synthetic/anonymized data trên portfolio deployment.
- Session HttpOnly, OAuth state/nonce/PKCE và CSRF cho mutation.
- Permission-based RBAC và tenant-scoped database access.
- Refresh token được mã hóa; metrics endpoint được bảo vệ.
- CSP, HSTS, frame denial, referrer và browser permission policy trên frontend.
- Không log API key, OAuth secret, token hoặc raw sensitive document text.

Xem [Security and privacy](docs/SECURITY_AND_PRIVACY.md) và
[Production readiness report](docs/PRODUCTION_READINESS_REPORT.md).

## Tài liệu

- [AI Agent runbook](docs/AI_AGENT_RUNBOOK.md)
- [Operations runbook](docs/RUNBOOK.md)
- [V1 operations](docs/V1_OPERATIONS.md)
- [V2 operations](docs/V2_OPERATIONS.md)
- [Production architecture](docs/PRODUCTION_ARCHITECTURE.md)
- [Portfolio deployment](docs/PORTFOLIO_DEPLOYMENT.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)

## Trạng thái an toàn của portfolio

Portfolio là **conditional go** cho demo có kiểm soát. Các yêu cầu SLA, customer data thật, webhook,
timer bền vững, external delivery hoặc email sending cần một production readiness gate và hạ tầng
riêng trước khi bật.
