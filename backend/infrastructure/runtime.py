from __future__ import annotations

import boto3

from backend.application.documents import MalwareScanner
from backend.application.ports import ObjectStorage
from backend.infrastructure.config import Settings
from backend.infrastructure.fakes import FakeMalwareScanner, MemoryObjectStorage
from backend.infrastructure.malware import ClamAVScanner
from backend.infrastructure.s3_storage import S3ObjectStorage


def build_document_dependencies(settings: Settings) -> tuple[ObjectStorage, MalwareScanner]:
    if settings.app_env in {"development", "test"} or not settings.document_upload_enabled:
        return MemoryObjectStorage(), FakeMalwareScanner()
    if not all(
        (settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key, settings.clamav_host)
    ):
        raise RuntimeError("production document dependencies are not configured")
    access_key = settings.s3_access_key
    secret_key = settings.s3_secret_key
    clamav_host = settings.clamav_host
    assert access_key is not None and secret_key is not None and clamav_host is not None
    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=settings.s3_region,
    )
    return (
        S3ObjectStorage(
            client,
            bucket=settings.s3_bucket,
            server_side_encryption=settings.s3_server_side_encryption,
        ),
        ClamAVScanner(clamav_host, settings.clamav_port),
    )
