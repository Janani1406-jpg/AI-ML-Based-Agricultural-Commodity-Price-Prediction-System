import os
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://postgres:agri_pass@localhost/agri_db'

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime
from api.models.database import AsyncSessionLocal, RawPrice
from sqlalchemy import select
from sklearn.ensemble import RandomForestRegressor
import joblib
import json
from pathlib import Path

async def get_prices():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(RawPrice).order_by(RawPrice.date))
        rows = result.scalars().all()
        data = []
        for r in rows:
            commodity = r.commodity.value if hasattr(r.commodity, 'value') else str(r.commodity)
            data.append({
                'commodity': commodity,
                'date': pd.to_datetime(r.date),
                'price': float(r.modal_price),
            })
        return pd.DataFrame(data)

def create_features(df):
    df = df.sort_values('date').reset_index(drop=True)
    df['lag_1']  = df['price'].shift(1)
    df['lag_3']  = df['price'].shift(3)
    df['lag_7']  = df['price'].shift(7)
    df['ma_7']   = df['price'].rolling(7, min_periods=1).mean()
    df['ma_14']  = df['price'].rolling(14, min_periods=1).mean()
    df['std_7']  = df['price'].rolling(7, min_periods=1).std().fillna(0)
    df['change'] = df['price'].diff(1).fillna(0)
    df['month']  = df['date'].dt.month
    df['dow']    = df['date'].dt.dayofweek
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df = df.bfill().fillna(0)
    return df

FEATURE_COLS = ['lag_1','lag_3','lag_7','ma_7','ma_14','std_7','change','month_sin','month_cos','dow']

def train_commodity(commodity, df):
    print(f'\nTraining {commodity} ({len(df)} records)...')

    for horizon in [7, 15, 30, 90]:
        df_h = df.copy()
        df_h['target'] = df_h['price'].shift(-horizon)
        df_h = df_h.dropna(subset=['target'])

        if len(df_h) < 10:
            print(f'  Skipping horizon {horizon}d — not enough data ({len(df_h)} rows)')
            continue

        X = df_h[FEATURE_COLS].values
        y = df_h['target'].values

        split = max(1, int(len(X) * 0.8))
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]

        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)

        if len(X_val) > 0:
            preds = model.predict(X_val)
            mape = np.mean(np.abs((y_val - preds) / np.maximum(y_val, 0.01))) * 100
        else:
            mape = 0.0

        # Save model
        model_dir = Path(f'models/{commodity}/latest')
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_dir / f'rf_{horizon}d.pkl')

        metadata = {
            'commodity': commodity,
            'horizon_days': horizon,
            'feature_cols': FEATURE_COLS,
            'mape': round(mape, 2),
            'version': 'v1',
            'trained_at': str(datetime.utcnow()),
            'n_samples': len(df_h)
        }
        with open(model_dir / f'metadata_{horizon}d.json', 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f'  Horizon {horizon}d — MAPE: {mape:.2f}% — Saved!')

async def main():
    print('Loading price data from database...')
    df = await get_prices()
    print(f'Total records loaded: {len(df)}')
    print(f'Commodities: {df["commodity"].unique()}')

    for commodity in df['commodity'].unique():
        comm_df = df[df['commodity'] == commodity].copy()
        comm_df = create_features(comm_df)
        train_commodity(commodity, comm_df)

    print('\n✅ All models trained successfully!')
    print('Models saved in: backend/models/')
    print('Now go to http://localhost:3000 → Predictions to test!')

asyncio.run(main())