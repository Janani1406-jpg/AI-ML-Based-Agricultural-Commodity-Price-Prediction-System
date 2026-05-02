"""
fetch_tamilnadu_prices.py
=========================
Fetches REAL-TIME commodity prices for Tamil Nadu from:
  1. data.gov.in  (Agmarknet API - official government source)
  2. agmarknet.gov.in (direct scraping fallback)

Filters ONLY Tamil Nadu markets. No other states.
Saves to PostgreSQL database (raw_prices table).

Run:
    python fetch_tamilnadu_prices.py
"""

import os
import asyncio
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── Database URL ──────────────────────────────────────────────────────────────
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:agri_pass@localhost/agri_db"
)

# ── Tamil Nadu Commodity Mapping ──────────────────────────────────────────────
# Maps your DB commodity names → Agmarknet commodity names
COMMODITIES = {
    "onion":  "Onion",
    "potato": "Potato",
    "tomato": "Tomato",
    "gram":   "Gram(Split)",
    "tur":    "Arhar (Tur/Red Gram)(Whole)",
    "urad":   "Black Gram (Urd Beans)(Whole)",
    "moong":  "Green Gram (Moong)(Whole)",
    "masur":  "Lentil (Masur)(Whole)",
}

# Major Tamil Nadu APMC markets (Agmarknet codes)
TAMIL_NADU_MARKETS = [
    "Chennai",
    "Coimbatore",
    "Madurai",
    "Salem",
    "Trichy",
    "Tirunelveli",
    "Erode",
    "Vellore",
    "Thanjavur",
    "Tirupur",
    "Kancheepuram",
    "Dindigul",
    "Krishnagiri",
    "Hosur",
    "Namakkal",
    "Karur",
    "Kumbakonam",
    "Pollachi",
]

STATE = "Tamil Nadu"


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1:  data.gov.in  Agmarknet API  (official, free, no key needed)
# ══════════════════════════════════════════════════════════════════════════════

DATA_GOV_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
DATA_GOV_API_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aae38d975ea6dfed92"
# ↑ This is a public demo key. For production get your free key at:
#   https://data.gov.in/user/register


