import json
import logging
from typing import Any, Dict, List, Optional
import urllib.parse
import boto3
from botocore.config import Config
import httpx

from ..core.config import settings
from ..core.exceptions import SanctuaryException

logger = logging.getLogger("urheart.storage")


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
        self.account_id = account_id if account_id is not None else settings.CLOUDFLARE_ACCOUNT_ID
        self.access_key_id = access_key_id if access_key_id is not None else settings.R2_ACCESS_KEY_ID
        self.secret_access_key = secret_access_key if secret_access_key is not None else settings.R2_SECRET_ACCESS_KEY
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
        """Paginates and batch-deletes all objects matching a prefix."""
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


class SupabaseStorageService:
    """Supabase Storage adapter utilizing Supabase Storage REST API."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ):
        self.supabase_url = (supabase_url or settings.SUPABASE_URL).rstrip("/")
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY
        self.bucket_name = bucket_name or settings.SUPABASE_STORAGE_BUCKET or "ur-heart-media"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def validate_credentials(self) -> None:
        if not self.supabase_url or not self.service_role_key:
            raise SanctuaryException(
                error_code="STORAGE_UNCONFIGURED",
                message="Supabase Storage credentials (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) are not configured.",
                status_code=500,
            )

    def generate_presigned_put_url(
        self,
        key: str,
        content_type: str = "image/webp",
        content_length: Optional[int] = None,
        expires_in: int = 300,
    ) -> str:
        """Generates a signed upload URL via Supabase Storage REST API."""
        self.validate_credentials()
        clean_key = "/".join(urllib.parse.quote(seg, safe="") for seg in key.lstrip("/").split("/"))
        url = f"{self.supabase_url}/storage/v1/object/upload/sign/{self.bucket_name}/{clean_key}"
        # shortcut: Supabase upload-sign endpoint enforces a server-configured 2h JWT lifetime, upgrade to edge worker if strict sub-minute expiry needed
        sign_payload = {"expiresIn": expires_in}
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=self._headers(), json=sign_payload)
                if res.status_code == 200:
                    signed_path = res.json().get("url", "")
                    if signed_path.startswith("http"):
                        return signed_path
                    return f"{self.supabase_url}/storage/v1{signed_path}"
                logger.error("Supabase Storage presigned upload returned %d for key %s", res.status_code, clean_key)
        except Exception as e:
            logger.error("Supabase Storage presigned upload URL error: %s", e)
            raise SanctuaryException(
                error_code="PRESIGNED_UPLOAD_FAILED",
                message=f"Failed to generate signed upload target: {e}",
                status_code=500,
            )
        raise SanctuaryException(
            error_code="PRESIGNED_UPLOAD_FAILED",
            message="Failed to generate signed upload target from Supabase Storage.",
            status_code=500,
        )

    def generate_presigned_get_url(
        self,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        self.validate_credentials()
        clean_key = "/".join(urllib.parse.quote(seg, safe="") for seg in key.lstrip("/").split("/"))
        url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket_name}/{clean_key}"
        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, headers=self._headers(), json={"expiresIn": expires_in})
                if res.status_code == 200:
                    signed_path = res.json().get("signedURL", "")
                    if signed_path.startswith("http"):
                        return signed_path
                    return f"{self.supabase_url}/storage/v1{signed_path}"
                logger.error(
                    "Supabase Storage presigned GET returned %d for key %s",
                    res.status_code,
                    clean_key,
                )
        except Exception as e:
            logger.error(f"Supabase Storage presigned URL generation error: {e}")
        raise SanctuaryException(
            error_code="PRESIGNED_URL_GENERATION_FAILED",
            message=f"Failed to generate secure signed URL for storage key: {clean_key}",
            status_code=500,
        )

    def get_public_cdn_url(self, key: str) -> str:
        clean_key = key.lstrip("/")
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{clean_key}"

    def get_object_bytes(self, key: str) -> bytes:
        self.validate_credentials()
        clean_key = key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{clean_key}"
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=self._headers())
            if resp.status_code != 200:
                raise SanctuaryException(
                    error_code="STORAGE_OBJECT_NOT_FOUND",
                    message=f"Supabase storage object not found: {key}",
                    status_code=resp.status_code,
                )
            return resp.content

    def put_object_bytes(self, key: str, data: bytes, content_type: str = "image/webp") -> bool:
        """Stores binary bytes directly into Supabase Storage. Returns True on success, raises SanctuaryException on failure (including network/transport errors)."""
        self.validate_credentials()
        clean_key = key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{clean_key}"
        headers = self._headers()
        headers["Content-Type"] = content_type
        headers["x-upsert"] = "true"
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(url, headers=headers, content=data)
                if resp.status_code not in (200, 201):
                    raise SanctuaryException(
                        error_code="STORAGE_PUT_FAILED",
                        message=f"Failed to put object bytes to Supabase Storage for key: {key}",
                        status_code=resp.status_code,
                    )
                return True
        except httpx.RequestError as e:
            raise SanctuaryException(
                error_code="STORAGE_PUT_FAILED",
                message=f"Network error while writing to Supabase Storage: {e}",
                status_code=503,
            )

    def delete_object(self, key: str) -> bool:
        """Deletes a single object from Supabase Storage. Returns True on success, raises SanctuaryException on failure (including network/transport errors)."""
        self.validate_credentials()
        clean_key = key.lstrip("/")
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.request("DELETE", url, headers=self._headers(), json={"prefixes": [clean_key]})
                if resp.status_code != 200:
                    raise SanctuaryException(
                        error_code="STORAGE_DELETE_FAILED",
                        message=f"Failed to delete storage object: {key}",
                        status_code=resp.status_code,
                    )
                return True
        except httpx.RequestError as e:
            raise SanctuaryException(
                error_code="STORAGE_DELETE_FAILED",
                message=f"Network error while deleting from Supabase Storage: {e}",
                status_code=503,
            )

    def delete_objects_by_prefix(self, prefix: str) -> int:
        self.validate_credentials()
        clean_prefix = prefix.lstrip("/")
        list_url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
        del_url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
        total_deleted = 0

        def _list_recursive(current_prefix: str) -> List[str]:
            all_keys: List[str] = []
            offset = 0
            while True:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.post(
                        list_url,
                        headers=self._headers(),
                        json={"prefix": current_prefix, "limit": 100, "offset": offset},
                    )
                    if resp.status_code != 200:
                        raise SanctuaryException(
                            error_code="STORAGE_LISTING_FAILED",
                            message=f"Failed to list objects under prefix '{current_prefix}'.",
                            status_code=resp.status_code,
                        )
                    items = resp.json()
                    if not items:
                        break
                    for item in items:
                        name = item.get("name")
                        if not name:
                            continue
                        full_path = f"{current_prefix.rstrip('/')}/{name}" if current_prefix else name
                        # Folders in Supabase Storage have id=None or metadata=None
                        if item.get("id") is None and item.get("metadata") is None:
                            all_keys.extend(_list_recursive(full_path))
                        else:
                            all_keys.append(full_path)
                    offset += len(items)
                    if len(items) < 100:
                        break
            return all_keys

        target_keys = _list_recursive(clean_prefix)
        if not target_keys:
            return 0

        batch_size = 100
        with httpx.Client(timeout=15.0) as client:
            for i in range(0, len(target_keys), batch_size):
                batch = target_keys[i : i + batch_size]
                del_resp = client.request("DELETE", del_url, headers=self._headers(), json={"prefixes": batch})
                if del_resp.status_code != 200:
                    raise SanctuaryException(
                        error_code="STORAGE_DELETE_FAILED",
                        message=f"Failed to purge batch of {len(batch)} storage objects under '{clean_prefix}'.",
                        status_code=del_resp.status_code,
                    )
                total_deleted += len(batch)

        return total_deleted


class UnifiedStorageService:
    """Unified storage service prioritizing Cloudflare R2 and falling back to Supabase Storage."""

    def __init__(
        self,
        r2_service: Optional[CloudflareR2StorageService] = None,
        supabase_service: Optional[SupabaseStorageService] = None,
    ):
        self.r2 = r2_service or CloudflareR2StorageService()
        self.supabase = supabase_service or SupabaseStorageService()

    @property
    def _active_adapter(self) -> Any:
        # Prioritize Cloudflare R2 if configured, otherwise Supabase Storage
        if self.r2.s3_client is not None:
            return self.r2
        if self.supabase.supabase_url and self.supabase.service_role_key:
            return self.supabase
        return self.r2

    def validate_credentials(self) -> None:
        self._active_adapter.validate_credentials()

    def generate_presigned_put_url(self, key: str, content_type: str = "image/webp", content_length: Optional[int] = None, expires_in: int = 300) -> str:
        return self._active_adapter.generate_presigned_put_url(key, content_type, content_length, expires_in)

    def generate_presigned_get_url(self, key: str, expires_in: int = 3600) -> str:
        return self._active_adapter.generate_presigned_get_url(key, expires_in)

    def get_public_cdn_url(self, key: str) -> str:
        return self._active_adapter.get_public_cdn_url(key)

    def get_object_bytes(self, key: str) -> bytes:
        return self._active_adapter.get_object_bytes(key)

    def put_object_bytes(self, key: str, data: bytes, content_type: str = "image/webp") -> bool:
        return self._active_adapter.put_object_bytes(key, data, content_type)

    def delete_object(self, key: str) -> bool:
        return self._active_adapter.delete_object(key)

    def delete_objects_by_prefix(self, prefix: str) -> int:
        return self._active_adapter.delete_objects_by_prefix(prefix)


# Default singleton instance
storage_service = UnifiedStorageService()

def get_storage_service() -> UnifiedStorageService:
    """Dependency provider returning the active unified storage service."""
    return storage_service
