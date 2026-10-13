import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
import pytest
from pydantic import ValidationError

from backend.app.core.config import settings
from backend.app.models.domain.user import User
from backend.app.schemas import (
    SanctuaryResponse,
    SanctuaryErrorResponse,
    RegisterIntentRequest,
    GoogleSyncRequest,
    MagicLinkSendRequest,
    MagicLinkVerifyRequest,
    TokenResponse,
    ProfileCreate,
    ProfileUpdate,
    ProfilePublicResponse,
    SwipeRequest,
    SwipeResponse,
    PhotoRevealRequest,
    PhotoRevealResponse,
    DialogueMessageSend,
    MessageItemResponse,
    PassWithGraceClosureRequest,
    WsTicketResponse,
    BlindDateQueueJoin,
    BlindDateSessionResponse,
    BlindDateDecisionRequest,
    RazorpayOrderCreate,
    RazorpayPaymentVerify,
    InAppPurchaseVerifyRequest,
    AdSSVCallbackParams,
    WebStoreClaimPending,
    GrievanceSubmitRequest,
    GrievanceResponse,
    DataNomineeRequest,
    WebAccountDeletionRequest,
)

def safe_years_ago(years: int, from_date: Optional[date] = None) -> date:
    """Safely calculate a date N years ago, handling February 29 on leap years."""
    d = from_date or date.today()
    try:
        return d.replace(year=d.year - years)
    except ValueError:
        return date(d.year - years, 2, 28)

def test_register_intent_age_verification():
    """Test 1: RegisterIntentRequest permits age >= 18 and strictly rejects age < 18."""
    # 20 years old -> valid
    valid_dob = safe_years_ago(20)
    req = RegisterIntentRequest(
        dob=valid_dob,
        device_fingerprint="a" * 32,
    )
    assert req.dob == valid_dob

    # 17 years old -> raises ValidationError
    underage_dob = safe_years_ago(17)
    with pytest.raises(ValidationError) as exc:
        RegisterIntentRequest(
            dob=underage_dob,
            device_fingerprint="a" * 32,
        )
    assert "under 18 years of age" in str(exc.value)

def test_ingestion_extra_fields_forbidden():
    """Test 2: All ingestion schemas reject unknown injected fields (extra='forbid')."""
    valid_dob = safe_years_ago(22)

    # Injected field on RegisterIntentRequest
    with pytest.raises(ValidationError) as exc:
        RegisterIntentRequest(
            dob=valid_dob,
            device_fingerprint="a" * 32,
            malicious_payload="drop_database",  # type: ignore
        )
    assert "extra_forbidden" in str(exc.value)

    # Injected field on SwipeRequest
    with pytest.raises(ValidationError) as exc:
        SwipeRequest(
            target_id=uuid.uuid4(),
            action="like",
            hacker_param="bypass",  # type: ignore
        )
    assert "extra_forbidden" in str(exc.value)

    # Injected field on DialogueMessageSend
    with pytest.raises(ValidationError) as exc:
        DialogueMessageSend(
            match_id=uuid.uuid4(),
            recipient_id=uuid.uuid4(),
            encrypted_text="valid ciphertext",
            client_id="client_uuid_123",
            tamper_flag=True,  # type: ignore
        )
    assert "extra_forbidden" in str(exc.value)

def test_swipe_action_enum_strictness():
    """Test 3: SwipeRequest accepts only 'like', 'pass', or 'superlike'."""
    target = uuid.uuid4()
    for act in ["like", "pass", "superlike"]:
        req = SwipeRequest(target_id=target, action=act)
        assert req.action == act

    # Invalid action like 'swipe_right' or 'dislike' must be rejected
    with pytest.raises(ValidationError):
        SwipeRequest(target_id=target, action="swipe_right")  # type: ignore

