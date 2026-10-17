"""
Automated Test Suite for Production-Grade Web Portals
Validates HTML5 rendering, statutory compliance disclosures, and web checkout:
- GET /store (Web Store with +20% bonus and strict no-refund disclosure)
- GET /emergency-takedown (IT Rules 2021 Rule 3(2)(b) NCII 24h Portal)
- GET /grievance (Resident Grievance Officer: Anubhav Singh, Ayodhya District Court, asiverticals@gmail.com, NO phone)
- GET /refund (Strict No-Refund & Digital Consumable Finality Policy)
- GET /delete-account (DPDP Act 2023 § 12 & Apple 5.1.1(v) Out-of-App Incineration)
- GET /contact (Corporate Office & Support Desk)
- POST /api/v1/payments/web-create-order (Guest / Web Seeker Order Creation)
"""

import httpx
from httpx import ASGITransport
import pytest
from backend.app.main import app


@pytest.mark.asyncio
async def test_web_store_page_renders_with_perks_and_disclosures():
    """Verifies GET /store returns 200 OK, HTML5, +20% bonus perks, and strict no-refund notice."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/store")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text

        # Verify branding and web exclusive perks
        assert "UR-Heart Sanctuary" in html
        assert "+20% Bonus Perks" in html or "+20% Web Bonus" in html
        assert "Weekly Sovereign Pass" in html
        assert "Monthly Sovereign Pass" in html
        assert "Infinity Sovereign Pass" in html

        # Verify strict no-refund disclosure
        assert "Strict No-Refund Policy" in html
        assert "Consumer Protection" in html

        # Verify statutory grievance officer footer particulars
        assert "Anubhav Singh" in html
        assert "Ayodhya District Court" in html
        assert "asiverticals@gmail.com" in html

        # Verify telephone number is strictly NOT present
        assert "+91-120-4567890" not in html


@pytest.mark.asyncio
async def test_emergency_takedown_portal_renders_statutory_form():
    """Verifies GET /emergency-takedown exposes IT Rules 2021 Rule 3(2)(b) emergency form."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/emergency-takedown")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text

        assert "Rule 3(2)(b)" in html
        assert "24-Hour" in html
        assert "NCII" in html
        assert "Non-Consensual Intimate Imagery" in html
        assert "complainant_name" in html or "comp-name" in html
        assert "asiverticals@gmail.com" in html


@pytest.mark.asyncio
async def test_grievance_officer_portal_renders_anubhav_singh_ayodhya_and_no_phone():
    """Verifies GET /grievance displays Anubhav Singh, Ayodhya District Court, asiverticals@gmail.com, and NO phone."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/grievance")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text

        # Mandatory particulars
        assert "Anubhav Singh" in html
        assert "Ayodhya District Court" in html
        assert "asiverticals@gmail.com" in html
        assert "gac.gov.in" in html
        assert "15-Day" in html or "15 calendar days" in html
        assert "24-Hour" in html or "24 hours" in html

        # Verify telephone is omitted
        assert "+91-120-4567890" not in html
        assert "Phone:" not in html
        assert "Telephone:" not in html


@pytest.mark.asyncio
async def test_refund_policy_portal_renders_strict_no_refund_policy():
    """Verifies GET /refund displays strict no-refund policy under Consumer Protection Rules 2020."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/refund")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text

        assert "Strict No-Refund" in html
        assert "Consumer Protection (E-Commerce) Rules, 2020" in html or "Consumer Protection" in html
        assert "strictly final, non-refundable" in html or "non-refundable" in html
        assert "asiverticals@gmail.com" in html
        assert "Ayodhya District Court" in html


@pytest.mark.asyncio
async def test_data_incineration_portal_renders_dpdp_erasure():
    """Verifies GET /delete-account displays DPDP Section 12 out-of-app data incineration desk."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1 view without token
        res = await client.get("/delete-account")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text
        assert "DPDP Act 2023" in html
        assert "Section 12" in html
        assert "del-email" in html

        # Step 2 view with token
        res_with_token = await client.get("/delete-account?token=mock_incineration_token_xyz")
        assert res_with_token.status_code == 200
        html_token = res_with_token.text
        assert "PERMANENTLY INCINERATE" in html_token


@pytest.mark.asyncio
async def test_corporate_contact_hub_renders_ayodhya_address():
    """Verifies GET /contact displays ASI Verticals Private Limited at Ayodhya District Court."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/contact")
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")
        html = res.text
        assert "ASI Verticals Private Limited" in html
        assert "Ayodhya District Court" in html
        assert "asiverticals@gmail.com" in html


@pytest.mark.asyncio
async def test_web_create_order_for_guest_email(db_session):
    """Verifies POST /api/v1/payments/web-create-order creates order for guest seeker email."""
    from backend.app.api.deps import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "product_identifier": "pass_weekly",
                "email": "webseeker@example.com",
                "currency": "INR",
            }
            res = await client.post("/api/v1/payments/web-create-order", json=payload)
            assert res.status_code == 200
            body = res.json()
            assert body["success"] is True
            data = body["data"]
            assert data["order_id"].startswith("order_")
            assert data["amount"] == 49.0
            assert data["amount_paise"] == 4900
            assert data["currency"] == "INR"
            assert "key_id" in data
    finally:
        app.dependency_overrides.clear()

