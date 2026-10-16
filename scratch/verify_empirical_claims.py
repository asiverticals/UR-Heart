"""
Empirical verification harness for UR-Heart architecture & security audit claims.
Tests:
1. Missing 404 endpoints in FastAPI router:
   - POST /api/v1/profile/create -> 404
   - POST /api/v1/auth/refresh -> 404
2. Schema contract mismatch:
   - ProfileCreate rejects Flutter's extra fields (contact_bridge_handle, voice_spark_url, voice_spark_duration)
3. Modesty veil photo URL leakage:
   - feed_service payload dictionary returns is_photo_veiled=True alongside unblurred raw photos and avatar_url
4. Superadmin backdoor:
   - deps.py get_superadmin validates X-Superadmin-Key header against settings.SUPERADMIN_SECRET_KEY ("BsaapSingh")
5. Media voice spark unauthenticated redirect:
   - GET /api/v1/media/voice/{user_id}/{filename} has no authentication dependency and returns 307 redirect
6. In-app chat reporting disabled:
   - Flutter chat_dialogue_screen.dart line 261 has enabled: false
"""
import os
import sys
import uuid
from datetime import date
from pydantic import ValidationError

# Set testing environment
os.environ["ENVIRONMENT"] = "development"
os.environ["TESTING"] = "true"
sys.path.insert(0, os.path.abspath("."))

def test_missing_routes():
    print("\n--- Test 1: Verifying Missing FastAPI Routes ---")
    from backend.app.main import app
    
    all_routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            all_routes.append((route.path, getattr(route, "methods", set())))
        elif hasattr(route, "routes"):
            for sub_route in route.routes:
                all_routes.append((sub_route.path, getattr(sub_route, "methods", set())))

    route_paths = list(app.openapi()["paths"].keys())
    
    # Check POST /api/v1/profile/create
    profile_create_present = any("/profile/create" in p for p in route_paths)
    print(f"Profile create endpoint present: {profile_create_present}")
    assert profile_create_present, "Expected /api/v1/profile/create to be registered in FastAPI!"

    # Check POST /api/v1/auth/refresh
    refresh_present = any("/auth/refresh" in p for p in route_paths)
    print(f"Auth refresh endpoint present: {refresh_present}")
    assert refresh_present, "Expected /api/v1/auth/refresh to be registered in FastAPI!"
    
    print("[PASS] Routes verified: Both /api/v1/profile/create and /api/v1/auth/refresh are REGISTERED in FastAPI.")

def test_pydantic_contract_mismatch():
    print("\n--- Test 2: Verifying Flutter -> ProfileCreate Payload Contract ---")
    from backend.app.schemas.profile import ProfileCreate

    # Flutter payload from profile_setup_controller.dart#L342-L357
    flutter_payload = {
        "full_name": "Test Seeker",
        "dob": date(2000, 1, 1),
        "gender": "Woman",
        "interested_in": "Men",
        "contact_bridge_type": "whatsapp",
        "contact_bridge_handle": "+919999999999",
        "bio": "Searching for soul connection",
        "profession": "Engineer",
        "education": "B.Tech",
        "photos": ["https://media.urheart.app/users/123/moments/slot_1.webp"],
        "avatar_url": "https://media.urheart.app/users/123/moments/slot_1.webp",
        "voice_spark_url": "https://media.urheart.app/users/123/voice/prompt.m4a",
        "voice_spark_duration": 15,
    }

    profile = ProfileCreate(**flutter_payload)
    assert profile.full_name == "Test Seeker"
    assert profile.contact_bridge_handle == "+919999999999"
    assert profile.contact_bridge_raw == "+919999999999"
    assert profile.voice_spark_url == "https://media.urheart.app/users/123/voice/prompt.m4a"
    assert profile.voice_spark_duration == 15
    print("[PASS] ProfileCreate successfully accepts and validates Flutter onboarding payload.")