def test_dialogue_message_bounds():
    """Test 4: DialogueMessageSend validates encrypted_text length boundaries."""
    match_id = uuid.uuid4()
    recipient_id = uuid.uuid4()

    # Empty text rejected (min_length=1)
    with pytest.raises(ValidationError):
        DialogueMessageSend(
            match_id=match_id,
            recipient_id=recipient_id,
            encrypted_text="",
            client_id="client_01",
        )

    # Oversized text rejected (max_length=4096)
    with pytest.raises(ValidationError):
        DialogueMessageSend(
            match_id=match_id,
            recipient_id=recipient_id,
            encrypted_text="a" * 4097,
            client_id="client_01",
        )

    # Valid text accepted
    valid = DialogueMessageSend(
        match_id=match_id,
        recipient_id=recipient_id,
        encrypted_text="encrypted_base64_payload",
        client_id="client_01",
    )
    assert valid.encrypted_text == "encrypted_base64_payload"

def test_profile_public_response_orm_serialization():
    """Test 5: ProfilePublicResponse serializes ORM models calculating age without PII leak."""
    user_dob = safe_years_ago(25)

    mock_user = User(
        id=uuid.uuid4(),
        auth_id=uuid.uuid4(),
        email="seeker@urheart.app",
        full_name="Ananya Sharma",
        dob=user_dob,
        gender="Woman",
        interested_in="Men",
        contact_bridge_type="whatsapp",
        contact_bridge_encrypted="super_secret_enc_bridge",
        location_name="Varanasi, UP",
        bio="Serenity seeker and classical music lover.",
        profession="Architect",
        education="IIT BHU",
        streak_count=5,
        boost_points=50,
        kyc_status=True,
        is_photo_veiled=False,
        photos=["https://media.urheart.app/users/123/moments/slot_1.webp"],
        avatar_url="https://media.urheart.app/users/123/avatar/primary.webp",
        referral_code="ANANYA108",
    )

    public_profile = ProfilePublicResponse.model_validate(mock_user)
    assert public_profile.id == mock_user.id
    assert public_profile.full_name == "Ananya Sharma"
    assert public_profile.age == 25
    assert public_profile.kyc_status is True
    assert "https://media.urheart.app" in public_profile.photos[0]

    # Verify sensitive PII is absent from serialization dump
    dump = public_profile.model_dump()
    assert "auth_id" not in dump
    assert "email" not in dump
    assert "contact_bridge_encrypted" not in dump
    assert "referral_code" not in dump

def test_monetization_usd_gating():
    """Test 6: RazorpayOrderCreate rejects USD when ENABLE_GLOBAL_USD_BILLING is False."""
    orig = settings.ENABLE_GLOBAL_USD_BILLING
    try:
        settings.ENABLE_GLOBAL_USD_BILLING = False
        with pytest.raises(ValidationError, match="USD billing is disabled under condition C2"):
            RazorpayOrderCreate(product_identifier="pass_sovereign_monthly", currency="USD")

        # INR currency is always allowed
        inr_order = RazorpayOrderCreate(product_identifier="pass_sovereign_monthly", currency="INR")
        assert inr_order.currency == "INR"

        # When flag is enabled, USD is permitted
        settings.ENABLE_GLOBAL_USD_BILLING = True
        usd_order = RazorpayOrderCreate(product_identifier="pass_sovereign_monthly", currency="USD")
        assert usd_order.currency == "USD"
    finally:
        settings.ENABLE_GLOBAL_USD_BILLING = orig

def test_generic_sanctuary_response_envelope():
    """Test 7: SanctuaryResponse and SanctuaryErrorResponse enforce unified envelope structure."""
    res = SanctuaryResponse[dict](data={"active": True}, message="Sanctuary alive")
    assert res.success is True
    assert res.data == {"active": True}
    assert res.message == "Sanctuary alive"
    assert res.timestamp is not None

    err = SanctuaryErrorResponse(
        error_code="UNDERAGE_QUARANTINE_TRIGGERED",
        message="Seeker is under the legal age threshold.",
        details={"age": 16},
    )
    assert err.success is False
    assert err.error_code == "UNDERAGE_QUARANTINE_TRIGGERED"
    assert err.details == {"age": 16}

