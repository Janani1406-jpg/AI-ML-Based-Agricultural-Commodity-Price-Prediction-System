"""
Pydantic Schemas - Request/Response Validation
Agricultural Commodity Price Prediction System
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class CommodityEnum(str, Enum):
    ONION = "onion"; POTATO = "potato"; TOMATO = "tomato"; GRAM = "gram"
    TUR = "tur"; URAD = "urad"; MOONG = "moong"; MASUR = "masur"


class HorizonEnum(int, Enum):
    WEEK = 7; FORTNIGHT = 15; MONTH = 30; QUARTER = 90


class ScenarioEnum(str, Enum):
    BASELINE = "baseline"; OPTIMISTIC = "optimistic"; PESSIMISTIC = "pessimistic"


class RoleEnum(str, Enum):
    ADMIN = "admin"; ANALYST = "analyst"; VIEWER = "viewer"


# ─── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    totp_code: Optional[str] = Field(None, min_length=6, max_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: RoleEnum
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: RoleEnum = RoleEnum.VIEWER

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v): raise ValueError("Must have uppercase")
        if not any(c.islower() for c in v): raise ValueError("Must have lowercase")
        if not any(c.isdigit() for c in v): raise ValueError("Must have digit")
        return v


# ─── Predictions ──────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    commodity: CommodityEnum
    horizon_days: HorizonEnum
    scenario: ScenarioEnum = ScenarioEnum.BASELINE
    market: Optional[str] = None


class FeatureContribution(BaseModel):
    feature: str
    value: float
    impact: float     # positive = upward price pressure, negative = downward
    description: str


class PredictionResponse(BaseModel):
    id: int
    commodity: CommodityEnum
    prediction_date: datetime
    target_date: datetime
    horizon_days: int
    scenario: str
    predicted_price: float              # Rs/kg
    price_change: float                 # Rs/kg vs current
    price_change_pct: float             # % change
    lower_bound: float
    upper_bound: float
    confidence_score: float             # 0-100
    model_components: Dict[str, float]  # xgb, rf, sarima predictions
    top_factors: List[FeatureContribution]
    explanation: str
    is_flagged: bool
    created_at: datetime
    class Config: from_attributes = True


class BatchPredictionRequest(BaseModel):
    commodities: List[CommodityEnum]
    horizon_days: HorizonEnum
    scenario: ScenarioEnum = ScenarioEnum.BASELINE


# ─── Recommendations ──────────────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    id: int
    commodity: CommodityEnum
    generated_at: datetime
    headline: str
    detail: str
    action_type: str
    quantity_tonnes: Optional[float]
    target_markets: List[str]
    expected_price_impact: float
    confidence_score: float
    risk_level: str
    status: str
    is_active: bool
    class Config: from_attributes = True


class ExecuteRecommendationRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=1000)
    actual_quantity_tonnes: Optional[float] = None
    markets_covered: Optional[List[str]] = None


# ─── Commodities ──────────────────────────────────────────────────────────────

class CommodityCurrentStats(BaseModel):
    commodity: CommodityEnum
    current_price: float        # Rs/kg, latest modal price
    price_change_1d: float
    price_change_7d: float
    price_change_30d: float
    avg_arrivals_7d: float
    msp: Optional[float]
    last_updated: datetime
    sparkline: List[float]      # last 30 days prices


class PriceHistoryPoint(BaseModel):
    date: datetime
    modal_price: float
    min_price: Optional[float]
    max_price: Optional[float]
    arrivals_tonnes: Optional[float]
    market: str


class PriceHistoryResponse(BaseModel):
    commodity: CommodityEnum
    start_date: datetime
    end_date: datetime
    data: List[PriceHistoryPoint]
    total_records: int


# ─── Models ───────────────────────────────────────────────────────────────────

class ModelPerformance(BaseModel):
    commodity: CommodityEnum
    model_type: str
    version: str
    val_mape: float
    val_rmse: float
    val_mae: float
    train_date: datetime
    is_active: bool
    feature_importance: Dict[str, float]


class RetrainRequest(BaseModel):
    commodity: Optional[CommodityEnum] = None      # None = all commodities
    model_type: Optional[str] = None               # None = all models
    force: bool = False


# ─── Alerts ───────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    commodity: CommodityEnum
    alert_type: str
    severity: str
    title: str
    message: str
    current_price: Optional[float]
    predicted_price: Optional[float]
    pct_change: Optional[float]
    is_read: bool
    created_at: datetime
    class Config: from_attributes = True


# ─── Scenarios ────────────────────────────────────────────────────────────────

class ScenarioSimulationRequest(BaseModel):
    commodity: CommodityEnum
    horizon_days: HorizonEnum
    interventions: Dict[str, Any] = Field(
        default_factory=dict,
        description="e.g. {'release_buffer_tonnes': 500, 'rainfall_assumption': 'normal'}"
    )


class ScenarioSimulationResponse(BaseModel):
    commodity: CommodityEnum
    baseline_price: float
    simulated_price: float
    price_difference: float
    pct_difference: float
    interventions_applied: Dict[str, Any]
    explanation: str


# ─── Reports ──────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(weekly_summary|monthly_analysis|annual_review|custom)$")
    commodities: Optional[List[CommodityEnum]] = None   # None = all
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    format: str = Field("pdf", pattern="^(pdf|excel)$")
    include_charts: bool = True
    include_recommendations: bool = True


# ─── Data Ingestion ───────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    source: str = Field(..., pattern="^(agmarknet|imd|ministry|enam|all)$")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    commodity: Optional[CommodityEnum] = None


class DataQualityReport(BaseModel):
    source: str
    records_collected: int
    records_passed: int
    records_failed: int
    avg_quality_score: float
    issues: List[str]
    collected_at: datetime