def fetch_from_datagov(
    commodity_agmark: str,
    from_date: str,
    to_date: str,
    limit: int = 5000,
) -> pd.DataFrame:
    """
    Fetch prices from data.gov.in Agmarknet dataset.
    Returns a DataFrame with columns: market, modal_price, min_price, max_price,
    arrivals_tonnes, date, commodity, state.
    """
    params = {
        "api-key":  DATA_GOV_API_KEY,
        "format":   "json",
        "limit":    limit,
        "filters[state]":     STATE,
        "filters[commodity]": commodity_agmark,
        "filters[arrival_date][gte]": from_date,   # e.g. "01/01/2024"
        "filters[arrival_date][lte]": to_date,
    }
    try:
        r = requests.get(DATA_GOV_URL, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        records = data.get("records", [])
        if not records:
            log.warning(f"  data.gov.in → 0 records for {commodity_agmark}")
            return pd.DataFrame()

        df = pd.DataFrame(records)
        # Rename columns
        df = df.rename(columns={
            "arrival_date": "date",
            "market":       "market",
            "modal_price":  "modal_price",
            "min_price":    "min_price",
            "max_price":    "max_price",
            "commodity":    "commodity_raw",
            "state":        "state",
        })

        # Keep only Tamil Nadu rows (already filtered by API, but double-check)
        df = df[df["state"].str.lower() == "tamil nadu"]

        # Parse date
        df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y", errors="coerce")
        df = df.dropna(subset=["date"])

        # Convert price columns (Agmarknet reports in ₹ per quintal → convert to ₹/kg)
        for col in ["modal_price", "min_price", "max_price"]:
            df[col] = pd.to_numeric(df[col], errors="coerce") / 100  # quintal→kg

        # arrivals is in tonnes in some versions, quintals in others
        if "arrivals_in_qtls" in df.columns:
            df["arrivals_tonnes"] = pd.to_numeric(df["arrivals_in_qtls"], errors="coerce") / 10
        else:
            df["arrivals_tonnes"] = 0.0

        df = df.dropna(subset=["modal_price"])
        log.info(f"  data.gov.in → {len(df)} rows for {commodity_agmark}")
        return df

    except Exception as e:
        log.error(f"  data.gov.in error for {commodity_agmark}: {e}")
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2:  Agmarknet direct (scrape fallback)
# ══════════════════════════════════════════════════════════════════════════════

AGMARKNET_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"


def fetch_from_agmarknet(commodity_agmark: str, date_str: str) -> pd.DataFrame:
    """
    Scrape today's price from agmarknet.gov.in for Tamil Nadu.
    date_str format: "DD-MMM-YYYY" e.g. "01-Apr-2025"
    """
    from io import StringIO
    payload = {
        "Tx_State":     "TN",       # Tamil Nadu state code
        "Tx_District":  "0",        # 0 = all districts
        "Tx_Market":    "0",        # 0 = all markets
        "Tx_Commodity": commodity_agmark,
        "Tx_Variety":   "0",
        "Tx_Grade":     "0",
        "Tx_Year":      date_str.split("-")[2],
        "Tx_Month":     date_str.split("-")[1],
        "Tx_Date":      date_str.split("-")[0],
        "Tx_Frm_Date":  date_str,
        "Tx_To_Date":   date_str,
        "Tx_Fr_Date":   date_str,
        "DateFrom":     date_str,
        "DateTo":       date_str,
        "Fr_Date":      date_str,
        "To_Date":      date_str,
    }
    try:
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        r = session.post(AGMARKNET_URL, data=payload, timeout=30)
        r.raise_for_status()
        tables = pd.read_html(StringIO(r.text))
        for t in tables:
            if "Modal Price" in " ".join(str(c) for c in t.columns):
                t.columns = [str(c).strip() for c in t.columns]
                t = t.rename(columns={
                    "Market Name":  "market",
                    "Modal Price":  "modal_price",
                    "Min Price":    "min_price",
                    "Max Price":    "max_price",
                    "Arrivals (Tonnes)": "arrivals_tonnes",
                })
                # Prices in ₹/quintal → ₹/kg
                for col in ["modal_price", "min_price", "max_price"]:
                    if col in t.columns:
                        t[col] = pd.to_numeric(t[col], errors="coerce") / 100
                t["date"] = pd.to_datetime(date_str, format="%d-%b-%Y")
                t = t.dropna(subset=["modal_price"])
                log.info(f"  agmarknet.gov.in → {len(t)} rows for {commodity_agmark}")
                return t
    except Exception as e:
        log.error(f"  agmarknet.gov.in error for {commodity_agmark}: {e}")
    return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE SAVE
# ══════════════════════════════════════════════════════════════════════════════

async def save_to_db(rows: list[dict]):
    """Upsert price rows into the raw_prices table."""
    from api.models.database import AsyncSessionLocal, RawPrice
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        saved = 0
        skipped = 0
        for row in rows:
            # Check duplicate
            existing = await db.execute(
                select(RawPrice).where(
                    RawPrice.commodity == row["commodity"],
                    RawPrice.date == row["date"],
                    RawPrice.market == row["market"],
                    RawPrice.state == STATE,
                )
            )
            if existing.scalars().first():
                skipped += 1
                continue

            rec = RawPrice(
                commodity=row["commodity"],
                date=row["date"],
                market=row["market"],
                state=STATE,
                modal_price=row["modal_price"],
                min_price=row.get("min_price", row["modal_price"] - 1),
                max_price=row.get("max_price", row["modal_price"] + 1),
                arrivals_tonnes=row.get("arrivals_tonnes", 0.0),
                source="agmarknet_live",
                quality_score=95.0,
            )
            db.add(rec)
            saved += 1

        await db.commit()
        log.info(f"  DB: saved={saved}, skipped(dup)={skipped}")
        return saved


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN FETCH PIPELINE
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_and_save(days_back: int = 90):
    """
    Fetch last `days_back` days of Tamil Nadu prices for all 8 commodities.
    """
    to_dt   = datetime.now()
    from_dt = to_dt - timedelta(days=days_back)

    from_date_gov = from_dt.strftime("%d/%m/%Y")
    to_date_gov   = to_dt.strftime("%d/%m/%Y")

    total_saved = 0

    for db_name, agmark_name in COMMODITIES.items():
        log.info(f"\n{'='*55}")
        log.info(f"  Fetching: {db_name.upper()} ({agmark_name})")
        log.info(f"  Range: {from_date_gov} → {to_date_gov}")
        log.info(f"{'='*55}")

        df = fetch_from_datagov(agmark_name, from_date_gov, to_date_gov)

        # Fallback: try agmarknet for today only
        if df.empty:
            today_agmark = to_dt.strftime("%d-%b-%Y")
            df = fetch_from_agmarknet(agmark_name, today_agmark)

        if df.empty:
            log.warning(f"  No data found for {db_name}. Skipping.")
            continue

        # Build rows
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "commodity":       db_name,
                "date":            r["date"],
                "market":          str(r.get("market", "Tamil Nadu")).strip(),
                "modal_price":     float(r["modal_price"]),
                "min_price":       float(r.get("min_price", r["modal_price"])),
                "max_price":       float(r.get("max_price", r["modal_price"])),
                "arrivals_tonnes": float(r.get("arrivals_tonnes", 0) or 0),
            })

        saved = await save_to_db(rows)
        total_saved += saved

    log.info(f"\n✅ Done! Total new records saved: {total_saved}")
    return total_saved


