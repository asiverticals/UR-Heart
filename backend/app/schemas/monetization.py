from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class RazorpayOrderCreate(BaseModel):
    """Payment order creation request strictly gated by Condition C2."""
    model_config = ConfigDict(extra="forbid")

    product_identifier: str = Field(..., max_length=60, description="SKU identifier from product catalog")
    currency: Literal["INR", "USD"] = "INR"

    @field_validator("currency")
    @classmethod
    def validate_usd_allowed(cls, v: str) -> str:
        if v == "USD":
            try:
                from ..core.config import settings
            except (ImportError, ValueError):
                from backend.app.core.config import settings
            if not getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False):
                raise ValueError("USD billing is disabled under condition C2 until global milestone activation")
        return v

class WebRazorpayOrderCreate(BaseModel):
    """Payment order creation request for Web Store visitors."""
    model_config = ConfigDict(extra="forbid")

    product_identifier: str = Field(..., max_length=60, description="SKU identifier from product catalog")
    email: EmailStr = Field(..., description="Seeker registered email or guest checkout email")
    seeker_uuid: Optional[str] = Field(None, description="Optional seeker account UUID")
    currency: Literal["INR", "USD"] = "INR"

    @field_validator("currency")
    @classmethod
    def validate_usd_allowed(cls, v: str) -> str:
        if v == "USD":
            try:
                from ..core.config import settings
            except (ImportError, ValueError):
                from backend.app.core.config import settings
            if not getattr(settings, "ENABLE_GLOBAL_USD_BILLING", False):
                raise ValueError("USD billing is disabled under condition C2 until global milestone activation")
        return v


class RazorpayOrderResponse(BaseModel):
    """Server-side generated Razorpay order response payload."""
    order_id: str = Field(..., description="Authoritative Razorpay order ID (e.g., order_...)")
    amount: float = Field(..., description="Amount in INR rupees")
    amount_paise: int = Field(..., description="Amount in integer paise subunit")
    currency: str = Field("INR", description="Order currency")
    key_id: str = Field(..., description="Public Razorpay key ID")

class RazorpayPaymentVerify(BaseModel):
    """HMAC-SHA256 signature verification payload upon checkout completion."""
    model_config = ConfigDict(extra="forbid")

    razorpay_order_id: str = Field(..., max_length=150)
    razorpay_payment_id: str = Field(..., max_length=150)
    razorpay_signature: str = Field(..., max_length=256)
    product_identifier: Optional[str] = Field(None, max_length=60, description="Product identifier SKU")

class InAppPurchaseVerifyRequest(BaseModel):
    """Google Play Billing purchase token validation request."""
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(..., max_length=150)
    product_identifier: str = Field(..., max_length=60)
    purchase_token: str = Field(..., min_length=1)
    amount_gross: Decimal = Field(..., ge=0)

class AdSSVCallbackParams(BaseModel):
    """Ad network Server-Side Verification (SSV) callback query parameters."""
    model_config = ConfigDict(extra="allow")

    custom_data: str = Field(..., description="{user_id}:{ad_type}:{target_id}")
    transaction_id: str = Field(..., description="Cryptographic unique ad view ID")
    signature: Optional[str] = None
    key_id: Optional[str] = None

class WebStoreClaimPending(BaseModel):
    """Entitlement claim payload for Web Store off-platform purchases."""
    model_config = ConfigDict(extra="forbid")

    email: EmailStr = Field(..., description="Account email linked to pending purchase entitlement")

class StoreProductItem(BaseModel):
    """Product model in sovereign store catalog."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Product SKU identifier")
    title: str = Field(..., description="Product display title")
    description: str = Field(..., description="Editorial product explanation")
    product_class: str = Field(..., description="Product class: micro_perk or pass")
    inr_price: float = Field(..., description="Price in Indian Rupees (INR)")
    usd_price: Optional[float] = Field(None, description="Price in USD (gated under Condition C2)")
    currency_symbol: str = Field("₹", description="Display currency symbol")
    badge_label: Optional[str] = Field(None, description="Product badge tag")
    entitlement: Optional[str] = Field(None, description="Yield entitlement description")

class StoreCatalogResponse(BaseModel):
    """Sovereign Store active catalog response."""
    currency: str = Field("INR", description="Default billing currency")
    usd_enabled: bool = Field(False, description="Whether international USD billing is enabled")
    products: List[StoreProductItem] = Field(default_factory=list, description="Available products")

class StoreBalancesResponse(BaseModel):
    """Seeker wallet and entitlement balance response."""
    reward_balance: int = Field(0, description="Mindful reward points / coins balance")
    streak_count: int = Field(0, description="Active daily streak count")
    swipes_remaining: int = Field(25, description="Available discovery swipe balance")
    direct_letters_count: int = Field(1, description="Intentional direct letters balance")
    boost_points: int = Field(0, description="Discovery boost priority score")
    super_likes_count: int = Field(0, description="Super likes balance")
    instant_bridge_passes: int = Field(0, description="Instant contact bridge passes balance")
    subscription_tier: str = Field("free", description="Active membership tier")
    is_ad_free: bool = Field(False, description="Whether seeker enjoys ad-free experience")
