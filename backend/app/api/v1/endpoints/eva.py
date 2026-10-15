import logging

from fastapi import APIRouter, Depends

from ....models.domain.user import User
from ....schemas.base_response import SanctuaryResponse
from ....schemas.eva import EvaBioPolishRequest, EvaBioPolishResponse
from ....services.eva_service import EvaService
from ...deps import get_current_user

logger = logging.getLogger("urheart.eva_endpoint")

router = APIRouter()

def get_eva_service() -> EvaService:
    return EvaService()


@router.post(
    "/polish-bio",
    response_model=SanctuaryResponse[EvaBioPolishResponse],
    summary="Mindful profile bio refinement via Eva AI consciousness guide",
)
async def polish_bio(
    payload: EvaBioPolishRequest,
    current_user: User = Depends(get_current_user),
    eva_service: EvaService = Depends(get_eva_service),
) -> SanctuaryResponse[EvaBioPolishResponse]:
    """Generates authentic, intentional bio polish and contemplative reflection prompt.
    
    Preserves declared traits without algorithmic distortion.
    """
    profession = payload.profession if payload.profession is not None else current_user.profession
    education = payload.education if payload.education is not None else current_user.education

    result = await eva_service.polish_bio(
        raw_bio=payload.raw_bio,
        profession=profession,
        education=education,
    )

    response_data = EvaBioPolishResponse(
        polished_bio=result["polished_bio"],
        reflection_prompt=result["reflection_prompt"],
        engine=result.get("engine", "groq"),
    )

    return SanctuaryResponse(
        data=response_data,
        message="Eva polished bio and reflection generated successfully.",
    )
