"""
API Routes: Commodities, Models, Alerts, Data Ingestion, Reports
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timedelta
from typing import Optional, List

from api.models.database import get_db, RawPrice, MLModel, Alert
from api.dependencies import get_current_user, require_role

# ── Commodities ───────────────────────────────────────────────────────────────
router = APIRouter()   # Will be registered as commodities router

@router.get("/stats/all")
async def get_all_stats(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Return current stats summary for all commodities."""
    from api.models.database import CommodityEnum
    results = []
    for commodity in CommodityEnum:
        try:
            stats = await _get_commodity_stats(db, commodity.value)
            results.append(stats)
        except Exception:
            pass
    return results

@router.get("/{commodity}/stats")
async def get_commodity_stats(commodity: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    return await _get_commodity_stats(db, commodity)

async def _get_commodity_stats(db, commodity: str) -> dict:
    now = datetime.utcnow()
    recent = await db.execute(
        select(RawPrice).where(RawPrice.commodity == commodity)
        .order_by(desc(RawPrice.date)).limit(90)
    )
    rows = recent.scalars().all()
    if not rows:
        return {"commodity": commodity, "current_price": None}
    latest = rows[0]
    sparkline = [r.modal_price for r in reversed(rows[:30])]
    prev_day = rows[1].modal_price if len(rows) > 1 else None
    prev_7d = rows[6].modal_price if len(rows) > 6 else None
    prev_30d = rows[29].modal_price if len(rows) > 29 else None
    cp = latest.modal_price
    return {
        "commodity": commodity,
        "current_price": cp,
        "price_change_1d": (cp - prev_day) if prev_day else None,
        "price_change_7d": (cp - prev_7d) if prev_7d else None,
        "price_change_30d": (cp - prev_30d) if prev_30d else None,
        "avg_arrivals_7d": sum(r.arrivals_tonnes or 0 for r in rows[:7]) / 7,
        "last_updated": latest.date,
        "sparkline": sparkline,
    }

@router.get("/{commodity}/history")
async def get_price_history(
    commodity: str, days: int = Query(90, ge=1, le=730),
    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
):
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(RawPrice).where(RawPrice.commodity == commodity, RawPrice.date >= cutoff)
        .order_by(desc(RawPrice.date)).limit(1000)
    )
    rows = result.scalars().all()
    return {
        "commodity": commodity,
        "start_date": cutoff,
        "end_date": datetime.utcnow(),
        "data": [{"date": r.date, "modal_price": r.modal_price, "min_price": r.min_price,
                  "max_price": r.max_price, "arrivals_tonnes": r.arrivals_tonnes, "market": r.market}
                 for r in rows],
        "total_records": len(rows),
    }


# ── These will be imported as separate routers in main.py ─────────────────────

def make_models_router():
    r = APIRouter()

    @r.get("/performance")
    async def model_performance(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
        result = await db.execute(select(MLModel).where(MLModel.is_active == True))
        return result.scalars().all()

    @r.post("/retrain")
    async def retrain_models(payload: dict, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
        from api.services.training_service import trigger_retraining
        import asyncio
        asyncio.create_task(trigger_retraining(payload.get("commodity"), payload.get("model_type"), db))
        return {"message": "Retraining triggered in background.", "status": "queued"}

    return r


def make_alerts_router():
    r = APIRouter()

    @r.get("/active")
    async def get_active_alerts(
        commodity: Optional[str] = None,
        db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)
    ):
        q = select(Alert).where(Alert.is_read == False).order_by(desc(Alert.created_at)).limit(50)
        if commodity:
            q = q.where(Alert.commodity == commodity)
        result = await db.execute(q)
        return result.scalars().all()

    @r.put("/{alert_id}/read")
    async def mark_alert_read(alert_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
        result = await db.execute(select(Alert).where(Alert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert: raise HTTPException(404)
        alert.is_read = True
        await db.commit()
        return {"success": True}

    return r


def make_data_router():
    r = APIRouter()

    @r.post("/ingest")
    async def trigger_ingest(payload: dict, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("analyst"))):
        from data.collectors.scrapers import AGMARKNETScraper, IMDWeatherCollector
        source = payload.get("source", "all")
        return {"message": f"Data ingestion triggered for source: {source}", "status": "queued"}

    @r.get("/quality")
    async def data_quality(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
        result = await db.execute(
            select(func.avg(RawPrice.quality_score), func.count(RawPrice.id))
            .where(RawPrice.date >= datetime.utcnow() - timedelta(days=1))
        )
        avg_score, count = result.one()
        return {"avg_quality_score": avg_score, "records_today": count, "status": "healthy" if (avg_score or 0) > 70 else "warning"}

    return r


def make_reports_router():
    r = APIRouter()

    @r.post("/generate")
    async def generate_report(payload: dict, current_user=Depends(get_current_user)):
        # In production: enqueue report generation job, return download URL
        return {
            "report_id": "rpt_20250101_001",
            "status": "queued",
            "download_url": "/api/reports/download/rpt_20250101_001",
            "estimated_seconds": 30,
        }

    return r
