from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime
from typing import List
import logging

from api.models.database import get_db, Recommendation, Prediction, RiskEnum
from api.dependencies import get_current_user, require_role

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/active")
async def get_active_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Recommendation)
        .order_by(desc(Recommendation.generated_at))
        .limit(50)
    )
    recs = result.scalars().all()
    return [format_rec(r) for r in recs]


@router.post("/generate")
async def generate_recommendations(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    from api.services.recommendation_service import RecommendationEngine
    engine = RecommendationEngine(db)
    recs = await engine.generate_recommendations()
    return {
        "generated": len(recs),
        "message": f"Generated {len(recs)} recommendations."
    }


@router.put("/{rec_id}/execute")
async def execute_recommendation(
    rec_id: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = "executed"
    rec.executed_by = current_user.id
    rec.executed_at = datetime.utcnow()
    rec.execution_notes = payload.get("notes", "")
    await db.commit()
    return {"success": True, "message": "Recommendation executed successfully."}


@router.put("/{rec_id}/dismiss")
async def dismiss_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    result = await db.execute(
        select(Recommendation).where(Recommendation.id == rec_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    rec.status = "dismissed"
    rec.is_active = False
    await db.commit()
    return {"success": True}


def format_rec(r):
    return {
        "id": r.id,
        "commodity": r.commodity if isinstance(r.commodity, str) else r.commodity.value,
        "generated_at": r.generated_at,
        "headline": r.headline,
        "detail": r.detail,
        "action_type": r.action_type,
        "quantity_tonnes": r.quantity_tonnes,
        "target_markets": r.target_markets or [],
        "expected_price_impact": r.expected_price_impact,
        "confidence_score": r.confidence_score,
        "risk_level": r.risk_level if isinstance(r.risk_level, str) else r.risk_level.value,
        "status": r.status,
        "is_active": r.is_active,
    }