import base64
import hashlib
import hmac
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import httpx
from httpx import ASGITransport
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from backend.app.api.deps import get_current_user
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.main import app
from backend.app.models.domain.monetization import ProcessedAdTransaction
from backend.app.models.domain.user import User
from backend.app.services.ad_ssv_service import ad_ssv_service
from backend.app.services.billing_entitlement_service import billing_entitlement_service


@pytest.mark.asyncio
async def test_catalog_invariants_and_condition_c2():
    """Test 1: Sovereign Catalog Invariants: 6 canonical products, exact INR prices, Condition C2 USD hiding, and Web Store bonus."""
    with patch.object(settings, "ENABLE_GLOBAL_USD_BILLING", False):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/v1/store/catalog")
            assert res.status_code == 200
            data = res.json()["data"]

            assert data["currency"] == "INR"
            assert data["usd_enabled"] is False
            assert len(data["products"]) == 6

            products = {p["id"]: p for p in data["products"]}
            assert products["pass_weekly"]["inr_price"] == 49.0
            assert products["pass_monthly"]["inr_price"] == 149.0
            assert products["pass_infinity"]["inr_price"] == 1499.0
            assert products["contact_key_instant"]["inr_price"] == 29.0
            assert products["direct_letters_pack_3"]["inr_price"] == 49.0
            assert products["passport_24h"]["inr_price"] == 99.0

            # Under Condition C2 with USD billing disabled, all usd_price fields are None
            for p in data["products"]:
                assert p["usd_price"] is None

    # Test Web Store Parity (+20% bonus badges/descriptions, identical pricing)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res_web = await client.get("/api/v1/store/catalog?is_web_store=true")
        assert res_web.status_code == 200
        web_products = {p["id"]: p for p in res_web.json()["data"]["products"]}
        assert web_products["pass_weekly"]["inr_price"] == 49.0
        assert "+20%" in web_products["pass_weekly"]["badge_label"]
        assert "120 Swipes" in web_products["pass_weekly"]["description"]


@pytest.mark.asyncio
async def test_entitlement_provisioning(db_session, make_user):
    """Test 2: Entitlement Provisioning: pass_weekly adds 100 swipes, pass_monthly adds 500 swipes & 5 letters, pass_infinity enables has_unlimited_swipes."""
    user = make_user(
        full_name="Entitled Seeker",
        is_profile_completed=True,
        swipes_remaining=10,
        direct_letters_count=2,
    )
    db_session.add(user)
    await db_session.commit()

    # 1. Weekly Pass
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_weekly",
        session=db_session,
    )
    assert user.swipes_remaining == 110
    assert user.subscription_tier == "spark"
    assert user.is_ad_free is True

    # 2. Monthly Pass
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_monthly",
        session=db_session,
    )
    assert user.swipes_remaining == 610
    assert user.direct_letters_count == 7  # 2 + 5
    assert user.subscription_tier == "flame"

    # 3. Infinity Pass
    await billing_entitlement_service.provision_user_entitlements(
        user=user,
        product_identifier="pass_infinity",
        session=db_session,
    )
    assert user.has_unlimited_swipes is True
    assert user.direct_letters_count == 22  # 7 + 15
    assert user.subscription_tier == "lifetime"


