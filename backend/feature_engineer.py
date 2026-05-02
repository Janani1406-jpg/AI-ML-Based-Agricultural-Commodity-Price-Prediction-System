"""
Feature Engineering Pipeline
Generates 50+ features from cleaned agricultural data for ML models.
"""

import pandas as pd
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)

COMMODITIES = ["onion", "potato", "tomato", "gram", "tur", "urad", "moong", "masur"]

# Festival calendar with demand multipliers
FESTIVALS = [
    {"month": 10, "day_range": (1, 31), "name": "Navratri/Diwali", "multiplier": 1.35},
    {"month": 4, "day_range": (1, 15), "name": "Ugadi/Bihu", "multiplier": 1.15},
    {"month": 8, "day_range": (15, 31), "name": "Raksha Bandhan/Onam", "multiplier": 1.20},
    {"month": 1, "day_range": (10, 20), "name": "Makar Sankranti/Pongal", "multiplier": 1.18},
    {"month": 3, "day_range": (20, 31), "name": "Holi", "multiplier": 1.12},
]

# MSP values (Rs/quintal) — updated annually
MSP_VALUES = {
    "gram": 5440, "tur": 7000, "urad": 6950, "moong": 8558, "masur": 6425,
    "onion": None, "potato": None, "tomato": None,  # No MSP for vegetables
}


