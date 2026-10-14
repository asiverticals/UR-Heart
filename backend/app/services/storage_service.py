from typing import Any, Optional
import boto3
from botocore.config import Config

from ..core.config import settings
from ..core.exceptions import SanctuaryException

class CloudflareR2StorageService:
    """Enterprise Cloudflare R2 storage adapter generating S3v4 presigned URLs and managing media lifecycles."""

    def __init__(
        self,
        account_id: Optional[str] = None,
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        public_domain: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        self.account_id = account_id or settings.CLOUDFLARE_ACCOUNT_ID
        self.access_key_id = access_key_id or settings.R2_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key or settings.R2_SECRET_ACCESS_KEY
        self.bucket_name = bucket_name or settings.R2_BUCKET_NAME or "ur-heart-media"
        self.public_domain = public_domain or settings.R2_PUBLIC_DOMAIN or "https://media.urheart.app"

        if client is not None:
            self.s3_client = client
        elif self.account_id and self.access_key_id and self.secret_access_key:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=f"https://{self.account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name="auto",
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            )
        else:
            self.s3_client = None

    def validate_credentials(self) -> None:
        """Validates that Cloudflare R2 credentials or an active S3 client are configured."""
        if self.s3_client is None:
            raise SanctuaryException(
                error_code="STORAGE_UNCONFIGURED",
                message="Cloudflare R2 storage credentials (CLOUDFLARE_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY) are not configured.",
                status_code=500,
            )

    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str = "image/webp",
        content_length: Optional[int] = None,
        expires_in: int = 300,
    ) -> str:
        """Generates an S3v4 Presigned PUT URL allowing clients to upload directly to R2 within 5 minutes."""
        self.validate_credentials()
        params: dict[str, Any] = {
            "Bucket": self.bucket_name,
            "Key": key,
            "ContentType": content_type,
        }
        if content_length is not None:
            params["ContentLength"] = content_length

        return self.s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expires_in,
        )

    def generate_presigned_get_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generates a signed GET URL for private assets (e.g. KYC verification review frames)."""
        self.validate_credentials()
        return self.s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self.bucket_name,
                "Key": key,
            },
            ExpiresIn=expires_in,
        )

    def get_public_cdn_url(self, key: str) -> str:
        """Constructs the canonical Cloudflare Edge CDN URL for publicly available assets."""
        domain = self.public_domain or "https://media.urheart.app"
        return f"{domain.rstrip('/')}/{key.lstrip('/')}"

    def get_object_bytes(self, key: str) -> bytes:
        """Retrieves raw object bytes from Cloudflare R2 bucket."""
        self.validate_credentials()
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"].read()

    def put_object_bytes(self, key: str, data: bytes, content_type: str = "image/webp") -> bool:
        """Stores binary bytes directly into Cloudflare R2 bucket."""
        self.validate_credentials()
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return True

    def delete_object(self, key: str) -> bool:
        """Deletes a single object from Cloudflare R2."""
        self.validate_credentials()
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=key,
        )
        return True

    def delete_objects_by_prefix(self, prefix: str) -> int:
        """Paginates and batch-deletes all objects matching a prefix (e.g. users/{user_id}/ under DPDP Sec 12)."""
        self.validate_credentials()
        total_deleted = 0
        paginator = self.s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            contents = page.get("Contents", [])
            if not contents:
                continue
            keys = [{"Key": obj["Key"]} for obj in contents]
            for i in range(0, len(keys), 1000):
                chunk = keys[i : i + 1000]
                resp = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={"Objects": chunk},
                )
                errors = resp.get("Errors", [])
                if errors:
                    failed_keys = [e.get("Key", "unknown") for e in errors]
                    raise RuntimeError(
                        f"R2 batch deletion failed for {len(failed_keys)} objects: {failed_keys}"
                    )
                deleted_items = resp.get("Deleted", chunk)
                total_deleted += len(deleted_items)
        return total_deleted

storage_service = CloudflareR2StorageService()

def get_storage_service() -> CloudflareR2StorageService:
    """Dependency provider returning the active Cloudflare R2 storage service."""
    return storage_service
