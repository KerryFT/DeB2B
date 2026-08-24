from __future__ import annotations

from typing import Any


class S3ObjectStorage:
    def __init__(self, client: Any, *, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    async def put(self, *, tenant_id: str, key: str, content: bytes, content_type: str) -> str:
        object_key = f"{tenant_id}/{key}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=content,
            ContentType=content_type,
            Metadata={"tenant-id": tenant_id},
        )
        return object_key

    async def get(self, *, tenant_id: str, key: str) -> bytes:
        object_key = key if key.startswith(f"{tenant_id}/") else f"{tenant_id}/{key}"
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return bytes(response["Body"].read())

    def inventory(self, *, tenant_id: str) -> list[dict[str, object]]:
        response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=f"{tenant_id}/")
        return [
            {"key": item["Key"], "size": item["Size"], "etag": str(item["ETag"]).strip('"')}
            for item in response.get("Contents", [])
        ]

    def delete_tenant_prefix(self, *, tenant_id: str) -> int:
        inventory = self.inventory(tenant_id=tenant_id)
        if inventory:
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": [{"Key": item["key"]} for item in inventory]},
            )
        return len(inventory)
