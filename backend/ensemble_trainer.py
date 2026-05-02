"""
ML Model Training Pipeline
Implements XGBoost + Random Forest + SARIMA ensemble with online learning.
"""

import numpy as np
import pandas as pd
import joblib
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

MODEL_REGISTRY_PATH = Path(os.getenv("MODEL_REGISTRY_PATH", "/app/models"))
MODEL_REGISTRY_PATH.mkdir(parents=True, exist_ok=True)

TARGET_COL = "modal_price_per_kg"
DROP_COLS = ["commodity", "date", "market", "state", "quarter_key", TARGET_COL,
             "min_price", "max_price", "arrivals_tonnes", "source", "quality_score", "scraped_at"]


class EnsembleTrainer:
    """
    Trains XGBoost, Random Forest, and SARIMA models per commodity.
    Combines them into a weighted ensemble with SHAP explainability.
    """

    def __init__(self, commodity: str, horizon_days: int = 7):
        self.commodity = commodity
        self.horizon_days = horizon_days
        self.version = datetime.utcnow().strftime("v%Y%m%d_%H%M")
        self.xgb_model = None
        self.rf_model = None
        self.sarima_model = None
        self.ensemble_weights = {"xgb": 0.40, "rf": 0.30, "sarima": 0.30}
        self.feature_cols: list[str] = []
        self.scaler = None
        self.metrics: dict = {}

    # ── Training ───────────────────────────────────────────────────────────────

    def train(self, features_df: pd.DataFrame) -> dict:
        """Full training pipeline. Returns validation metrics."""
        logger.info(f"Training ensemble for {self.commodity} (horizon={self.horizon_days}d)...")
        df = features_df[features_df["commodity"] == self.commodity].copy()
        df = df.sort_values("date").dropna(subset=[TARGET_COL])

        if len(df) < 100:
            raise ValueError(f"Insufficient data for {self.commodity}: {len(df)} rows")

        # Create target: price N days ahead
        df["target"] = df[TARGET_COL].shift(-self.horizon_days)
        df = df.dropna(subset=["target"])

        self.feature_cols = [c for c in df.columns if c not in DROP_COLS + ["target"]]
        X = df[self.feature_cols].fillna(method="ffill").fillna(0)
        y = df["target"]

        # Time-aware train/val split (last 20% for validation)
        split_idx = int(len(df) * 0.80)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

        # Train individual models
        self._train_xgboost(X_train, y_train, X_val, y_val)
        self._train_random_forest(X_train, y_train)
        self._train_sarima(df[TARGET_COL].iloc[:split_idx])

        # Optimize ensemble weights on validation set
        self._optimize_weights(X_val, y_val, df[TARGET_COL].iloc[split_idx:])

        # Final validation metrics
        preds = self._predict_ensemble(X_val, df[TARGET_COL].iloc[split_idx:])
        self.metrics = self._calculate_metrics(y_val, preds)
        logger.info(f"  {self.commodity} ensemble MAPE: {self.metrics['mape']:.2f}%")

        self._save_models()
        return self.metrics

    def _train_xgboost(self, X_train, y_train, X_val, y_val):
        import xgboost as xgb
        dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_cols)
        dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_cols)

        params = {
            "objective": "reg:squarederror",
            "n_estimators": 200,
            "max_depth": 6,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "gamma": 0.1,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "seed": 42,
        }
        evals_result = {}
        self.xgb_model = xgb.train(
            params,
            dtrain,
            num_boost_round=200,
            evals=[(dval, "val")],
            early_stopping_rounds=20,
            evals_result=evals_result,
            verbose_eval=False,
        )
        logger.info(f"    XGBoost trained. Best iteration: {self.xgb_model.best_iteration}")

    def _train_random_forest(self, X_train, y_train):
        from sklearn.ensemble import RandomForestRegressor
        self.rf_model = RandomForestRegressor(
            n_estimators=300,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features="sqrt",
            bootstrap=True,
            n_jobs=-1,
            random_state=42,
        )
        self.rf_model.fit(X_train, y_train)
        logger.info(f"    Random Forest trained.")

    def _train_sarima(self, price_series: pd.Series):
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        try:
            model = SARIMAX(
                price_series.values,
                order=(2, 1, 2),
                seasonal_order=(1, 1, 1, 30),  # 30-day seasonality
                enforce_stationarity=False,
                enforce_invertibility=False,
            )
            self.sarima_model = model.fit(disp=False, maxiter=100)
            logger.info(f"    SARIMA trained.")
        except Exception as e:
            logger.warning(f"    SARIMA training failed: {e}. Will use RF/XGB only.")
            self.sarima_model = None
            self.ensemble_weights = {"xgb": 0.55, "rf": 0.45, "sarima": 0.0}

    def _optimize_weights(self, X_val, y_val, price_series_val):
        """Grid search for optimal ensemble weights on validation set."""
        import xgboost as xgb
        from sklearn.metrics import mean_absolute_percentage_error

        xgb_preds = self.xgb_model.predict(xgb.DMatrix(X_val, feature_names=self.feature_cols))
        rf_preds = self.rf_model.predict(X_val)
        sarima_preds = self._sarima_forecast(len(X_val))

        best_mape, best_w = float("inf"), (0.4, 0.3, 0.3)
        for xw in np.arange(0.3, 0.6, 0.1):
            for rw in np.arange(0.2, 0.5, 0.1):
                sw = 1.0 - xw - rw
                if sw < 0: continue
                combined = xw * xgb_preds + rw * rf_preds + sw * sarima_preds
                mape = mean_absolute_percentage_error(y_val, combined) * 100
                if mape < best_mape:
                    best_mape, best_w = mape, (xw, rw, sw)

        self.ensemble_weights = {"xgb": best_w[0], "rf": best_w[1], "sarima": best_w[2]}
        logger.info(f"    Optimized weights: XGB={best_w[0]:.2f} RF={best_w[1]:.2f} SARIMA={best_w[2]:.2f}")

    def _predict_ensemble(self, X, price_series) -> np.ndarray:
        import xgboost as xgb
        xgb_p = self.xgb_model.predict(xgb.DMatrix(X, feature_names=self.feature_cols))
        rf_p = self.rf_model.predict(X)
        sarima_p = self._sarima_forecast(len(X))
        w = self.ensemble_weights
        return w["xgb"] * xgb_p + w["rf"] * rf_p + w["sarima"] * sarima_p

    def _sarima_forecast(self, n_steps: int) -> np.ndarray:
        if self.sarima_model is None:
            return np.zeros(n_steps)
        try:
            forecasts = self.sarima_model.forecast(steps=n_steps)
            return np.array(forecasts)
        except Exception:
            return np.zeros(n_steps)

    # ── Online Learning ────────────────────────────────────────────────────────

    def partial_fit(self, new_features_df: pd.DataFrame):
        """
        Incremental update with new data (daily online learning).
        Adds boosting rounds to XGBoost, appends trees to RF.
        """
        import xgboost as xgb
        df = new_features_df[new_features_df["commodity"] == self.commodity].copy()
        df["target"] = df[TARGET_COL].shift(-self.horizon_days)
        df = df.dropna(subset=["target"])
        X = df[self.feature_cols].fillna(0)
        y = df["target"]

        if len(X) < 5:
            logger.info(f"  Insufficient new data for {self.commodity} partial fit ({len(X)} rows). Skipping.")
            return

        # XGBoost incremental: train 10 additional rounds
        dtrain = xgb.DMatrix(X, label=y, feature_names=self.feature_cols)
        self.xgb_model = xgb.train(
            {"objective": "reg:squarederror", "learning_rate": 0.02},
            dtrain,
            num_boost_round=10,
            xgb_model=self.xgb_model,
            verbose_eval=False,
        )

        # RF: add new trees (expand forest)
        from sklearn.ensemble import RandomForestRegressor
        new_trees = RandomForestRegressor(n_estimators=10, n_jobs=-1, random_state=42)
        new_trees.fit(X, y)
        self.rf_model.estimators_ += new_trees.estimators_
        self.rf_model.n_estimators = len(self.rf_model.estimators_)

        logger.info(f"  Online learning update complete for {self.commodity}.")
        self._save_models()

    # ── Prediction ─────────────────────────────────────────────────────────────

    def predict_with_confidence(self, feature_row: pd.Series) -> dict:
        """
        Single-row prediction with confidence score and explanation.
        Returns dict with predicted_price, lower_bound, upper_bound, confidence, components.
        """
        import xgboost as xgb
        import shap

        X = feature_row[self.feature_cols].values.reshape(1, -1)
        X_df = pd.DataFrame(X, columns=self.feature_cols)

        xgb_pred = float(self.xgb_model.predict(xgb.DMatrix(X_df, feature_names=self.feature_cols))[0])
        rf_pred = float(self.rf_model.predict(X_df)[0])
        sarima_pred = float(self._sarima_forecast(1)[0]) if self.sarima_model else xgb_pred

        w = self.ensemble_weights
        ensemble_pred = w["xgb"] * xgb_pred + w["rf"] * rf_pred + w["sarima"] * sarima_pred

        # Confidence: model agreement + historical MAPE
        pred_std = np.std([xgb_pred, rf_pred, sarima_pred])
        agreement_score = max(0, 100 - (pred_std / max(ensemble_pred, 0.01) * 100))
        historical_mape = self.metrics.get("mape", 10.0)
        confidence = 0.5 * agreement_score + 0.5 * max(0, 100 - historical_mape)

        # Uncertainty bounds via bootstrap approximation
        bootstrap_std = pred_std * 1.5
        lower = ensemble_pred - 1.28 * bootstrap_std   # 80% CI
        upper = ensemble_pred + 1.28 * bootstrap_std

        # SHAP explanation (XGBoost)
        try:
            explainer = shap.TreeExplainer(self.xgb_model)
            shap_vals = explainer.shap_values(xgb.DMatrix(X_df, feature_names=self.feature_cols))
            top_features = sorted(
                zip(self.feature_cols, shap_vals[0]),
                key=lambda x: abs(x[1]), reverse=True
            )[:5]
            shap_explanation = [{"feature": f, "impact": float(v)} for f, v in top_features]
        except Exception:
            shap_explanation = []

        return {
            "predicted_price": round(ensemble_pred, 2),
            "lower_bound": round(max(0, lower), 2),
            "upper_bound": round(upper, 2),
            "confidence_score": round(confidence, 1),
            "components": {"xgb": round(xgb_pred, 2), "rf": round(rf_pred, 2), "sarima": round(sarima_pred, 2)},
            "shap_values": shap_explanation,
        }

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save_models(self):
        """Save all model artifacts to versioned directory."""
        model_dir = MODEL_REGISTRY_PATH / self.commodity / self.version
        model_dir.mkdir(parents=True, exist_ok=True)

        self.xgb_model.save_model(str(model_dir / "xgboost.ubj"))
        joblib.dump(self.rf_model, model_dir / "random_forest.pkl")
        if self.sarima_model:
            self.sarima_model.save(str(model_dir / "sarima.pkl"))

        metadata = {
            "commodity": self.commodity,
            "version": self.version,
            "horizon_days": self.horizon_days,
            "feature_cols": self.feature_cols,
            "ensemble_weights": self.ensemble_weights,
            "metrics": self.metrics,
            "saved_at": datetime.utcnow().isoformat(),
        }
        with open(model_dir / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        # Update "latest" symlink
        latest_link = MODEL_REGISTRY_PATH / self.commodity / "latest"
        if latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(model_dir)
        logger.info(f"  Models saved to {model_dir}")

    @classmethod
    def load_latest(cls, commodity: str, horizon_days: int = 7) -> "EnsembleTrainer":
        """Load the latest trained model for a commodity."""
        import xgboost as xgb
        from statsmodels.tsa.statespace.sarimax import SARIMAXResults

        model_dir = MODEL_REGISTRY_PATH / commodity / "latest"
        if not model_dir.exists():
            raise FileNotFoundError(f"No trained model found for {commodity}")

        with open(model_dir / "metadata.json") as f:
            metadata = json.load(f)

        trainer = cls(commodity, horizon_days)
        trainer.version = metadata["version"]
        trainer.feature_cols = metadata["feature_cols"]
        trainer.ensemble_weights = metadata["ensemble_weights"]
        trainer.metrics = metadata["metrics"]

        trainer.xgb_model = xgb.Booster()
        trainer.xgb_model.load_model(str(model_dir / "xgboost.ubj"))
        trainer.rf_model = joblib.load(model_dir / "random_forest.pkl")

        sarima_path = model_dir / "sarima.pkl"
        if sarima_path.exists():
            trainer.sarima_model = SARIMAXResults.load(str(sarima_path))

        return trainer

    # ── Metrics ────────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict:
        from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
        return {
            "mape": round(mean_absolute_percentage_error(y_true, y_pred) * 100, 3),
            "mae": round(mean_absolute_error(y_true, y_pred), 3),
            "rmse": round(np.sqrt(mean_squared_error(y_true, y_pred)), 3),
        }
