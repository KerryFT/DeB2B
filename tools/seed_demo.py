from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select

from backend.application.bank_imports import preview_bank_csv, upsert_bank_rows
from backend.application.imports import preview_import
from backend.application.invoice_import_service import upsert_invoice_rows
from backend.infrastructure.database import SessionFactory
from backend.infrastructure.models import (
    AutomationPolicyRecord,
    ConnectorConfig,
    DisputeRootCauseRecord,
    LLMPricing,
    LLMQualityMetric,
    LLMUsageEvent,
    PaymentCase,
    Tenant,
)

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
USER_ID = "00000000-0000-0000-0000-000000000002"


def main() -> None:
    fixture = Path("data/fixtures/smoke-v1/invoices.xlsx")
    preview = preview_import(fixture.read_bytes(), fixture.name)
    if preview.invalid:
        raise SystemExit(f"fixture contains {len(preview.invalid)} invalid rows")
    with SessionFactory.begin() as session:
        tenant = session.scalar(select(Tenant).where(Tenant.id == TENANT_ID))
        if tenant is None:
            session.add(Tenant(id=TENANT_ID, name="AR Operations Demo"))
            session.flush()
        result = upsert_invoice_rows(
            session,
            tenant_id=TENANT_ID,
            rows=preview.valid,
            correlation_id="demo-seed-v1",
            actor_id=USER_ID,
        )
        bank_fixture = Path("data/fixtures/smoke-v1/bank.csv")
        bank_preview = preview_bank_csv(bank_fixture.read_bytes())
        bank_created, bank_duplicates = upsert_bank_rows(
            session, tenant_id=TENANT_ID, rows=bank_preview.valid
        )
        for provider, capabilities in (
            ("gmail", ["email.read", "draft.create"]),
            ("outlook", ["email.read", "draft.create", "webhook"]),
            ("misa", ["customer.read", "invoice.read", "payment.read"]),
            ("zalo", ["notification.preview"]),
        ):
            connector = session.scalar(
                select(ConnectorConfig).where(
                    ConnectorConfig.tenant_id == TENANT_ID,
                    ConnectorConfig.provider == provider,
                )
            )
            if connector is None:
                session.add(
                    ConnectorConfig(
                        tenant_id=TENANT_ID,
                        provider=provider,
                        environment="sandbox",
                        secret_reference=f"secret://demo/{provider}",
                        capabilities=capabilities,
                        settings={"synthetic": True},
                        enabled=False,
                    )
                )
        pricing_rows = (
            ("openai", "demo-fast", "0.20", "0.80"),
            ("gemini", "demo-fast", "0.10", "0.40"),
            ("anthropic", "demo-balanced", "0.30", "1.20"),
        )
        for provider, model, input_price, output_price in pricing_rows:
            pricing = session.scalar(
                select(LLMPricing).where(
                    LLMPricing.provider == provider,
                    LLMPricing.model == model,
                    LLMPricing.version == 1,
                )
            )
            if pricing is None:
                session.add(
                    LLMPricing(
                        provider=provider,
                        model=model,
                        effective_from=datetime(2026, 1, 1, tzinfo=UTC),
                        currency="USD",
                        input_per_million=input_price,
                        output_per_million=output_price,
                        version=1,
                    )
                )
        usage_count = session.scalar(
            select(func.count())
            .select_from(LLMUsageEvent)
            .where(LLMUsageEvent.tenant_id == TENANT_ID)
        )
        if not usage_count:
            for index, (provider, model, fallback, latency) in enumerate(
                (
                    ("openai", "demo-fast", False, 420),
                    ("gemini", "demo-fast", True, 610),
                    ("anthropic", "demo-balanced", False, 880),
                ),
                start=1,
            ):
                session.add(
                    LLMUsageEvent(
                        tenant_id=TENANT_ID,
                        occurred_at=datetime(2026, 8, 24, 2, index, tzinfo=UTC),
                        task_type="document_classification",
                        provider=provider,
                        model=model,
                        prompt_version="demo-p1",
                        route="fallback" if fallback else "primary",
                        fallback=fallback,
                        success=True,
                        schema_valid=True,
                        latency_ms=latency,
                        input_tokens=1_000 + index * 100,
                        output_tokens=120 + index * 10,
                        request_metadata={"fixture": "synthetic-v2", "request": index},
                    )
                )
        quality_count = session.scalar(
            select(func.count())
            .select_from(LLMQualityMetric)
            .where(LLMQualityMetric.tenant_id == TENANT_ID)
        )
        if not quality_count:
            for provider, model, score in (
                ("openai", "demo-fast", "0.97"),
                ("gemini", "demo-fast", "0.96"),
                ("anthropic", "demo-balanced", "0.95"),
            ):
                session.add(
                    LLMQualityMetric(
                        tenant_id=TENANT_ID,
                        measured_at=datetime(2026, 8, 24, tzinfo=UTC),
                        dataset_version="synthetic-v2",
                        task_type="document_classification",
                        provider=provider,
                        model=model,
                        prompt_version="demo-p1",
                        metric_name="field_accuracy",
                        metric_value=score,
                        sample_count=100,
                    )
                )
        policy = session.scalar(
            select(AutomationPolicyRecord).where(AutomationPolicyRecord.tenant_id == TENANT_ID)
        )
        if policy is None:
            session.add(
                AutomationPolicyRecord(
                    tenant_id=TENANT_ID,
                    mode="disabled",
                    policy_version="auto-email-demo-v1",
                    config={"canary_percent": 0, "daily_send_cap": 10, "synthetic": True},
                    kill_switch=True,
                )
            )
        dispute_count = session.scalar(
            select(func.count())
            .select_from(DisputeRootCauseRecord)
            .where(DisputeRootCauseRecord.tenant_id == TENANT_ID)
        )
        first_case = session.scalar(
            select(PaymentCase).where(PaymentCase.tenant_id == TENANT_ID).order_by(PaymentCase.id)
        )
        if not dispute_count and first_case is not None:
            session.add(
                DisputeRootCauseRecord(
                    tenant_id=TENANT_ID,
                    case_id=first_case.id,
                    primary_cause="missing_invalid_document",
                    contributing_causes=[],
                    confidence="0.82",
                    evidence_ids=["synthetic:invoice-import"],
                    reason_codes=["missing_document"],
                    taxonomy_version="root-cause-v1",
                    first_detected_at=datetime(2026, 8, 24, tzinfo=UTC),
                    owner_id="demo-owner@example.com",
                    status="OPEN",
                    reopen_count=0,
                )
            )
    print(
        result,
        {
            "bank_created": bank_created,
            "bank_duplicates": bank_duplicates,
            "v1_seed": "ready",
            "v2_seed": "safe-disabled-ready",
        },
    )


if __name__ == "__main__":
    main()
