# 🌾 AgriPrice Intelligence System
**AI-ML Agricultural Commodity Price Prediction — Full Stack Implementation**

Government of India · Ministry of Consumer Affairs, Food & Public Distribution

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Data Collection (AGMARKNET, IMD, Ministry, eNAM)      │
│  LAYER 2: Preprocessing & Cleaning (Airflow DAGs)               │
│  LAYER 3: Feature Engineering (50+ features)                    │
│  LAYER 4: ML Models (XGBoost + Random Forest + SARIMA ensemble) │
│  LAYER 5: Prediction Engine (multi-horizon + confidence)        │
│  LAYER 6: Recommendation Engine (buffer stock decisions)        │
│  LAYER 7: FastAPI Backend (REST API + JWT auth)                 │
│  LAYER 8: React Frontend Dashboard                              │
└─────────────────────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
agri-price-system/
├── backend/
│   ├── main.py                          # FastAPI application entry point
│   ├── requirements.txt
│   ├── api/
│   │   ├── models/database.py           # SQLAlchemy ORM models
│   │   ├── schemas/schemas.py           # Pydantic validation schemas
│   │   ├── routes/
│   │   │   ├── auth.py                  # JWT authentication
│   │   │   ├── predictions.py           # Prediction endpoints
│   │   │   ├── recommendations.py       # Recommendation endpoints
│   │   │   └── commodities.py           # Commodity data endpoints
│   │   ├── services/
│   │   │   ├── prediction_service.py    # Prediction business logic
│   │   │   └── recommendation_service.py# Recommendation engine
│   │   └── dependencies.py             # Shared FastAPI dependencies
│   ├── ml/
│   │   ├── features/feature_engineer.py # 50+ feature generation
│   │   └── training/ensemble_trainer.py # XGBoost+RF+SARIMA ensemble
│   ├── data/
│   │   └── collectors/scrapers.py       # AGMARKNET & IMD scrapers
│   └── dags/
│       └── agri_pipeline_dags.py        # Airflow DAG definitions
├── frontend/
│   ├── package.json
│   └── src/
│       ├── App.jsx                      # Router + auth context
│       ├── utils/api.js                 # Authenticated API client
│       ├── styles/globals.css           # Global design system
│       └── pages/
│           ├── Dashboard.jsx            # Main dashboard with commodity cards
│           ├── PredictionsPage.jsx      # Prediction form + results + SHAP
│           ├── RecommendationsPage.jsx  # Buffer stock recommendations
│           ├── CommodityDetail.jsx      # Commodity detail with charts
│           ├── ReportsPage.jsx          # Report generation
│           ├── AdminPage.jsx            # Model management + data pipeline
│           └── LoginPage.jsx            # JWT authentication
├── docker/
│   ├── backend/Dockerfile
│   ├── frontend/Dockerfile
│   └── nginx/nginx.conf
└── docker-compose.yml
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB RAM minimum (ML models)
- Python 3.11+ (for local dev)
- Node.js 18+ (for frontend dev)

### 1. Clone & Configure

```bash
git clone <repo-url>
cd agri-price-system
cp .env.example .env
# Edit .env: set JWT_SECRET, IMD_API_KEY, DATA_GOV_API_KEY
```

### 2. Start All Services

```bash
docker-compose up -d
```

Services will start at:
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **pgAdmin (DB)**: http://localhost:5050

### 3. Initialize Database & Seed Data

```bash
docker-compose exec backend python scripts/init_db.py
docker-compose exec backend python scripts/seed_demo_data.py
```

### 4. Train Initial Models

```bash
docker-compose exec backend python scripts/train_initial_models.py
```
*(Takes ~30-60 min for all 8 commodities × 4 horizons × 3 model types)*

### 5. Login

Default credentials:
| Username | Password | Role |
|----------|----------|------|
| admin | Admin@123 | Admin |
| analyst1 | Analyst@123 | Analyst |
| viewer1 | Viewer@123 | Viewer |

---

## 🔧 Local Development

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+asyncpg://agri_user:agri_pass@localhost/agri_db"
export JWT_SECRET="dev-secret-key-min-32-characters!!"
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000/api npm start
```

### Run Data Pipeline Manually

```bash
# Collect today's prices
python -c "
import asyncio
from data.collectors.scrapers import AGMARKNETScraper
from datetime import date
scraper = AGMARKNETScraper()
records = asyncio.run(scraper.fetch_prices('onion', date.today(), date.today()))
print(f'Collected {len(records)} records')
"

