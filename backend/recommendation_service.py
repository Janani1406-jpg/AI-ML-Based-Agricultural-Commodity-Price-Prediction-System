"""
Recommendation Engine
Generates buffer stock recommendations based on predicted prices.

FLOW:
  Prediction → Business Rule Check → Recommendation → Official Action
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import logging

from api.models.database import Prediction, Recommendation, RiskEnum, RawPrice

logger = logging.getLogger(__name__)

# ── Priority Markets for Intervention ─────────────────────────────────────────
PRIORITY_MARKETS = [
    "Delhi", "Mumbai", "Bangalore",
    "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow"
]

# ── Buffer Stock Available (tonnes) per commodity ─────────────────────────────
BUFFER_STOCK = {
    "onion":  2500,
    "potato": 3800,
    "tomato": 800,
    "gram":   5000,
    "tur":    6200,
    "urad":   4800,
    "moong":  3100,
    "masur":  4500,
}

# ── Business Rules Configuration ──────────────────────────────────────────────
# These are the EXACT rules that trigger recommendations

BUSINESS_RULES = {
    # RULE 1: High Price Spike → Release Buffer Stock
    "release_buffer": {
        "price_increase_threshold": 12,    # Price must rise > 12%
        "confidence_threshold": 75,         # Confidence must be > 75%
        "min_buffer_stock": 500,            # Buffer stock must be > 500 tonnes
        "release_fraction": 0.30,           # Release 30% of buffer stock
        "horizon_days": 15,                 # Check 15-day prediction
    },
    # RULE 2: Price Drop → Procurement Opportunity
    "procure": {
        "price_decrease_threshold": -8,    # Price must fall > 8%
        "confidence_threshold": 70,         # Confidence must be > 70%
        "procure_fraction": 0.40,           # Procure 40% more stock
        "horizon_days": 30,                 # Check 30-day prediction
    },
    # RULE 3: Emergency Spike → Immediate Action
    "emergency": {
        "price_increase_7d": 20,           # 7-day price rise > 20%
        "price_increase_15d": 25,          # 15-day price rise > 25%
        "confidence_threshold": 80,         # Confidence must be > 80%
        "release_fraction": 0.50,           # Release 50% of buffer stock
    },
    # RULE 4: Stable Price → Monitor Only
    "monitor": {
        "stable_threshold": 5,             # Price change < 5%
    },
}

COMMODITIES = ["onion", "potato", "tomato", "gram", "tur", "urad", "moong", "masur"]


class RecommendationEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_recommendations(self) -> list:
        """Generate recommendations for all commodities."""
        all_recs = []
        for commodity in COMMODITIES:
            try:
                recs = await self._analyze_commodity(commodity)
                all_recs.extend(recs)
                logger.info(f"Generated {len(recs)} recommendations for {commodity}")
            except Exception as e:
                logger.error(f"Error generating rec for {commodity}: {e}")
        return all_recs

    async def _get_current_price(self, commodity: str) -> float:
        """Get latest market price for commodity."""
        result = await self.db.execute(
            select(RawPrice.modal_price)
            .where(RawPrice.commodity == commodity)
            .order_by(desc(RawPrice.date))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return float(row) if row else 0.0

    async def _get_prediction(self, commodity: str, horizon: int):
        """Get latest prediction for commodity and horizon."""
        result = await self.db.execute(
            select(Prediction)
            .where(
                Prediction.commodity == commodity,
                Prediction.horizon_days == horizon,
                Prediction.scenario == 'baseline',
            )
            .order_by(desc(Prediction.created_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _ensure_predictions_exist(self, commodity: str):
        """Generate predictions if they don't exist."""
        from api.services.prediction_service import PredictionService
        svc = PredictionService(self.db)
        for horizon in [7, 15, 30, 90]:
            existing = await self._get_prediction(commodity, horizon)
            if not existing:
                try:
                    await svc.generate_prediction(commodity, horizon, 'baseline')
                    logger.info(f"Generated prediction for {commodity} {horizon}d")
                except Exception as e:
                    logger.error(f"Failed to generate prediction: {e}")

    async def _analyze_commodity(self, commodity: str) -> list:
        """
        Main analysis function.
        Checks all business rules and generates recommendations.
        """
        # Ensure predictions exist
        await self._ensure_predictions_exist(commodity)

        # Get current price
        current_price = await self._get_current_price(commodity)
        if current_price == 0:
            logger.warning(f"No price data for {commodity}")
            return []

        # Get predictions for different horizons
        p7  = await self._get_prediction(commodity, 7)
        p15 = await self._get_prediction(commodity, 15)
        p30 = await self._get_prediction(commodity, 30)
        p90 = await self._get_prediction(commodity, 90)

        # Get buffer stock
        buffer_stock = BUFFER_STOCK.get(commodity, 1000)

        # Store generated recommendations
        recommendations = []

        # ── BUSINESS RULE 1: Price Spike → Release Buffer ──────────────────
        # Trigger: price increase > 12% in 15 days
        #          confidence > 75%
        #          buffer stock > 500 tonnes
        if p15 and p15.explanation:
            pct_change = p15.explanation.get("price_change_pct", 0)
            confidence = p15.confidence_score or 0
            rule = BUSINESS_RULES["release_buffer"]

            # ── BUSINESS RULE CHECK ────────────────────────────────────────
            price_check     = pct_change >= rule["price_increase_threshold"]
            confidence_check = confidence >= rule["confidence_threshold"]
            buffer_check    = buffer_stock >= rule["min_buffer_stock"]

            logger.info(
                f"\n{'='*50}\n"
                f"BUSINESS RULE CHECK for {commodity.upper()}\n"
                f"  Predicted Price  : ₹{p15.predicted_price:.2f}/kg\n"
                f"  Current Price    : ₹{current_price:.2f}/kg\n"
                f"  Price Change     : {pct_change:+.1f}%\n"
                f"  Rule 1 Checks:\n"
                f"    Price > {rule['price_increase_threshold']}%? "
                f"{'YES ✅' if price_check else 'NO ❌'} ({pct_change:.1f}%)\n"
                f"    Confidence > {rule['confidence_threshold']}%? "
                f"{'YES ✅' if confidence_check else 'NO ❌'} ({confidence:.0f}%)\n"
                f"    Buffer > {rule['min_buffer_stock']}T? "
                f"{'YES ✅' if buffer_check else 'NO ❌'} ({buffer_stock}T)\n"
                f"{'='*50}"
            )

            if price_check and confidence_check and buffer_check:
                # All conditions met → Generate recommendation
                release_qty = buffer_stock * rule["release_fraction"]
                target_markets = PRIORITY_MARKETS[:3]
                expected_impact = -(pct_change * 0.65)

                # Determine risk level
                if pct_change >= 30:
                    risk = RiskEnum.HIGH
                elif pct_change >= 20:
                    risk = RiskEnum.HIGH
                else:
                    risk = RiskEnum.MEDIUM

                rec = Recommendation(
                    commodity=commodity,
                    headline=(
                        f"⚠️ Release {release_qty:.0f} tonnes "
                        f"{commodity.title()} buffer stock IMMEDIATELY"
                    ),
                    detail=(
                        f"PREDICTION RESULT:\n"
                        f"  Current Price   : ₹{current_price:.2f}/kg\n"
                        f"  Predicted Price : ₹{p15.predicted_price:.2f}/kg "
                        f"(in 15 days)\n"
                        f"  Price Change    : {pct_change:+.1f}%\n"
                        f"  Confidence      : {confidence:.0f}%\n\n"
                        f"BUSINESS RULE CHECK:\n"
                        f"  ✅ Price increase > {rule['price_increase_threshold']}% "
                        f"→ {pct_change:.1f}% (PASSED)\n"
                        f"  ✅ Confidence > {rule['confidence_threshold']}% "
                        f"→ {confidence:.0f}% (PASSED)\n"
                        f"  ✅ Buffer stock > {rule['min_buffer_stock']} tonnes "
                        f"→ {buffer_stock} tonnes (PASSED)\n\n"
                        f"RECOMMENDED ACTION:\n"
                        f"  Release {release_qty:.0f} tonnes immediately to "
                        f"{', '.join(target_markets)}.\n"
                        f"  Expected price reduction: {abs(expected_impact):.1f}%\n"
                        f"  This will bring price from ₹{p15.predicted_price:.2f} "
                        f"down to approx "
                        f"₹{p15.predicted_price * (1 + expected_impact/100):.2f}/kg"
                    ),
                    action_type="release_buffer",
                    quantity_tonnes=round(release_qty, 0),
                    target_markets=target_markets,
                    expected_price_impact=round(expected_impact, 1),
                    confidence_score=confidence,
                    risk_level=risk,
                    prediction_id=p15.id,
                    is_active=True,
                    status="pending",
                )
                recommendations.append(rec)
                logger.info(
                    f"✅ RECOMMENDATION GENERATED: Release {release_qty:.0f}T "
                    f"for {commodity}"
                )

        # ── BUSINESS RULE 2: Procurement Opportunity ───────────────────────
        # Trigger: price decrease > 8% in 30 days
        #          confidence > 70%
        if p30 and p30.explanation:
            pct_change = p30.explanation.get("price_change_pct", 0)
            confidence = p30.confidence_score or 0
            rule = BUSINESS_RULES["procure"]

            price_check      = pct_change <= rule["price_decrease_threshold"]
            confidence_check = confidence >= rule["confidence_threshold"]

            if price_check and confidence_check:
                procure_qty = buffer_stock * rule["procure_fraction"]

                rec = Recommendation(
                    commodity=commodity,
                    headline=(
                        f"📥 Procurement Opportunity: "
                        f"{commodity.title()} price dropping {abs(pct_change):.1f}%"
                    ),
                    detail=(
                        f"PREDICTION RESULT:\n"
                        f"  Current Price   : ₹{current_price:.2f}/kg\n"
                        f"  Predicted Price : ₹{p30.predicted_price:.2f}/kg "
                        f"(in 30 days)\n"
                        f"  Price Change    : {pct_change:+.1f}%\n"
                        f"  Confidence      : {confidence:.0f}%\n\n"
                        f"BUSINESS RULE CHECK:\n"
                        f"  ✅ Price decrease > {abs(rule['price_decrease_threshold'])}% "
                        f"→ {abs(pct_change):.1f}% (PASSED)\n"
                        f"  ✅ Confidence > {rule['confidence_threshold']}% "
                        f"→ {confidence:.0f}% (PASSED)\n\n"
                        f"RECOMMENDED ACTION:\n"
                        f"  Procure {procure_qty:.0f} tonnes during price low window "
                        f"(days 20-30).\n"
                        f"  Estimated savings vs current price: "
                        f"₹{(current_price - p30.predicted_price) * procure_qty:.0f}"
                    ),
                    action_type="procure",
                    quantity_tonnes=round(procure_qty, 0),
                    target_markets=PRIORITY_MARKETS[:2],
                    expected_price_impact=0.0,
                    confidence_score=confidence,
                    risk_level=RiskEnum.LOW,
                    prediction_id=p30.id,
                    is_active=True,
                    status="pending",
                )
                recommendations.append(rec)

        # ── BUSINESS RULE 3: Emergency Price Crisis ────────────────────────
        # Trigger: 7-day rise > 20% AND 15-day rise > 25%
        #          confidence > 80%
        if p7 and p15 and p7.explanation and p15.explanation:
            pct_7d  = p7.explanation.get("price_change_pct", 0)
            pct_15d = p15.explanation.get("price_change_pct", 0)
            conf_7d = p7.confidence_score or 0
            rule    = BUSINESS_RULES["emergency"]

            crisis_check    = (
                pct_7d  >= rule["price_increase_7d"] and
                pct_15d >= rule["price_increase_15d"]
            )
            confidence_check = conf_7d >= rule["confidence_threshold"]

            if crisis_check and confidence_check:
                emergency_qty    = buffer_stock * rule["release_fraction"]
                expected_impact  = -(pct_15d * 0.70)

                rec = Recommendation(
                    commodity=commodity,
                    headline=(
                        f"🚨 EMERGENCY: {commodity.title()} price crisis — "
                        f"IMMEDIATE action required!"
                    ),
                    detail=(
                        f"CRITICAL PRICE SPIKE DETECTED:\n"
                        f"  Current Price   : ₹{current_price:.2f}/kg\n"
                        f"  7-day Prediction: ₹{p7.predicted_price:.2f}/kg "
                        f"(+{pct_7d:.1f}%)\n"
                        f"  15-day Prediction: ₹{p15.predicted_price:.2f}/kg "
                        f"(+{pct_15d:.1f}%)\n\n"
                        f"BUSINESS RULE CHECK:\n"
                        f"  ✅ 7-day rise > {rule['price_increase_7d']}% "
                        f"→ {pct_7d:.1f}% (PASSED)\n"
                        f"  ✅ 15-day rise > {rule['price_increase_15d']}% "
                        f"→ {pct_15d:.1f}% (PASSED)\n"
                        f"  ✅ Confidence > {rule['confidence_threshold']}% "
                        f"→ {conf_7d:.0f}% (PASSED)\n\n"
                        f"EMERGENCY ACTION:\n"
                        f"  Release {emergency_qty:.0f} tonnes IMMEDIATELY "
                        f"across all metro markets.\n"
                        f"  Also consider: Import duty reduction, "
                        f"MSP adjustment,\n"
                        f"  Inter-state movement facilitation.\n"
                        f"  Expected price impact: {abs(expected_impact):.1f}% reduction"
                    ),
                    action_type="release_buffer",
                    quantity_tonnes=round(emergency_qty, 0),
                    target_markets=PRIORITY_MARKETS[:5],
                    expected_price_impact=round(expected_impact, 1),
                    confidence_score=conf_7d,
                    risk_level=RiskEnum.HIGH,
                    prediction_id=p7.id,
                    is_active=True,
                    status="pending",
                )
                recommendations.append(rec)

        # ── BUSINESS RULE 4: Stable Prices → Monitor ──────────────────────
        # Trigger: price change < 5% in 7 days
        # Only add if no other recommendations were generated
        if not recommendations and p7 and p7.explanation:
            pct_change  = p7.explanation.get("price_change_pct", 0)
            confidence  = p7.confidence_score or 0
            rule        = BUSINESS_RULES["monitor"]

            if abs(pct_change) < rule["stable_threshold"]:
                rec = Recommendation(
                    commodity=commodity,
                    headline=(
                        f"✅ {commodity.title()} prices stable — "
                        f"Continue monitoring"
                    ),
                    detail=(
                        f"PREDICTION RESULT:\n"
                        f"  Current Price   : ₹{current_price:.2f}/kg\n"
                        f"  Predicted Price : ₹{p7.predicted_price:.2f}/kg "
                        f"(in 7 days)\n"
                        f"  Price Change    : {pct_change:+.1f}%\n"
                        f"  Confidence      : {confidence:.0f}%\n\n"
                        f"BUSINESS RULE CHECK:\n"
                        f"  ✅ Price change < {rule['stable_threshold']}% "
                        f"→ {abs(pct_change):.1f}% (STABLE)\n\n"
                        f"NO INTERVENTION REQUIRED:\n"
                        f"  Market is stable. Continue daily monitoring.\n"
                        f"  Next review: {(datetime.utcnow() + timedelta(days=7)).strftime('%d %b %Y')}"
                    ),
                    action_type="monitor",
                    quantity_tonnes=0,
                    target_markets=[],
                    expected_price_impact=0.0,
                    confidence_score=confidence,
                    risk_level=RiskEnum.LOW,
                    prediction_id=p7.id,
                    is_active=True,
                    status="pending",
                )
                recommendations.append(rec)

        # Save all recommendations to database
        for rec in recommendations:
            self.db.add(rec)
        await self.db.commit()

        return recommendations

    async def simulate_intervention(
        self, commodity: str, release_tonnes: float, horizon_days: int
    ) -> dict:
        """
        What-if simulator: estimate price impact of releasing buffer stock.
        Price elasticity of supply = 0.3 (standard economic model)
        """
        pred = await self._get_prediction(commodity, horizon_days)
        if not pred:
            return {"error": "No prediction found for simulation"}

        current_price = await self._get_current_price(commodity)
        avg_daily_arrivals = 500  # tonnes/day (approximate)

        supply_increase_pct = (
            release_tonnes / (avg_daily_arrivals * horizon_days)
        ) * 100

        # Price reduction based on elasticity
        price_reduction_pct = supply_increase_pct * 0.30
        simulated_price     = pred.predicted_price * (1 - price_reduction_pct / 100)
        simulated_price     = max(1.0, simulated_price)

        return {
            "commodity": commodity,
            "current_price": round(current_price, 2),
            "baseline_predicted_price": round(pred.predicted_price, 2),
            "simulated_price": round(simulated_price, 2),
            "price_difference": round(simulated_price - pred.predicted_price, 2),
            "pct_difference": round(-price_reduction_pct, 2),
            "supply_increase_pct": round(supply_increase_pct, 2),
            "interventions_applied": {
                "release_tonnes": release_tonnes,
                "horizon_days": horizon_days,
            },
            "explanation": (
                f"Releasing {release_tonnes:.0f} tonnes increases supply by "
                f"{supply_increase_pct:.1f}%, reducing predicted price by "
                f"~{price_reduction_pct:.1f}% "
                f"(from ₹{pred.predicted_price:.2f} to ₹{simulated_price:.2f}/kg)."
            ),
        }