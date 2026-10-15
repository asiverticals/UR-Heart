import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import SanctuaryException
from ..models.domain.monetization import AdRewardLedger, ProcessedAdTransaction
from ..models.domain.user import User

logger = logging.getLogger("SanctuaryAdSSV")


class AdSsvService:
    """5-Network Cryptographic Server-Side Verification (SSV) & Anti-Bot Cooling Engine."""

    def __init__(self) -> None:
        self.admob_keys_cache: Dict[str, str] = {}
        self.admob_cache_expires_at: float = 0.0

    async def fetch_admob_public_keys(self, force_refresh: bool = False) -> Dict[str, str]:
        """Fetches and caches Google AdMob ECDSA P-256 verifier keys."""
        now = time.time()
        if self.admob_keys_cache and not force_refresh and now < self.admob_cache_expires_at:
            return self.admob_keys_cache

        url = settings.ADMOB_VERIFIER_KEYS_URL or "https://www.gstatic.com/admob/reward/verifier-keys.json"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    self.admob_keys_cache = {
                        str(k["keyId"]): k["pem"]
                        for k in data.get("keys", [])
                        if "keyId" in k and "pem" in k
                    }
                    self.admob_cache_expires_at = now + 86400.0  # 24-hour cache
        except Exception as exc:
            logger.warning("Failed to fetch AdMob public keys from Google: %s", exc)

        return self.admob_keys_cache

    async def verify_admob_ssv(
        self,
        query_params: Dict[str, str],
        raw_query_string: Optional[str] = None,
    ) -> bool:
        """Verifies Google AdMob ECDSA SHA-256 signature over raw query parameters."""
        signature_b64 = query_params.get("signature")
        key_id = query_params.get("key_id")
        if not signature_b64 or not key_id:
            return False

        if raw_query_string:
            sig_idx = raw_query_string.find("&signature=")
            if sig_idx != -1:
                canonical_qs = raw_query_string[:sig_idx]
            else:
                sig_idx = raw_query_string.find("signature=")
                canonical_qs = raw_query_string[:sig_idx].rstrip("&") if sig_idx != -1 else raw_query_string
        else:
            # Build canonical sorted query string excluding signature and key_id as fallback
            filtered = {k: v for k, v in query_params.items() if k not in ("signature", "key_id")}
            canonical_qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))

        try:
            padded_b64 = signature_b64 + "=" * ((4 - len(signature_b64) % 4) % 4)
            raw_sig = base64.urlsafe_b64decode(padded_b64)

            key_pem = self.admob_keys_cache.get(str(key_id))
            if not key_pem:
                await self.fetch_admob_public_keys(force_refresh=True)
                key_pem = self.admob_keys_cache.get(str(key_id))

            if not key_pem:
                return False

            public_key = load_pem_public_key(key_pem.encode("utf-8"))

            # 1. Primary: Verify over original raw query string preceding &signature=
            if raw_query_string and "signature=" in raw_query_string:
                sig_idx = raw_query_string.find("&signature=")
                prefix = raw_query_string[:sig_idx] if sig_idx != -1 else raw_query_string.split("signature=")[0].rstrip("&")
                try:
                    public_key.verify(raw_sig, prefix.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
                    return True
                except Exception:
                    pass

            # 2. Secondary/Fallback: Verify over canonical sorted query string
            filtered = {k: v for k, v in query_params.items() if k not in ("signature", "key_id")}
            canonical_qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
            public_key.verify(raw_sig, canonical_qs.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
            return True
        except Exception as exc:
            logger.debug("AdMob ECDSA verification failed: %s", exc)
            return False

    def verify_meta_ssv(self, query_params: Dict[str, str]) -> bool:
        """Verifies Meta Audience Network HMAC-SHA256 signature over callback parameters."""
        signature = query_params.get("signature") or query_params.get("sig")
        secret = settings.META_APP_SECRET or settings.META_AUDIENCE_SSV_SECRET
        if not secret or not signature:
            return False

        filtered = {k: v for k, v in query_params.items() if k not in ("signature", "sig")}
        canonical_qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
        expected = hmac.new(
            secret.encode("utf-8"),
            canonical_qs.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_unity_ssv(self, query_params: Dict[str, str]) -> bool:
        """Verifies Unity Ads HMAC-SHA256/MD5 signature over sid and oid."""
        signature = query_params.get("hmac") or query_params.get("signature")
        secret = settings.UNITY_ADS_SECRET or settings.UNITY_ADS_SSV_SECRET
        if not secret or not signature:
            return False

        sid = query_params.get("sid", "")
        oid = query_params.get("oid", "")
        payload = f"{sid}:{oid}".encode("utf-8")

        expected_sha = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        expected_md5 = hmac.new(secret.encode("utf-8"), payload, hashlib.md5).hexdigest()

        return hmac.compare_digest(expected_sha, signature) or hmac.compare_digest(expected_md5, signature)

    def verify_liftoff_ssv(self, query_params: Dict[str, str]) -> bool:
        """Verifies Liftoff (Vungle) token digest / SHA-256 transaction signature."""
        signature = query_params.get("digest") or query_params.get("signature")
        secret = settings.LIFTOFF_API_SECRET or settings.LIFTOFF_SSV_SECRET
        if not secret or not signature:
            return False

        tx_id = query_params.get("transaction_id") or query_params.get("tx_id", "")
        user_id = query_params.get("user_id") or query_params.get("uid", "")
        payload = f"{tx_id}:{user_id}:{secret}".encode("utf-8")

        expected_sha = hashlib.sha256(payload).hexdigest()
        expected_hmac = hmac.new(secret.encode("utf-8"), f"{tx_id}:{user_id}".encode("utf-8"), hashlib.sha256).hexdigest()

        return hmac.compare_digest(expected_sha, signature) or hmac.compare_digest(expected_hmac, signature)

    def verify_chartboost_ssv(self, query_params: Dict[str, str]) -> bool:
        """Verifies Chartboost digest over trans_id, user_id, reward, and secret."""
        signature = query_params.get("digest") or query_params.get("signature")
        secret = settings.CHARTBOOST_APP_SECRET or settings.CHARTBOOST_SSV_SECRET
        if not secret or not signature:
            return False

        trans_id = query_params.get("trans_id") or query_params.get("transaction_id", "")
        user_id = query_params.get("user_id", "")
        reward = query_params.get("reward") or query_params.get("reward_amount", "10")

        payload = f"{trans_id}:{user_id}:{reward}:{secret}".encode("utf-8")
        expected_sha = hashlib.sha256(payload).hexdigest()
        expected_md5 = hashlib.md5(payload).hexdigest()

        return hmac.compare_digest(expected_sha, signature) or hmac.compare_digest(expected_md5, signature)

    async def fulfill_ssv_reward(
        self,
        network: str,
        transaction_id: str,
        custom_data: str,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Idempotently provisions ad reward, enforcing 15-second cooling and 20-ad daily ceiling."""
        if not transaction_id:
            raise SanctuaryException(
                error_code="INVALID_SSV_TRANSACTION",
                message="Missing transaction identifier in SSV callback.",
                status_code=400,
            )

        # 1. Parse custom_data payload first to resolve user
        user_uuid: Optional[UUID] = None
        ad_type = "quick_reflection"

        if custom_data:
            # Try JSON first
            try:
                parsed = json.loads(custom_data)
                if isinstance(parsed, dict):
                    user_uuid = UUID(str(parsed.get("user_id")))
                    ad_type = str(parsed.get("ad_type", ad_type))
            except Exception:
                # Fallback to colon-separated string: user_id:ad_type[:target_id]
                parts = custom_data.split(":")
                try:
                    user_uuid = UUID(parts[0])
                    if len(parts) > 1 and parts[1]:
                        ad_type = parts[1]
                except Exception:
                    pass

        if not user_uuid:
            raise SanctuaryException(
                error_code="INVALID_SSV_CUSTOM_DATA",
                message="Could not resolve user_id from SSV custom_data.",
                status_code=400,
            )

        # 2. Lock user row to serialize concurrent callbacks for this user
        user_stmt = select(User).where(User.id == user_uuid).with_for_update()
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise SanctuaryException(
                error_code="USER_NOT_FOUND",
                message=f"User {user_uuid} not found for ad reward.",
                status_code=404,
            )

        # 3. Replay defense under lock: check if already processed
        stmt = select(ProcessedAdTransaction).where(
            ProcessedAdTransaction.transaction_id == transaction_id
        )
        existing_res = await session.execute(stmt)
        if existing_res.scalar_one_or_none():
            return {
                "status": "already_processed",
                "transaction_id": transaction_id,
                "network": network,
            }

        now = datetime.now(timezone.utc)

        # 4. Anti-bot 15-second cooling interval check
        last_ad = user.last_ad_watched_at
        if last_ad is not None:
            if last_ad.tzinfo is None:
                last_ad = last_ad.replace(tzinfo=timezone.utc)
            elapsed = (now - last_ad).total_seconds()
            if elapsed < 15.0:
                # Terminal rejection: record transaction so ad network stops retrying, zero reward
                processed_tx = ProcessedAdTransaction(
                    transaction_id=transaction_id,
                    network=network,
                    user_id=user.id,
                    ad_type=f"rejected_cooling:{ad_type}",
                    created_at=now,
                )
                session.add(processed_tx)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                return {
                    "status": "rejected_cooling",
                    "transaction_id": transaction_id,
                    "network": network,
                    "user_id": str(user.id),
                    "reward_points": 0,
                }

        # 5. Anti-bot 20-ad daily ceiling check (rolling 24 hours, excluding rejected attempts)
        window_start = now - timedelta(hours=24)
        daily_count_stmt = select(func.count(ProcessedAdTransaction.id)).where(
            ProcessedAdTransaction.user_id == user.id,
            ProcessedAdTransaction.created_at >= window_start,
            ~ProcessedAdTransaction.ad_type.startswith("rejected_"),
        )
        daily_count_res = await session.execute(daily_count_stmt)
        daily_views = daily_count_res.scalar() or 0
        if daily_views >= 20:
            # Terminal rejection: record transaction so ad network stops retrying, zero reward
            processed_tx = ProcessedAdTransaction(
                transaction_id=transaction_id,
                network=network,
                user_id=user.id,
                ad_type=f"rejected_limit:{ad_type}",
                created_at=now,
            )
            session.add(processed_tx)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
            return {
                "status": "rejected_daily_limit",
                "transaction_id": transaction_id,
                "network": network,
                "user_id": str(user.id),
                "reward_points": 0,
            }

        # 6. Provision rewards by ad_type
        reward_points = 10
        if ad_type == "quick_reflection":
            user.swipes_remaining = (user.swipes_remaining or 0) + 10
            user.boost_points = (user.boost_points or 0) + 10
            reward_points = 10
        elif ad_type == "deep_resonance":
            user.direct_letters_count = (user.direct_letters_count or 0) + 1
            user.boost_points = (user.boost_points or 0) + 25
            reward_points = 25
        elif ad_type in ("sacred_bridge_reveal", "whatsapp_reveal"):
            user.instant_contact_keys = (getattr(user, "instant_contact_keys", 0) or 0) + 1
            user.instant_bridge_passes = (getattr(user, "instant_bridge_passes", 0) or 0) + 1
            reward_points = 15
        elif ad_type == "morning_harvest_unlock":
            user.reward_balance = (user.reward_balance or 0) + 50
            reward_points = 50
        elif ad_type in ("daily_streak_boost", "rewarded_daily_boost"):
            user.streak_count = (user.streak_count or 0) + 1
            reward_points = 20
        else:
            user.reward_balance = (user.reward_balance or 0) + 10
            reward_points = 10

        user.last_ad_watched_at = now

        # 7. Record transaction & ledger with concurrent duplicate defense
        processed_tx = ProcessedAdTransaction(
            transaction_id=transaction_id,
            network=network,
            user_id=user.id,
            ad_type=ad_type,
            created_at=now,
        )
        ledger_entry = AdRewardLedger(
            user_id=user.id,
            ssv_transaction_id=transaction_id,
            network=network,
            ad_type=ad_type,
            reward_points=reward_points,
            created_at=now,
        )

        session.add(processed_tx)
        session.add(ledger_entry)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return {
                "status": "already_processed",
                "transaction_id": transaction_id,
                "network": network,
            }

        return {
            "status": "completed",
            "transaction_id": transaction_id,
            "network": network,
            "user_id": str(user.id),
            "ad_type": ad_type,
            "reward_points": reward_points,
        }

    async def get_user_ad_status(self, user: User, session: AsyncSession) -> Dict[str, Any]:
        """Calculates cooling timer and remaining daily ad quota for seeker."""
        now = datetime.now(timezone.utc)
        cooling_active = False
        seconds_until_next_ad = 0

        last_ad = user.last_ad_watched_at
        if last_ad is not None:
            if last_ad.tzinfo is None:
                last_ad = last_ad.replace(tzinfo=timezone.utc)
            elapsed = (now - last_ad).total_seconds()
            if elapsed < 15.0:
                cooling_active = True
                seconds_until_next_ad = max(1, int(15.0 - elapsed))

        window_start = now - timedelta(hours=24)
        count_stmt = select(func.count(ProcessedAdTransaction.id)).where(
            ProcessedAdTransaction.user_id == user.id,
            ProcessedAdTransaction.created_at >= window_start,
            ~ProcessedAdTransaction.ad_type.startswith("rejected_"),
        )
        count_res = await session.execute(count_stmt)
        daily_ads_watched = count_res.scalar() or 0

        return {
            "cooling_active": cooling_active,
            "seconds_until_next_ad": seconds_until_next_ad,
            "daily_ads_watched": daily_ads_watched,
            "daily_ads_limit": 20,
        }


ad_ssv_service = AdSsvService()


def get_ad_ssv_service() -> AdSsvService:
    return ad_ssv_service
