from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import logging

from api.models.database import get_db, Prediction
from api.services.prediction_service import PredictionService
from api.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create")
async def create_prediction(
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = PredictionService(db)
    try:
        prediction = await service.generate_prediction(
            commodity=req.get("commodity"),
            horizon_days=req.get("horizon_days", 7),
            scenario=req.get("scenario", "baseline"),
            requested_by=current_user.id,
        )
        return prediction
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(500, f"Failed to generate prediction: {str(e)}")


@router.post("/batch")
async def batch_predict(
    req: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = PredictionService(db)
    results = []
    commodities = req.get("commodities", [])
    horizon = req.get("horizon_days", 7)
    scenario = req.get("scenario", "baseline")

    for commodity in commodities:
        try:
            pred = await service.generate_prediction(commodity, horizon, scenario, current_user.id)
            results.append(pred)
        except Exception as e:
            results.append({"commodity": commodity, "error": str(e)})
    return {"predictions": results, "count": len(results)}


@router.get("/latest/{commodity}")
async def get_latest_predictions(
    commodity: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Prediction)
        .where(Prediction.commodity == commodity)
        .order_by(desc(Prediction.created_at))
        .limit(4)
    )
    predictions = result.scalars().all()
    if not predictions:
        service = PredictionService(db)
        preds = []
        for horizon in [7, 15, 30, 90]:
            try:
                pred = await service.generate_prediction(commodity, horizon, "baseline")
                preds.append(pred)
            except Exception as e:
                logger.error(f"Error: {e}")
        return preds
    return [
        {
            "id": p.id,
            "commodity": p.commodity,
            "horizon_days": p.horizon_days,
            "predicted_price": p.predicted_price,
            "lower_bound": p.lower_bound,
            "upper_bound": p.upper_bound,
            "confidence_score": p.confidence_score,
            "scenario": p.scenario,
            "explanation": p.explanation,
            "is_flagged": p.is_flagged,
            "prediction_date": p.prediction_date,
            "target_date": p.target_date,
            "created_at": p.created_at,
        }
        for p in predictions
    ]


@router.get("/{prediction_id}")
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(
        select(Prediction).where(Prediction.id == prediction_id)
    )
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(404, "Prediction not found")
    return prediction