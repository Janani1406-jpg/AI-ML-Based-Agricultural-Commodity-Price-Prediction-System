"""
Database Models - SQLAlchemy ORM
Agricultural Commodity Price Prediction System
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:agri_pass@localhost/agri_db")

engine = create_async_engine(DATABASE_URL, pool_size=20, max_overflow=10, pool_recycle=3600, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ─── Enums ────────────────────────────────────────────────────────────────────

class CommodityEnum(str, enum.Enum):
    ONION = "onion"
    POTATO = "potato"
    TOMATO = "tomato"
    GRAM = "gram"
    TUR = "tur"
    URAD = "urad"
    MOONG = "moong"
    MASUR = "masur"


class HorizonEnum(int, enum.Enum):
    WEEK = 7
    FORTNIGHT = 15
    MONTH = 30
    QUARTER = 90


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class RiskEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ─── Models ───────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.VIEWER)
    is_active = Column(Boolean, default=True)
    totp_secret = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=datetime.utcnow)


class RawPrice(Base):
    __tablename__ = "raw_prices"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    date = Column(DateTime, nullable=False)
    market = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    modal_price = Column(Float, nullable=False)       # Rs/quintal
    min_price = Column(Float, nullable=True)
    max_price = Column(Float, nullable=True)
    arrivals_tonnes = Column(Float, nullable=True)
    source = Column(String(50), default="agmarknet")
    quality_score = Column(Float, default=100.0)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_raw_prices_commodity_date", "commodity", "date"),
        UniqueConstraint("commodity", "date", "market", name="uq_price_commodity_date_market"),
    )


class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    location = Column(String(100), nullable=False)
    state = Column(String(50), nullable=False)
    rainfall_mm = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_min_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    source = Column(String(30), default="imd")
    __table_args__ = (Index("ix_weather_date_location", "date", "location"),)


class ProductionData(Base):
    __tablename__ = "production_data"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    year = Column(Integer, nullable=False)
    quarter = Column(Integer, nullable=False)       # 1-4
    state = Column(String(50), nullable=False)
    sowing_area_ha = Column(Float, nullable=True)
    production_tonnes = Column(Float, nullable=True)
    yield_kg_per_ha = Column(Float, nullable=True)
    source = Column(String(50), default="ministry_agriculture")


class PolicyEvent(Base):
    __tablename__ = "policy_events"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    policy_type = Column(String(50), nullable=False)   # MSP, export_ban, import_duty, subsidy
    description = Column(Text)
    affected_commodities = Column(JSON)                # list of commodity names
    impact_score = Column(Float, default=5.0)          # 1-10
    source_url = Column(String(500), nullable=True)


class FestivalCalendar(Base):
    __tablename__ = "festival_calendar"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    festival_name = Column(String(100), nullable=False)
    region = Column(String(50), nullable=True)          # "national", "north", "south" etc.
    demand_multiplier = Column(Float, default=1.0)      # 1.0 = no change, 1.3 = 30% increase


class FeatureRecord(Base):
    __tablename__ = "feature_store"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    date = Column(DateTime, nullable=False)
    features = Column(JSON, nullable=False)    # dict of feature_name -> value
    feature_version = Column(String(20), default="v1")
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_features_commodity_date", "commodity", "date"),
        UniqueConstraint("commodity", "date", "feature_version", name="uq_features"),
    )


class MLModel(Base):
    __tablename__ = "ml_models"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    model_type = Column(String(30), nullable=False)    # xgboost, random_forest, sarima, ensemble
    version = Column(String(20), nullable=False)
    file_path = Column(String(500), nullable=False)
    train_date = Column(DateTime, default=datetime.utcnow)
    train_data_start = Column(DateTime)
    train_data_end = Column(DateTime)
    hyperparameters = Column(JSON)
    val_mape = Column(Float)
    val_rmse = Column(Float)
    val_mae = Column(Float)
    is_active = Column(Boolean, default=False)
    feature_importance = Column(JSON)
    __table_args__ = (Index("ix_models_commodity_type", "commodity", "model_type"),)


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    prediction_date = Column(DateTime, nullable=False)
    target_date = Column(DateTime, nullable=False)
    horizon_days = Column(Integer, nullable=False)
    scenario = Column(String(20), default="baseline")   # baseline, optimistic, pessimistic
    predicted_price = Column(Float, nullable=False)     # Rs/kg
    lower_bound = Column(Float)
    upper_bound = Column(Float)
    confidence_score = Column(Float)                    # 0-100
    xgb_prediction = Column(Float)
    rf_prediction = Column(Float)
    sarima_prediction = Column(Float)
    model_version = Column(String(20))
    shap_values = Column(JSON)
    explanation = Column(JSON)
    is_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_predictions_commodity_date", "commodity", "prediction_date"),
        Index("ix_predictions_target_date", "target_date"),
    )


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    headline = Column(String(300), nullable=False)
    detail = Column(Text)
    action_type = Column(String(50))    # release_buffer, procure, hold, monitor
    quantity_tonnes = Column(Float)
    target_markets = Column(JSON)
    expected_price_impact = Column(Float)   # Rs/kg change expected
    confidence_score = Column(Float)
    risk_level = Column(Enum(RiskEnum), default=RiskEnum.MEDIUM)
    prediction_id = Column(Integer, ForeignKey("predictions.id"))
    is_active = Column(Boolean, default=True)
    status = Column(String(30), default="pending")  # pending, approved, executed, dismissed
    executed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    execution_notes = Column(Text, nullable=True)
    actual_outcome = Column(JSON, nullable=True)
    prediction = relationship("Prediction")
    executor = relationship("User")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    commodity = Column(Enum(CommodityEnum), nullable=False)
    alert_type = Column(String(50))    # price_spike, procurement_opportunity, data_quality, model_drift
    severity = Column(String(20))      # low, medium, high, critical
    title = Column(String(300))
    message = Column(Text)
    current_price = Column(Float, nullable=True)
    predicted_price = Column(Float, nullable=True)
    pct_change = Column(Float, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(100))
    resource = Column(String(50))
    resource_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow)


# ─── DB Helpers ───────────────────────────────────────────────────────────────

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
