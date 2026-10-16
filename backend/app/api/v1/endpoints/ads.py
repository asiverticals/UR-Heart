import hashlib
import hmac
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import SanctuaryException
from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....services.ad_ssv_service import ad_ssv_service
from ...deps import get_current_user

logger = logging.getLogger("SanctuaryAdsRouter")

router = APIRouter()


@router.get("/status")
async def get_ad_cooldown_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Returns seeker 15-second anti-bot cooling state and daily velocity cap status."""
    status_data = await ad_ssv_service.get_user_ad_status(current_user, session)
    return status_data


@router.get("/ssv/admob", status_code=status.HTTP_200_OK)
async def admob_ssv_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Google AdMob Server-Side Verification (SSV) callback endpoint."""
    query_params = dict(request.query_params)
    is_valid = await ad_ssv_service.verify_admob_ssv(
        query_params,
        raw_query_string=request.url.query,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic AdMob SSV signature verification failed",
        )

    transaction_id = query_params.get("transaction_id") or query_params.get("trans_id") or ""
    custom_data = query_params.get("custom_data") or ""

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network="admob",
            transaction_id=transaction_id,
            custom_data=custom_data,
            session=session,
        )
        return {"status": "ok", "result": result}
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)


@router.get("/ssv/meta", status_code=status.HTTP_200_OK)
async def meta_ssv_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Meta Audience Network Server-Side Verification (SSV) callback endpoint."""
    query_params = dict(request.query_params)
    is_valid = ad_ssv_service.verify_meta_ssv(query_params)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic Meta SSV signature verification failed",
        )

    transaction_id = query_params.get("transaction_id") or query_params.get("trans_id") or ""
    custom_data = query_params.get("custom_data") or ""

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network="meta",
            transaction_id=transaction_id,
            custom_data=custom_data,
            session=session,
        )
        return {"status": "ok", "result": result}
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)


@router.get("/ssv/unity", status_code=status.HTTP_200_OK)
async def unity_ssv_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Unity Ads Server-Side Verification (SSV) callback endpoint."""
    query_params = dict(request.query_params)
    is_valid = ad_ssv_service.verify_unity_ssv(query_params)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic Unity SSV signature verification failed",
        )

    transaction_id = query_params.get("oid") or query_params.get("transaction_id") or ""
    custom_data = query_params.get("sid") or query_params.get("custom_data") or ""

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network="unity",
            transaction_id=transaction_id,
            custom_data=custom_data,
            session=session,
        )
        return {"status": "ok", "result": result}
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)


@router.get("/ssv/liftoff", status_code=status.HTTP_200_OK)
async def liftoff_ssv_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Liftoff (Vungle) Server-Side Verification (SSV) callback endpoint."""
    query_params = dict(request.query_params)
    is_valid = ad_ssv_service.verify_liftoff_ssv(query_params)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic Liftoff SSV signature verification failed",
        )

    transaction_id = query_params.get("transaction_id") or query_params.get("tx_id") or ""
    custom_data = query_params.get("custom_data") or query_params.get("user_id") or ""

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network="liftoff",
            transaction_id=transaction_id,
            custom_data=custom_data,
            session=session,
        )
        return {"status": "ok", "result": result}
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)


@router.get("/ssv/chartboost", status_code=status.HTTP_200_OK)
async def chartboost_ssv_callback(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Chartboost Server-Side Verification (SSV) callback endpoint."""
    query_params = dict(request.query_params)
    is_valid = ad_ssv_service.verify_chartboost_ssv(query_params)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cryptographic Chartboost SSV signature verification failed",
        )

    transaction_id = query_params.get("trans_id") or query_params.get("transaction_id") or ""
    custom_data = query_params.get("custom_data") or query_params.get("user_id") or ""

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network="chartboost",
            transaction_id=transaction_id,
            custom_data=custom_data,
            session=session,
        )
        return {"status": "ok", "result": result}
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)


@router.post("/claim-reward", status_code=status.HTTP_200_OK)
async def claim_ad_reward(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SanctuaryResponse[Dict[str, Any]]:
    """Client-facing claim endpoint for completed rewarded ads.
    Requires server-verifiable completion proof or an independently authenticated SSV record.
    """
    import json
    from sqlalchemy import select
    from ....core.config import settings
    from ....models.domain.monetization import ProcessedAdTransaction

    transaction_id = payload.get("transaction_id")
    if not transaction_id or not isinstance(transaction_id, str) or len(transaction_id.strip()) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid, non-empty transaction_id is required to claim an ad reward.",
        )

    clean_tx = transaction_id.strip()

    # 1. Check if an independently authenticated SSV record already exists for this transaction
    stmt = select(ProcessedAdTransaction).where(
        ProcessedAdTransaction.transaction_id == clean_tx,
        ProcessedAdTransaction.user_id == current_user.id,
    )
    existing_res = await session.execute(stmt)
    existing_tx = existing_res.scalar_one_or_none()
    if existing_tx:
        return SanctuaryResponse(
            data={"status": "already_processed", "transaction_id": clean_tx, "ad_type": existing_tx.ad_type},
            message="Reward already verified and credited via authenticated SSV.",
        )

    ad_type = str(payload.get("ad_type", "extra_swipes"))

    # 2. In production, unverified client claims without verified cryptographic proof or existing SSV record must be rejected
    completion_proof = payload.get("completion_proof") or payload.get("ssv_token")
    if settings.ENVIRONMENT == "production":
        is_verified = False
        if completion_proof and isinstance(completion_proof, str):
            key = (settings.SECRET_KEY or settings.JWT_SECRET_KEY or "").encode("utf-8")
            expected_sig = hmac.new(
                key,
                f"{current_user.id}:{clean_tx}:{ad_type}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            is_verified = hmac.compare_digest(expected_sig, completion_proof.strip())
        if not is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unverified ad completion claim: Independent server-side SSV record or valid cryptographic proof is required.",
            )
    # Restrict network to client-claimed flow to prevent forging server-to-server SSV origins
    network = "client_reward"
    custom_data = json.dumps({"user_id": str(current_user.id), "ad_type": ad_type})

    try:
        result = await ad_ssv_service.fulfill_ssv_reward(
            network=network,
            transaction_id=clean_tx,
            custom_data=custom_data,
            session=session,
        )

        res_status = result.get("status")
        if res_status in ("rejected_cooling", "rejected_daily_limit"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Reward claim rate limited: {res_status}",
            )

        return SanctuaryResponse(
            data={"status": "ok", "result": result, "reward_balance": current_user.reward_balance},
            message="Reward successfully claimed.",
        )
    except SanctuaryException as se:
        if se.status_code == 429:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=se.message)
        raise HTTPException(status_code=se.status_code or 400, detail=se.message)