@pytest.mark.asyncio
async def test_5_network_signature_validation(db_session, make_user):
    """Test 3: 5-Network SSV Signature Validation (AdMob, Meta, Unity, Liftoff, Chartboost) for authentic and forged callbacks."""
    user = make_user(
        full_name="SSV Seeker",
        is_profile_completed=True,
        swipes_remaining=0,
        direct_letters_count=0,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            # -----------------------------------------------------------------
            # 1. Google AdMob (ECDSA P-256 SHA-256)
            # -----------------------------------------------------------------
            private_key = ec.generate_private_key(ec.SECP256R1())
            public_key = private_key.public_key()
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")

            # Mock AdMob key cache with key_id "admob_key_001"
            ad_ssv_service.admob_keys_cache["admob_key_001"] = pem
            ad_ssv_service.admob_cache_expires_at = time.time() + 3600

            admob_custom_data = json.dumps({"user_id": str(user.id), "ad_type": "quick_reflection"})
            admob_params = {
                "ad_network": "12345",
                "ad_unit": "54321",
                "custom_data": admob_custom_data,
                "key_id": "admob_key_001",
                "reward_amount": "10",
                "reward_item": "swipes",
                "timestamp": "1700000000",
                "transaction_id": "admob_tx_001",
            }
            # Canonical query string excludes signature and key_id
            filtered = {k: v for k, v in admob_params.items() if k not in ("signature", "key_id")}
            canonical_qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
            raw_sig = private_key.sign(canonical_qs.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
            admob_params["signature"] = base64.urlsafe_b64encode(raw_sig).decode("utf-8")

            # Authentic AdMob SSV
            res_admob = await client.get("/api/v1/ads/ssv/admob", params=admob_params)
            assert res_admob.status_code == 200
            assert res_admob.json()["status"] == "ok"
            await db_session.refresh(user)
            assert user.swipes_remaining == 10

            # Forged AdMob SSV
            forged_admob = dict(admob_params)
            forged_admob["signature"] = "forged_admob_sig_xyz"
            forged_admob["transaction_id"] = "admob_tx_forged"
            res_admob_forged = await client.get("/api/v1/ads/ssv/admob", params=forged_admob)
            assert res_admob_forged.status_code == 400

            # -----------------------------------------------------------------
            # 2. Meta Audience Network (HMAC-SHA256)
            # -----------------------------------------------------------------
            # Fast-forward last_ad_watched_at to clear cooling
            user.last_ad_watched_at = datetime.now(timezone.utc) - timedelta(seconds=20)
            await db_session.commit()

            with patch.object(settings, "META_APP_SECRET", "meta_secret_key_123"):
                meta_custom_data = json.dumps({"user_id": str(user.id), "ad_type": "deep_resonance"})
                meta_params = {
                    "ad_network": "meta",
                    "custom_data": meta_custom_data,
                    "timestamp": "1700000010",
                    "transaction_id": "meta_tx_001",
                }
                meta_filtered = {k: v for k, v in meta_params.items() if k not in ("signature", "sig")}
                meta_qs = "&".join(f"{k}={meta_filtered[k]}" for k in sorted(meta_filtered.keys()))
                meta_params["signature"] = hmac.new(
                    b"meta_secret_key_123", meta_qs.encode("utf-8"), hashlib.sha256
                ).hexdigest()

                res_meta = await client.get("/api/v1/ads/ssv/meta", params=meta_params)
                assert res_meta.status_code == 200
                await db_session.refresh(user)
                assert user.direct_letters_count == 1

                # Forged Meta SSV
                forged_meta = dict(meta_params)
                forged_meta["signature"] = "forged_meta_sig"
                forged_meta["transaction_id"] = "meta_tx_forged"
                res_meta_forged = await client.get("/api/v1/ads/ssv/meta", params=forged_meta)
                assert res_meta_forged.status_code == 400

            # -----------------------------------------------------------------
            # 3. Unity Ads (HMAC-SHA256)
            # -----------------------------------------------------------------
            user.last_ad_watched_at = datetime.now(timezone.utc) - timedelta(seconds=20)
            await db_session.commit()

            with patch.object(settings, "UNITY_ADS_SECRET", "unity_secret_key_456"):
                unity_sid = json.dumps({"user_id": str(user.id), "ad_type": "quick_reflection"})
                unity_oid = "unity_tx_001"
                unity_hmac = hmac.new(
                    b"unity_secret_key_456", f"{unity_sid}:{unity_oid}".encode("utf-8"), hashlib.sha256
                ).hexdigest()

                res_unity = await client.get(
                    "/api/v1/ads/ssv/unity",
                    params={"sid": unity_sid, "oid": unity_oid, "hmac": unity_hmac},
                )
                assert res_unity.status_code == 200
                await db_session.refresh(user)
                assert user.swipes_remaining == 20  # 10 + 10

                # Forged Unity SSV
                res_unity_forged = await client.get(
                    "/api/v1/ads/ssv/unity",
                    params={"sid": unity_sid, "oid": "unity_tx_forged", "hmac": "forged_unity_hmac"},
                )
                assert res_unity_forged.status_code == 400

            # -----------------------------------------------------------------
            # 4. Liftoff / Vungle (SHA-256 Digest)
            # -----------------------------------------------------------------
            user.last_ad_watched_at = datetime.now(timezone.utc) - timedelta(seconds=20)
            await db_session.commit()

            with patch.object(settings, "LIFTOFF_API_SECRET", "liftoff_secret_key_789"):
                liftoff_tx = "liftoff_tx_001"
                liftoff_uid = f"{user.id}:quick_reflection"
                liftoff_digest = hashlib.sha256(
                    f"{liftoff_tx}:{liftoff_uid}:liftoff_secret_key_789".encode("utf-8")
                ).hexdigest()

                res_liftoff = await client.get(
                    "/api/v1/ads/ssv/liftoff",
                    params={
                        "transaction_id": liftoff_tx,
                        "user_id": liftoff_uid,
                        "digest": liftoff_digest,
                    },
                )
                assert res_liftoff.status_code == 200
                await db_session.refresh(user)
                assert user.swipes_remaining == 30  # 20 + 10

                # Forged Liftoff SSV
                res_liftoff_forged = await client.get(
                    "/api/v1/ads/ssv/liftoff",
                    params={
                        "transaction_id": "liftoff_tx_forged",
                        "user_id": liftoff_uid,
                        "digest": "forged_liftoff_digest",
                    },
                )
                assert res_liftoff_forged.status_code == 400

            # -----------------------------------------------------------------
            # 5. Chartboost (SHA-256 Digest)
            # -----------------------------------------------------------------
            user.last_ad_watched_at = datetime.now(timezone.utc) - timedelta(seconds=20)
            await db_session.commit()

            with patch.object(settings, "CHARTBOOST_APP_SECRET", "chartboost_secret_key_999"):
                cb_tx = "cb_tx_001"
                cb_uid = f"{user.id}:quick_reflection"
                cb_reward = "10"
                cb_digest = hashlib.sha256(
                    f"{cb_tx}:{cb_uid}:{cb_reward}:chartboost_secret_key_999".encode("utf-8")
                ).hexdigest()

                res_cb = await client.get(
                    "/api/v1/ads/ssv/chartboost",
                    params={
                        "trans_id": cb_tx,
                        "user_id": cb_uid,
                        "reward": cb_reward,
                        "digest": cb_digest,
                    },
                )
                assert res_cb.status_code == 200
                await db_session.refresh(user)
                assert user.swipes_remaining == 40  # 30 + 10

                # Forged Chartboost SSV
                res_cb_forged = await client.get(
                    "/api/v1/ads/ssv/chartboost",
                    params={
                        "trans_id": "cb_tx_forged",
                        "user_id": cb_uid,
                        "reward": cb_reward,
                        "digest": "forged_chartboost_digest",
                    },
                )
                assert res_cb_forged.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_idempotency_and_replay_defense(db_session, make_user):
    """Test 4: Idempotency & Replay Defense: Duplicate transaction_id returns HTTP 200 without double crediting balances."""
    user = make_user(
        full_name="Idempotent Seeker",
        is_profile_completed=True,
        swipes_remaining=5,
    )
    db_session.add(user)
    await db_session.commit()

    with patch.object(settings, "META_APP_SECRET", "meta_secret_123"):
        meta_custom_data = json.dumps({"user_id": str(user.id), "ad_type": "quick_reflection"})
        params = {
            "custom_data": meta_custom_data,
            "timestamp": "1700000000",
            "transaction_id": "replay_tx_unique_999",
        }
        filtered = {k: v for k, v in params.items() if k not in ("signature", "sig")}
        qs = "&".join(f"{k}={filtered[k]}" for k in sorted(filtered.keys()))
        params["signature"] = hmac.new(b"meta_secret_123", qs.encode("utf-8"), hashlib.sha256).hexdigest()

        app.dependency_overrides[get_db] = lambda: db_session

        try:
            transport = ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                # 1. First execution -> completed
                r1 = await client.get("/api/v1/ads/ssv/meta", params=params)
                assert r1.status_code == 200
                assert r1.json()["result"]["status"] == "completed"

                await db_session.refresh(user)
                assert user.swipes_remaining == 15  # 5 + 10

                # 2. Second execution with identical transaction_id -> already_processed (HTTP 200)
                r2 = await client.get("/api/v1/ads/ssv/meta", params=params)
                assert r2.status_code == 200
                assert r2.json()["result"]["status"] == "already_processed"

                await db_session.refresh(user)
                # Swipes balance must NOT have increased a second time
                assert user.swipes_remaining == 15
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_anti_bot_15s_cooling_and_20_ad_daily_ceiling(db_session, make_user):
    """Test 5: Anti-Bot Sentinel: Rejects requests within 15-second cooling window and blocks beyond 20 ads per 24 hours."""
    user = make_user(
        full_name="Bot Hunter",
        is_profile_completed=True,
        swipes_remaining=0,
    )
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:

            # 1. Initial status check: no cooling active, 0 ads watched
            res_status = await client.get("/api/v1/ads/status")
            assert res_status.status_code == 200
            status_data = res_status.json()
            assert status_data["cooling_active"] is False
            assert status_data["seconds_until_next_ad"] == 0
            assert status_data["daily_ads_watched"] == 0
            assert status_data["daily_ads_limit"] == 20

            # 2. Watch first ad via meta SSV
            with patch.object(settings, "META_APP_SECRET", "meta_secret_cooling"):
                custom_data = json.dumps({"user_id": str(user.id), "ad_type": "quick_reflection"})
                p1 = {"custom_data": custom_data, "transaction_id": "tx_cooling_1"}
                p1["signature"] = hmac.new(
                    b"meta_secret_cooling",
                    f"custom_data={custom_data}&transaction_id=tx_cooling_1".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()

                r1 = await client.get("/api/v1/ads/ssv/meta", params=p1)
                assert r1.status_code == 200
                assert r1.json()["result"]["status"] == "completed"

                # Check status immediately after: cooling should be active
                res_status2 = await client.get("/api/v1/ads/status")
                assert res_status2.json()["cooling_active"] is True
                assert res_status2.json()["seconds_until_next_ad"] > 0
                assert res_status2.json()["daily_ads_watched"] == 1

                # 3. Attempt immediate second ad (< 15s elapsed): returns 200 with rejected_cooling to halt network retry storms
                p2 = {"custom_data": custom_data, "transaction_id": "tx_cooling_2"}
                p2["signature"] = hmac.new(
                    b"meta_secret_cooling",
                    f"custom_data={custom_data}&transaction_id=tx_cooling_2".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()

                r2 = await client.get("/api/v1/ads/ssv/meta", params=p2)
                assert r2.status_code == 200
                assert r2.json()["result"]["status"] == "rejected_cooling"
                assert r2.json()["result"]["reward_points"] == 0
                await db_session.refresh(user)
                assert user.swipes_remaining == 10  # No reward added

                # 4. Fast-forward user.last_ad_watched_at past cooling window
                user.last_ad_watched_at = datetime.now(timezone.utc) - timedelta(seconds=20)
                await db_session.commit()

                # 5. Populate 19 more transactions to hit the 20-ad daily ceiling
                now = datetime.now(timezone.utc)
                for i in range(2, 21):
                    db_session.add(
                        ProcessedAdTransaction(
                            transaction_id=f"tx_bulk_{i}",
                            network="meta",
                            user_id=user.id,
                            ad_type="quick_reflection",
                            created_at=now - timedelta(minutes=i),
                        )
                    )
                await db_session.commit()

                res_status3 = await client.get("/api/v1/ads/status")
                assert res_status3.json()["daily_ads_watched"] == 20

                # 6. Attempt 21st ad: returns 200 with rejected_daily_limit to halt retry storms
                p21 = {"custom_data": custom_data, "transaction_id": "tx_ceiling_21"}
                p21["signature"] = hmac.new(
                    b"meta_secret_cooling",
                    f"custom_data={custom_data}&transaction_id=tx_ceiling_21".encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()

                r21 = await client.get("/api/v1/ads/ssv/meta", params=p21)
                assert r21.status_code == 200
                assert r21.json()["result"]["status"] == "rejected_daily_limit"
                assert r21.json()["result"]["reward_points"] == 0
                await db_session.refresh(user)
                assert user.swipes_remaining == 10  # No reward added
    finally:
        app.dependency_overrides.clear()
