from decimal import Decimal
import httpx
from httpx import ASGITransport
import pytest
from sqlalchemy import select

from backend.app.api.deps import get_current_user, get_db
from backend.app.main import app
from backend.app.models.domain.monetization import InAppPurchase


@pytest.mark.asyncio
async def test_apple_storekit_receipt_verification_and_entitlement(db_session, make_user):
    """Verifies POST /api/v1/payments/verify-in-app-purchase provisions StoreKit entitlement under Apple Guideline 3.1.1."""
    user = make_user(full_name="Apple Store Seeker")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "order_id": "apple_order_mock_999",
                "product_identifier": "pass_sovereign_weekly",
                "purchase_token": "valid_apple_storekit_receipt_token_12345",
                "amount_gross": "199.00",
            }
            res = await client.post("/api/v1/payments/verify-in-app-purchase", json=payload)
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True
            assert body["data"]["transaction_id"] == "valid_apple_storekit_receipt_token_12345"

            # Verify recorded in DB as in-app purchase with apple_storekit store
            stmt = select(InAppPurchase).where(InAppPurchase.user_id == user.id)
            result = await db_session.execute(stmt)
            purchases = result.scalars().all()
            assert len(purchases) == 1
            assert purchases[0].store == "apple_storekit"
            assert purchases[0].product_identifier == "pass_sovereign_weekly"
            assert purchases[0].status == "completed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_google_play_receipt_verification_and_entitlement(db_session, make_user):
    """Verifies POST /api/v1/payments/verify-in-app-purchase provisions Google Play entitlement."""
    user = make_user(full_name="Google Play Seeker")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "order_id": "GPA.3344-5566-7788-99001",
                "product_identifier": "direct_letter_single",
                "purchase_token": "valid_google_play_purchase_token_abcdef",
                "amount_gross": "29.00",
            }
            res = await client.post("/api/v1/payments/verify-in-app-purchase", json=payload)
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True
            assert body["data"]["transaction_id"] == "valid_google_play_purchase_token_abcdef"

            # Verify recorded in DB as in-app purchase with google_play store
            stmt = select(InAppPurchase).where(InAppPurchase.user_id == user.id)
            result = await db_session.execute(stmt)
            purchases = result.scalars().all()
            assert len(purchases) == 1
            assert purchases[0].store == "google_play"
            assert purchases[0].product_identifier == "direct_letter_single"
            assert purchases[0].status == "completed"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_invalid_short_store_receipt_token_rejected(db_session, make_user):
    """Verifies forged or malformed store receipt tokens (<16 chars) are rejected with 400."""
    user = make_user(full_name="Fraud Attempt Seeker")
    db_session.add(user)
    await db_session.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db_session

    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "order_id": "GPA.fake_order",
                "product_identifier": "direct_letter_single",
                "purchase_token": "short_token",  # < 16 chars
                "amount_gross": "29.00",
            }
            res = await client.post("/api/v1/payments/verify-in-app-purchase", json=payload)
            assert res.status_code == 400
            body = res.json()
            assert body["success"] is False
            assert body["error_code"] == "INVALID_STORE_RECEIPT"
    finally:
        app.dependency_overrides.clear()
