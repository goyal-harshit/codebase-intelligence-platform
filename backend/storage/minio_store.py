"""MinIO/S3-backed Storage (optional, prod).

Activated when ``MINIO_ENDPOINT`` is set. The ``minio`` client is imported
lazily so the dependency is only required when this backend is actually used.
"""
from __future__ import annotations

import io

from .base import Storage


class MinioStorage(Storage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str,
                 bucket: str, secure: bool = False) -> None:
        from minio import Minio  # lazy: only needed when this backend is selected

        self.bucket = bucket
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(self.bucket, key, io.BytesIO(data), length=len(data),
                               content_type=content_type)
        return f"s3://{self.bucket}/{key}"

    def get(self, key: str) -> bytes:
        resp = self.client.get_object(self.bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def exists(self, key: str) -> bool:
        from minio.error import S3Error

        try:
            self.client.stat_object(self.bucket, key)
            return True
        except S3Error:
            return False