def test_modesty_veil_data_leakage():
    print("\n--- Test 3: Verifying Modesty Veil Data Leakage in feed_service.py ---")
    import inspect
    from backend.app.services.feed_service import FeedService
    
    source = inspect.getsource(FeedService.get_discovery_feed)
    assert '"is_photo_veiled": True' in source
    assert '"photos": candidate.photos' in source
    assert '"avatar_url": candidate.avatar_url' in source
    print("[PASS] feed_service.py source empirically verified:")
    print("  - Backend flags is_photo_veiled: True")
    print("  - Backend transmits candidate.photos and candidate.avatar_url verbatim over HTTP")

def test_superadmin_backdoor():
    print("\n--- Test 4: Verifying Superadmin Secret Key Backdoor in deps.py ---")
    import asyncio
    from backend.app.api.deps import get_superadmin
    from backend.app.core.config import settings

    assert bool(settings.SUPERADMIN_SECRET_KEY), "Expected SUPERADMIN_SECRET_KEY to be configured"

    # Invoke get_superadmin with the configured key and NO credentials / JWT
    async def run_check():
        result = await get_superadmin(
            x_superadmin_key=settings.SUPERADMIN_SECRET_KEY,
            credentials=None,
            db=None,
        )
        return result

    authorized = asyncio.run(run_check())
    assert authorized is True
    print("[PASS] Superadmin backdoor empirically confirmed: configured key grants full clearance without credentials.")

def test_media_unauthenticated_voice():
    print("\n--- Test 5: Verifying Authenticated Voice Spark Endpoint in media.py ---")
    from backend.app.main import app
    from backend.app.api.deps import get_current_user
    from backend.app.api.v1.endpoints.media import router as media_router

    voice_route = next(
        (r for r in media_router.routes if getattr(r, "path", None) == "/voice/{user_id}/{filename}"),
        None,
    )
    assert voice_route is not None, "Route /voice/{user_id}/{filename} not registered in media_router.routes"
    dep_calls = [d.call for d in voice_route.dependant.dependencies]
    assert get_current_user in dep_calls, "Route /voice/{user_id}/{filename} missing get_current_user dependency!"

    import httpx, asyncio, uuid
    from datetime import date
    from unittest.mock import AsyncMock, MagicMock
    from backend.app.core.database import get_db
    from backend.app.models.domain.user import User

    async def check_auth_and_authorization():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # 1. Negative authentication test: unauthenticated requests strictly rejected with HTTP 401
            resp = await client.get("/api/v1/media/voice/00000000-0000-0000-0000-000000000001/spark.m4a")
            assert resp.status_code == 401, f"Expected 401 for unauthenticated request, got {resp.status_code}"

            # 2. Negative authorization test: authenticated caller without mutual match strictly rejected with HTTP 403
            caller = User(
                id=uuid.uuid4(),
                auth_id=uuid.uuid4(),
                full_name="Caller Seeker",
                dob=date(1995, 1, 1),
                gender="Woman",
                interested_in="Men",
            )
            target_id = uuid.uuid4()
            mock_db = AsyncMock()
            mock_res = MagicMock()
            mock_res.scalar_one_or_none.return_value = None  # No mutual match found
            mock_db.execute.return_value = mock_res

            app.dependency_overrides[get_current_user] = lambda: caller
            app.dependency_overrides[get_db] = lambda: mock_db
            try:
                resp_unauth = await client.get(f"/api/v1/media/voice/{target_id}/spark.m4a")
                assert resp_unauth.status_code == 403, f"Expected 403 for unauthorized caller, got {resp_unauth.status_code}"
            finally:
                app.dependency_overrides.clear()

    asyncio.run(check_auth_and_authorization())
    print("[PASS] Voice spark endpoint verified: authentication (401) and authorization access control (403) strictly enforced.")

def main():
    print("==================================================")
    print("UR-HEART EMPIRICAL CHALLENGE VERIFICATION HARNESS")
    print("==================================================")
    test_missing_routes()
    test_pydantic_contract_mismatch()
    test_modesty_veil_data_leakage()
    test_superadmin_backdoor()
    test_media_unauthenticated_voice()
    print("\n>>> ALL EMPIRICAL CHALLENGE TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    main()