class FeatureEngineer:
    """
    Transforms cleaned price, weather, production, and calendar data
    into ML-ready feature vectors for each (commodity, date) pair.
    """

    def __init__(self):
        self.feature_names: list[str] = []

    def engineer_all_features(
        self,
        prices_df: pd.DataFrame,
        weather_df: pd.DataFrame,
        production_df: pd.DataFrame,
        policies_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Main entry point: merges all data sources and generates features.
        Returns DataFrame indexed by (commodity, date) with all features.
        """
        logger.info("Starting feature engineering pipeline...")
        features_list = []

        for commodity in COMMODITIES:
            logger.info(f"  Engineering features for {commodity}...")
            comm_prices = prices_df[prices_df["commodity"] == commodity].copy()
            if comm_prices.empty:
                logger.warning(f"  No price data for {commodity}, skipping.")
                continue

            comm_features = self._engineer_commodity_features(
                commodity, comm_prices, weather_df, production_df, policies_df
            )
            features_list.append(comm_features)

        if not features_list:
            raise ValueError("No features generated — check data pipelines.")

        all_features = pd.concat(features_list, ignore_index=True)
        self.feature_names = [c for c in all_features.columns if c not in ["commodity", "date"]]
        logger.info(f"Feature engineering complete: {len(self.feature_names)} features for {len(all_features)} records.")
        return all_features

    def _engineer_commodity_features(
        self,
        commodity: str,
        prices: pd.DataFrame,
        weather: pd.DataFrame,
        production: pd.DataFrame,
        policies: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generates all features for a single commodity."""
        df = prices.sort_values("date").copy()
        df["commodity"] = commodity

        # ── 1. Temporal Features ───────────────────────────────────────────
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_month"] = df["date"].dt.day
        df["month"] = df["date"].dt.month
        df["quarter"] = df["date"].dt.quarter
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
        df["year"] = df["date"].dt.year
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["is_month_start"] = df["date"].dt.is_month_start.astype(int)
        df["is_month_end"] = df["date"].dt.is_month_end.astype(int)

        # Cyclical encoding for month and day_of_week
        df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)
        df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)

        # ── 2. Lag Features ────────────────────────────────────────────────
        price_col = "modal_price_per_kg"
        for lag in [1, 2, 3, 7, 14, 21, 30, 60, 90]:
            df[f"price_lag_{lag}"] = df[price_col].shift(lag)

        for lag in [1, 7, 14, 30]:
            df[f"arrivals_lag_{lag}"] = df["arrivals_tonnes"].shift(lag)

        # ── 3. Rolling Statistics ──────────────────────────────────────────
        for window in [7, 14, 30, 60]:
            df[f"price_ma_{window}"] = df[price_col].rolling(window, min_periods=1).mean()
            df[f"price_std_{window}"] = df[price_col].rolling(window, min_periods=1).std()
            df[f"price_min_{window}"] = df[price_col].rolling(window, min_periods=1).min()
            df[f"price_max_{window}"] = df[price_col].rolling(window, min_periods=1).max()
            df[f"arrivals_ma_{window}"] = df["arrivals_tonnes"].rolling(window, min_periods=1).mean()

        # Exponentially weighted moving averages
        for span in [7, 14, 30]:
            df[f"price_ewma_{span}"] = df[price_col].ewm(span=span, adjust=False).mean()

        # ── 4. Momentum / Velocity Features ───────────────────────────────
        df["price_change_1d"] = df[price_col].diff(1)
        df["price_change_7d"] = df[price_col].diff(7)
        df["price_change_14d"] = df[price_col].diff(14)
        df["price_change_30d"] = df[price_col].diff(30)
        df["price_pct_change_1d"] = df[price_col].pct_change(1)
        df["price_pct_change_7d"] = df[price_col].pct_change(7)
        df["price_velocity"] = df["price_change_1d"].rolling(7, min_periods=1).mean()
        df["price_acceleration"] = df["price_velocity"].diff(1)

        # Bollinger band position (price vs MA±σ)
        df["bb_upper_30"] = df["price_ma_30"] + 2 * df["price_std_30"]
        df["bb_lower_30"] = df["price_ma_30"] - 2 * df["price_std_30"]
        bb_range = (df["bb_upper_30"] - df["bb_lower_30"]).replace(0, np.nan)
        df["bb_position"] = (df[price_col] - df["bb_lower_30"]) / bb_range

        # Relative Strength Index (14-day RSI)
        df["rsi_14"] = self._compute_rsi(df[price_col], period=14)

        # ── 5. Weather Features ────────────────────────────────────────────
        if not weather.empty:
            weather_agg = weather.groupby("date").agg(
                rainfall_mm=("rainfall_mm", "mean"),
                temp_max_c=("temp_max_c", "mean"),
                temp_min_c=("temp_min_c", "mean"),
                humidity_pct=("humidity_pct", "mean"),
            ).reset_index()
            df = df.merge(weather_agg, on="date", how="left")
        else:
            for col in ["rainfall_mm", "temp_max_c", "temp_min_c", "humidity_pct"]:
                df[col] = np.nan

        df["temp_range"] = df["temp_max_c"] - df["temp_min_c"]
        df["rainfall_7d_sum"] = df["rainfall_mm"].rolling(7, min_periods=1).sum()
        df["rainfall_30d_sum"] = df["rainfall_mm"].rolling(30, min_periods=1).sum()

        # Growing degree days (base 10°C)
        mean_temp = (df["temp_max_c"] + df["temp_min_c"]) / 2
        df["gdd_daily"] = (mean_temp - 10).clip(lower=0)
        df["gdd_30d"] = df["gdd_daily"].rolling(30, min_periods=1).sum()

        # Weather anomaly (vs historical monthly mean)
        monthly_rain_mean = df.groupby("month")["rainfall_mm"].transform("mean")
        df["rainfall_anomaly"] = df["rainfall_mm"] - monthly_rain_mean

        # ── 6. Production Features ─────────────────────────────────────────
        if not production.empty:
            comm_prod = production[production["commodity"] == commodity].copy()
            if not comm_prod.empty:
                comm_prod = comm_prod.sort_values(["year", "quarter"])
                comm_prod["prod_yoy_growth"] = comm_prod["production_tonnes"].pct_change(4)  # vs same quarter last year
                comm_prod["sowing_area_change"] = comm_prod["sowing_area_ha"].pct_change(1)
                comm_prod["yield_per_ha"] = comm_prod["production_tonnes"] / comm_prod["sowing_area_ha"].replace(0, np.nan)
                # Map to daily rows by quarter
                df["quarter_key"] = df["year"].astype(str) + "_Q" + df["quarter"].astype(str)
                comm_prod["quarter_key"] = comm_prod["year"].astype(str) + "_Q" + comm_prod["quarter"].astype(str)
                prod_features = comm_prod[["quarter_key", "prod_yoy_growth", "sowing_area_change", "yield_per_ha"]]
                df = df.merge(prod_features, on="quarter_key", how="left")
            else:
                df["prod_yoy_growth"] = np.nan
                df["sowing_area_change"] = np.nan
                df["yield_per_ha"] = np.nan
        else:
            df["prod_yoy_growth"] = np.nan
            df["sowing_area_change"] = np.nan
            df["yield_per_ha"] = np.nan

        # ── 7. Market / Supply-Demand Features ────────────────────────────
        arrivals_mean_30 = df["arrivals_ma_30"].replace(0, np.nan)
        df["arrival_anomaly"] = (df["arrivals_tonnes"] - arrivals_mean_30) / arrivals_mean_30
        df["supply_demand_ratio"] = df["arrivals_tonnes"] / arrivals_mean_30

        # Price spread (if multi-market data — simplified here)
        df["price_vs_ma30"] = (df[price_col] - df["price_ma_30"]) / df["price_ma_30"].replace(0, np.nan)

        # MSP distance
        msp = MSP_VALUES.get(commodity)
        if msp is not None:
            df["msp_price_rkg"] = msp / 100  # Rs/kg
            df["msp_distance"] = df[price_col] - df["msp_price_rkg"]
        else:
            df["msp_price_rkg"] = np.nan
            df["msp_distance"] = np.nan

        # ── 8. Policy Features ─────────────────────────────────────────────
        if not policies.empty:
            comm_policies = policies[
                policies["affected_commodities"].apply(lambda x: commodity in (x or []))
            ].copy()
            if not comm_policies.empty:
                df["days_since_policy"] = df["date"].apply(
                    lambda d: self._days_since_last_event(d, comm_policies["date"])
                )
                df["policy_impact_score"] = df["date"].apply(
                    lambda d: self._nearest_event_value(d, comm_policies, "impact_score", window_days=30)
                )
            else:
                df["days_since_policy"] = 999
                df["policy_impact_score"] = 0.0
        else:
            df["days_since_policy"] = 999
            df["policy_impact_score"] = 0.0

        # ── 9. Festival Proximity Features ─────────────────────────────────
        df["days_to_festival"] = df["date"].apply(self._days_to_next_festival)
        df["festival_demand_multiplier"] = df["date"].apply(self._festival_demand_multiplier)
        df["is_festival_season"] = (df["days_to_festival"] <= 30).astype(int)

        # ── 10. Interaction Features ───────────────────────────────────────
        df["rainfall_temp_interaction"] = df["rainfall_mm"] * df["temp_max_c"]
        df["supply_festival_interaction"] = df["arrival_anomaly"] * df["festival_demand_multiplier"]
        df["price_weather_lag_interaction"] = df["price_lag_7"] * df["rainfall_anomaly"]

        return df

    # ── Helper Methods ─────────────────────────────────────────────────────────

    @staticmethod
    def _compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period, min_periods=1).mean()
        loss = (-delta.clip(upper=0)).rolling(period, min_periods=1).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _days_since_last_event(current_date, event_dates: pd.Series) -> float:
        past_events = event_dates[event_dates <= current_date]
        if past_events.empty:
            return 999.0
        return (current_date - past_events.max()).days

    @staticmethod
    def _nearest_event_value(current_date, events_df, value_col, window_days=30) -> float:
        nearby = events_df[
            (events_df["date"] >= current_date - pd.Timedelta(days=window_days)) &
            (events_df["date"] <= current_date + pd.Timedelta(days=window_days))
        ]
        if nearby.empty:
            return 0.0
        return nearby[value_col].max()

    @staticmethod
    def _days_to_next_festival(current_date) -> int:
        min_days = 999
        for fest in FESTIVALS:
            fest_date = current_date.replace(
                month=fest["month"],
                day=(fest["day_range"][0] + fest["day_range"][1]) // 2
            )
            if fest_date < current_date:
                try:
                    fest_date = fest_date.replace(year=current_date.year + 1)
                except ValueError:
                    pass
            days = (fest_date - current_date).days
            if 0 <= days < min_days:
                min_days = days
        return min_days

    @staticmethod
    def _festival_demand_multiplier(current_date) -> float:
        for fest in FESTIVALS:
            if current_date.month == fest["month"]:
                d_range = fest["day_range"]
                if d_range[0] <= current_date.day <= d_range[1]:
                    return fest["multiplier"]
        return 1.0
