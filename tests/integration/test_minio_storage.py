from uuid import uuid4

import boto3
import pytest

from backend.infrastructure.s3_storage import S3ObjectStorage


@pytest.mark.asyncio
async def test_minio_put_get_and_tenant_prefix_inventory() -> None:
    client = boto3.client(
        "s3",
        endpoint_url="http://127.0.0.1:9000",
        aws_access_key_id="localdev",
        aws_secret_access_key="localdev-secret",  # noqa: S106 - Compose-only fixture
        region_name="us-east-1",
    )
    storage = S3ObjectStorage(client, bucket="ar-documents")
    storage.ensure_bucket()
    tenant_id = str(uuid4())
    key = await storage.put(
        tenant_id=tenant_id,
        key="sha256/test-object",
        content=b"synthetic object",
        content_type="application/octet-stream",
    )
    assert await storage.get(tenant_id=tenant_id, key=key) == b"synthetic object"
    inventory = storage.inventory(tenant_id=tenant_id)
    assert inventory == [
        {"key": f"{tenant_id}/sha256/test-object", "size": 16, "etag": inventory[0]["etag"]}
    ]
    assert storage.delete_tenant_prefix(tenant_id=tenant_id) == 1
    assert storage.inventory(tenant_id=tenant_id) == []
