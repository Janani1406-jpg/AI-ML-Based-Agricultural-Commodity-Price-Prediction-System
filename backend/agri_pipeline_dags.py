"""
Apache Airflow DAGs
Orchestrates data collection, preprocessing, feature engineering, and model updates.
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

# ── Default args shared by all DAGs ───────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "agri_system",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

COMMODITIES = ["onion", "potato", "tomato", "gram", "tur", "urad", "moong", "masur"]


# ══════════════════════════════════════════════════════════════════════════════
# DAG 1: Data Collection  (every 6 hours)
# ══════════════════════════════════════════════════════════════════════════════

def collect_agmarknet_prices(**ctx):
    from data.collectors.scrapers import AGMARKNETScraper, DataValidator, DataPreprocessor
    import pandas as pd
    from datetime import date

    scraper = AGMARKNETScraper()
    validator = DataValidator()
    preprocessor = DataPreprocessor()

    all_records = []
    target_date = ctx["ds_nodash"]
    fetch_date = date.fromisoformat(ctx["ds"])

    for commodity in COMMODITIES:
        try:
            records = asyncio.run(scraper.fetch_prices(commodity, fetch_date, fetch_date))
            valid, issues = validator.validate_prices(records)
            if issues:
                logger.warning(f"Validation issues for {commodity}: {issues[:3]}")
            all_records.extend(valid)
            logger.info(f"Collected {len(valid)} records for {commodity}")
        except Exception as e:
            logger.error(f"Failed collecting {commodity}: {e}")

    if all_records:
        df = pd.DataFrame(all_records)
        df = preprocessor.preprocess_prices(df)
        # Save to DB via SQLAlchemy (synchronous version for Airflow)
        _save_prices_to_db(df)
        logger.info(f"Total: {len(df)} price records saved.")
    return len(all_records)


def collect_weather_data(**ctx):
    from data.collectors.scrapers import IMDWeatherCollector
    from datetime import date

    collector = IMDWeatherCollector()
    fetch_date = date.fromisoformat(ctx["ds"])
    records = asyncio.run(collector.fetch_weather(fetch_date, fetch_date))
    _save_weather_to_db(records)
    logger.info(f"Weather: {len(records)} records saved.")
    return len(records)


def run_preprocessing(**ctx):
    """Clean and standardize all raw data collected today."""
    from data.collectors.scrapers import DataPreprocessor
    import pandas as pd

    preprocessor = DataPreprocessor()
    raw_df = _load_raw_prices_from_db(days=2)
    if raw_df.empty:
        logger.warning("No raw data to preprocess.")
        return 0
    cleaned = preprocessor.preprocess_prices(raw_df)
    _save_cleaned_prices(cleaned)
    return len(cleaned)


def run_feature_engineering(**ctx):
    """Generate ML features from cleaned data."""
    from ml.features.feature_engineer import FeatureEngineer
    import pandas as pd

    engineer = FeatureEngineer()
    prices = _load_clean_prices(days=365)
    weather = _load_weather(days=365)
    production = _load_production()
    policies = _load_policies()

    if prices.empty:
        logger.warning("No clean prices for feature engineering.")
        return

    features = engineer.engineer_all_features(prices, weather, production, policies)
    _save_features(features)
    logger.info(f"Feature engineering: {len(features)} feature records generated.")


with DAG(
    dag_id="agri_data_collection",
    description="Collect, validate, and preprocess agricultural price data every 6 hours",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */6 * * *",      # Every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["data", "collection"],
) as data_collection_dag:

    collect_prices_task = PythonOperator(
        task_id="collect_agmarknet_prices",
        python_callable=collect_agmarknet_prices,
    )

    collect_weather_task = PythonOperator(
        task_id="collect_weather_data",
        python_callable=collect_weather_data,
    )

    preprocess_task = PythonOperator(
        task_id="run_preprocessing",
        python_callable=run_preprocessing,
    )

    feature_eng_task = PythonOperator(
        task_id="run_feature_engineering",
        python_callable=run_feature_engineering,
    )

    trigger_predictions = TriggerDagRunOperator(
        task_id="trigger_predictions_update",
        trigger_dag_id="agri_predictions_update",
        wait_for_completion=False,
    )

    [collect_prices_task, collect_weather_task] >> preprocess_task >> feature_eng_task >> trigger_predictions


# ══════════════════════════════════════════════════════════════════════════════
# DAG 2: Predictions Update  (every 4 hours)
# ══════════════════════════════════════════════════════════════════════════════

def update_predictions(**ctx):
    """Generate fresh predictions for all commodities and horizons."""
    from ml.training.ensemble_trainer import EnsembleTrainer
    import pandas as pd

    results = []
    for commodity in COMMODITIES:
        for horizon in [7, 15, 30, 90]:
            try:
                trainer = EnsembleTrainer.load_latest(commodity, horizon)
                features = _load_latest_features(commodity)
                if features is None:
                    continue
                prediction = trainer.predict_with_confidence(features)
                _save_prediction(commodity, horizon, prediction)
                results.append({"commodity": commodity, "horizon": horizon, "price": prediction["predicted_price"]})
            except FileNotFoundError:
                logger.warning(f"No model for {commodity} horizon={horizon}, skipping.")
            except Exception as e:
                logger.error(f"Prediction error {commodity}/{horizon}: {e}")

    logger.info(f"Updated {len(results)} predictions.")

    # Check for alerts
    _check_and_create_alerts(results)
    return len(results)


def update_recommendations(**ctx):
    """Generate buffer stock recommendations based on latest predictions."""
    # In production: call recommendation engine
    logger.info("Updating buffer stock recommendations...")


with DAG(
    dag_id="agri_predictions_update",
    description="Update price predictions and recommendations every 4 hours",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 */4 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["predictions", "recommendations"],
) as predictions_dag:

    update_preds_task = PythonOperator(
        task_id="update_predictions",
        python_callable=update_predictions,
    )

    update_recs_task = PythonOperator(
        task_id="update_recommendations",
        python_callable=update_recommendations,
    )

    update_preds_task >> update_recs_task


# ══════════════════════════════════════════════════════════════════════════════
# DAG 3: Model Training  (weekly + online learning daily)
# ══════════════════════════════════════════════════════════════════════════════

def online_learning_update(**ctx):
    """Daily incremental model update with new data."""
    from ml.training.ensemble_trainer import EnsembleTrainer

    new_data = _load_clean_prices(days=2)
    if new_data.empty:
        return

    for commodity in COMMODITIES:
        for horizon in [7, 15, 30, 90]:
            try:
                trainer = EnsembleTrainer.load_latest(commodity, horizon)
                trainer.partial_fit(new_data)
                logger.info(f"Online learning update: {commodity} horizon={horizon}")
            except FileNotFoundError:
                logger.warning(f"No model to update for {commodity}/{horizon}")
            except Exception as e:
                logger.error(f"Online learning error {commodity}/{horizon}: {e}")


def full_retrain(**ctx):
    """Weekly full model retraining on 2 years of data."""
    from ml.training.ensemble_trainer import EnsembleTrainer

    features = _load_clean_prices(days=730)
    for commodity in COMMODITIES:
        for horizon in [7, 15, 30, 90]:
            try:
                trainer = EnsembleTrainer(commodity, horizon)
                metrics = trainer.train(features)
                logger.info(f"Full retrain {commodity}/{horizon}: MAPE={metrics['mape']:.2f}%")
                _save_model_metadata(commodity, trainer)
            except Exception as e:
                logger.error(f"Full retrain error {commodity}/{horizon}: {e}", exc_info=True)


with DAG(
    dag_id="agri_model_training",
    description="Online learning daily, full retrain weekly",
    default_args=DEFAULT_ARGS,
    schedule_interval="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["ml", "training"],
) as training_dag:

    online_update_task = PythonOperator(
        task_id="online_learning_update",
        python_callable=online_learning_update,
    )

    # Full retrain only on Sundays (day_of_week=0)
    full_retrain_task = PythonOperator(
        task_id="full_retrain_if_sunday",
        python_callable=full_retrain,
        # In production: use ShortCircuitOperator to check day_of_week
    )

    online_update_task >> full_retrain_task


# ── DB helper stubs (replace with actual SQLAlchemy sync calls in production) ──

def _save_prices_to_db(df): pass
def _save_weather_to_db(records): pass
def _load_raw_prices_from_db(days=2): import pandas as pd; return pd.DataFrame()
def _save_cleaned_prices(df): pass
def _load_clean_prices(days=365): import pandas as pd; return pd.DataFrame()
def _load_weather(days=365): import pandas as pd; return pd.DataFrame()
def _load_production(): import pandas as pd; return pd.DataFrame()
def _load_policies(): import pandas as pd; return pd.DataFrame()
def _save_features(features): pass
def _load_latest_features(commodity): return None
def _save_prediction(commodity, horizon, pred): pass
def _check_and_create_alerts(results): pass
def _save_model_metadata(commodity, trainer): pass