# Run feature engineering
python -c "
from ml.features.feature_engineer import FeatureEngineer
# ... load data and run engineer.engineer_all_features(...)
"
```

---

## 📊 ML Model Details

### Ensemble Architecture

```
Input Features (50+)
        │
   ┌────┴────┬──────────┐
   ▼         ▼          ▼
XGBoost   RandomForest  SARIMA
(40%)      (30%)        (30%)
   │         │          │
   └────┬────┘          │
        ▼               │
   Weighted Ensemble ◄──┘
        │
   Final Prediction + Confidence Score + SHAP Explanation
```

### Feature Categories

| Category | Count | Examples |
|----------|-------|---------|
| Temporal | 12 | month_sin/cos, day_of_week, is_festival_season |
| Lag features | 9 | price_lag_1/7/14/30, arrivals_lag_7 |
| Rolling stats | 20 | price_ma_7/30, price_std_7, EWMA |
| Momentum | 8 | price_change_1d, RSI_14, Bollinger position |
| Weather | 8 | rainfall_7d_sum, GDD, weather_anomaly |
| Production | 4 | prod_yoy_growth, sowing_area_change |
| Market | 4 | arrival_anomaly, supply_demand_ratio |
| Policy | 3 | days_since_policy, msp_distance |
| Festival | 3 | days_to_festival, demand_multiplier |
| Interaction | 3 | rainfall_temp, supply_festival |

### Model Performance Targets

| Metric | Target | Typical |
|--------|--------|---------|
| MAPE | < 12% | 7–10% |
| MAE | < ₹2/kg | ₹1.5–2.5 |
| Confidence (high) | > 80% | 82–91% |

---

## 🔐 Security

- **JWT Authentication**: 1-hour access tokens, 7-day refresh tokens
- **TOTP 2FA**: Optional for admin accounts (Google Authenticator)
- **RBAC**: Admin > Analyst > Viewer role hierarchy
- **Rate Limiting**: 100 req/hr per user via slowapi
- **Input Validation**: Pydantic schemas on all endpoints
- **SQL Injection**: SQLAlchemy parameterized queries only
- **Audit Logging**: All user actions logged with IP and timestamp

---

## 📡 API Reference

Full Swagger docs at `/docs`. Key endpoints:

```
POST  /auth/login                    → Get JWT tokens
POST  /api/predictions/create        → Generate price prediction
GET   /api/predictions/latest/{c}    → Latest predictions for commodity
POST  /api/predictions/batch         → Batch predictions
GET   /api/recommendations/active    → Active buffer stock recommendations
POST  /api/recommendations/generate  → Generate new recommendations
PUT   /api/recommendations/{id}/execute → Execute a recommendation
GET   /api/commodities/{c}/history   → Price history with date range
POST  /api/scenarios/simulate        → What-if scenario analysis
POST  /api/data/ingest               → Trigger data collection
POST  /api/models/retrain            → Trigger model retraining
GET   /api/alerts/active             → Active price alerts
POST  /api/reports/generate          → Generate PDF/Excel report
GET   /health/detailed               → System health metrics
```

---

## 🔄 Scheduled Jobs (Airflow)

| DAG | Schedule | Description |
|-----|----------|-------------|
| `agri_data_collection` | Every 6h | Scrape AGMARKNET, fetch IMD weather |
| `agri_predictions_update` | Every 4h | Refresh all predictions + alerts |
| `agri_model_training` | Daily | Online learning; full retrain on Sunday |

---

## 🧪 Testing

```bash
# Backend unit tests
cd backend && pytest tests/ -v --cov=. --cov-report=html

# Frontend tests
cd frontend && npm test -- --watchAll=false

# Load testing (100 concurrent users)
cd tests && locust -f locustfile.py --headless -u 100 -r 10 --run-time 60s
```

---

## 📈 Monitoring

- **Prometheus** metrics: http://localhost:9090
- **Grafana** dashboards: http://localhost:3001
- Key metrics tracked: API latency p95, prediction MAPE drift, data freshness, error rates

---

## 🤝 Commodities Supported

| Commodity | MSP | Seasonality | Key Growing States |
|-----------|-----|-------------|-------------------|
| Onion | No | Rabi/Kharif | Maharashtra, Karnataka |
| Potato | No | Rabi | UP, West Bengal |
| Tomato | No | Year-round | AP, Karnataka |
| Gram (Chana) | Yes | Rabi | MP, Rajasthan |
| Tur Dal | Yes | Kharif | Maharashtra, Karnataka |
| Urad Dal | Yes | Kharif | MP, Rajasthan |
| Moong Dal | Yes | Kharif/Zaid | Rajasthan, UP |
| Masur Dal | Yes | Rabi | UP, MP |

---

*Built for Ministry of Consumer Affairs, Food & Public Distribution · Government of India*
