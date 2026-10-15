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