# ══════════════════════════════════════════════════════════════════════════════
#  STANDALONE MODE  (run without DB — print to screen for verification)
# ══════════════════════════════════════════════════════════════════════════════

def preview_live_prices():
    """
    Quick preview of live Tamil Nadu prices. No DB needed.
    Run: python fetch_tamilnadu_prices.py --preview
    """
    print("\n🌾 LIVE TAMIL NADU COMMODITY PRICES (Agmarknet)")
    print("=" * 65)

    today    = datetime.now()
    from_dt  = today - timedelta(days=7)
    from_str = from_dt.strftime("%d/%m/%Y")
    to_str   = today.strftime("%d/%m/%Y")

    results = []
    for db_name, agmark_name in COMMODITIES.items():
        df = fetch_from_datagov(agmark_name, from_str, to_str, limit=50)
        if not df.empty:
            latest = df.sort_values("date", ascending=False).iloc[0]
            results.append({
                "Commodity": db_name.capitalize(),
                "Market":    str(latest.get("market", "TN"))[:20],
                "Price(₹/kg)": f"₹{latest['modal_price']:.2f}",
                "Date":      latest["date"].strftime("%d %b %Y"),
            })
        else:
            results.append({
                "Commodity":   db_name.capitalize(),
                "Market":      "—",
                "Price(₹/kg)": "API unavailable",
                "Date":        "—",
            })

    df_out = pd.DataFrame(results)
    print(df_out.to_string(index=False))
    print("\n📌 Source: data.gov.in → Agmarknet (Tamil Nadu only)")


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEDULED DAILY FETCH  (auto-updates DB every day at 9 AM)
# ══════════════════════════════════════════════════════════════════════════════

async def run_scheduler():
    """Run fetch every 24 hours. Keep this running in background."""
    import time
    log.info("🕐 Scheduler started — will fetch Tamil Nadu prices daily at 9 AM")
    while True:
        now = datetime.now()
        # Next 9 AM
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)
        wait_sec = (next_run - now).total_seconds()
        log.info(f"  Next fetch in {wait_sec/3600:.1f} hours ({next_run.strftime('%d %b %Y %H:%M')})")
        await asyncio.sleep(wait_sec)
        log.info("⏰ Daily fetch starting...")
        await fetch_and_save(days_back=2)   # last 2 days to catch any missing


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if "--preview" in sys.argv:
        # Quick test — no DB needed
        preview_live_prices()

    elif "--schedule" in sys.argv:
        # Run as daily scheduler
        asyncio.run(run_scheduler())

    else:
        # Default: fetch last 90 days and save to DB
        days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
        log.info(f"🌾 Fetching Tamil Nadu prices for last {days} days...")
        asyncio.run(fetch_and_save(days_back=days))