def test_blind_date_queue_age_boundaries():
    """Test 8: BlindDateQueueJoin validates min and max age boundaries and logical ordering."""
    # min > max raises error
    with pytest.raises(ValidationError, match="preferred_age_min cannot exceed preferred_age_max"):
        BlindDateQueueJoin(preferred_age_min=30, preferred_age_max=25)

    # under 18 raises error
    with pytest.raises(ValidationError):
        BlindDateQueueJoin(preferred_age_min=17, preferred_age_max=25)

    # Valid configuration succeeds
    valid = BlindDateQueueJoin(preferred_age_min=21, preferred_age_max=28)
    assert valid.preferred_age_min == 21
    assert valid.preferred_age_max == 28

def test_in_app_purchase_non_negative_amount():
    """Test 9: InAppPurchaseVerifyRequest rejects negative amounts."""
    with pytest.raises(ValidationError):
        InAppPurchaseVerifyRequest(
            order_id="GPA.1234-5678",
            product_identifier="direct_letter_single",
            purchase_token="tok_12345",
            amount_gross=Decimal("-10.00"),
        )

def test_data_nominee_length_boundaries():
    """Test 10: DataNomineeRequest enforces min and max length bounds."""
    with pytest.raises(ValidationError):
        DataNomineeRequest(
            nominee_name="A",  # too short (<2)
            nominee_contact="12345",
            relationship="Brother",
        )

    valid = DataNomineeRequest(
        nominee_name="Arjun Sharma",
        nominee_contact="+919876543210",
        relationship="Brother",
    )
    assert valid.nominee_name == "Arjun Sharma"

def test_profile_update_age_range_validation():
    """Test 11: ProfileUpdate rejects inverted preferred age range."""
    # Inverted range raises ValidationError
    with pytest.raises(ValidationError, match="preferred_age_min cannot exceed preferred_age_max"):
        ProfileUpdate(preferred_age_min=30, preferred_age_max=22)

    # Equal min and max is permitted
    valid_equal = ProfileUpdate(preferred_age_min=25, preferred_age_max=25)
    assert valid_equal.preferred_age_min == 25
    assert valid_equal.preferred_age_max == 25

    # Valid ordered range is permitted
    valid_range = ProfileUpdate(preferred_age_min=20, preferred_age_max=30)
    assert valid_range.preferred_age_min == 20
    assert valid_range.preferred_age_max == 30

    # Only one bound provided is permitted
    valid_single = ProfileUpdate(preferred_age_min=21)
    assert valid_single.preferred_age_min == 21
    assert valid_single.preferred_age_max is None

def test_profile_public_response_dict_with_dob():
    """Test 12: ProfilePublicResponse model_validate accepts dict with 'dob' and strips it cleanly."""
    card_data = {
        "id": uuid.uuid4(),
        "full_name": "Rohan Mehra",
        "dob": safe_years_ago(28),
        "gender": "Man",
        "interested_in": "Women",
        "location_name": "Mumbai, MH",
        "bio": "Minimalist designer and coffee enthusiast.",
        "profession": "UX Lead",
        "education": "NID Ahmedabad",
        "streak_count": 12,
        "boost_points": 100,
        "kyc_status": True,
        "is_photo_veiled": False,
        "photos": ["https://media.urheart.app/users/456/moments/slot_1.webp"],
    }

    # Should not raise extra_forbidden despite extra='forbid'
    response = ProfilePublicResponse.model_validate(card_data)
    assert response.full_name == "Rohan Mehra"
    assert response.age == 28
    # Ensure dob is not present in exported schema
    assert "dob" not in response.model_dump()

def test_safe_years_ago_leap_year_handling():
    """Test 13: safe_years_ago properly handles leap day (February 29) without ValueError."""
    leap_day = date(2024, 2, 29)
    # 1 year before 2024 is 2023 (non-leap), must fallback to Feb 28
    res_non_leap = safe_years_ago(1, from_date=leap_day)
    assert res_non_leap == date(2023, 2, 28)

    # 4 years before 2024 is 2020 (leap year), retains Feb 29
    res_leap = safe_years_ago(4, from_date=leap_day)
    assert res_leap == date(2020, 2, 29)

