"""
Data Collection Pipeline
Scrapers for AGMARKNET, IMD Weather, Ministry of Agriculture, and eNAM.
"""

import asyncio
import aiohttp
import logging
import re
from datetime import datetime, date, timedelta
from typing import Optional
from bs4 import BeautifulSoup
import pandas as pd
import time

logger = logging.getLogger(__name__)

COMMODITY_CODES = {
    "onion": "23", "potato": "24", "tomato": "78", "gram": "3",
    "tur": "4", "urad": "8", "moong": "6", "masur": "5",
}

RETRY_CONFIG = {"max_retries": 3, "base_delay": 2, "backoff": 2}


async def _retry_request(session, url, **kwargs):
    """Async HTTP GET with exponential backoff."""
    for attempt in range(RETRY_CONFIG["max_retries"]):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30), **kwargs) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"HTTP {resp.status} for {url} (attempt {attempt+1})")
        except Exception as e:
            logger.error(f"Request failed for {url}: {e} (attempt {attempt+1})")
        delay = RETRY_CONFIG["base_delay"] * (RETRY_CONFIG["backoff"] ** attempt)
        await asyncio.sleep(delay)
    return None


class AGMARKNETScraper:
    """
    Scrapes price data from AGMARKNET (agmarknet.gov.in).
    Fetches modal price, min/max price, and arrivals per market.
    """

    BASE_URL = "https://agmarknet.gov.in/SearchCmmMkt.aspx"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; AgriBot/1.0; +https://gov.in)",
        "Accept": "text/html,application/xhtml+xml",
    }

    async def fetch_prices(
        self, commodity: str, start_date: date, end_date: date, state: Optional[str] = None
    ) -> list[dict]:
        """
        Fetches price records for a commodity and date range.
        Returns list of dicts with keys: commodity, date, market, state, modal_price, min_price, max_price, arrivals_tonnes.
        """
        commodity_code = COMMODITY_CODES.get(commodity)
        if not commodity_code:
            raise ValueError(f"Unknown commodity: {commodity}")

        all_records = []
        current = start_date
        async with aiohttp.ClientSession(headers=self.HEADERS) as session:
            while current <= end_date:
                records = await self._fetch_date(session, commodity, commodity_code, current, state)
                all_records.extend(records)
                current += timedelta(days=1)
                await asyncio.sleep(0.5)  # Respectful crawl delay

        logger.info(f"AGMARKNET: Fetched {len(all_records)} records for {commodity} ({start_date} to {end_date})")
        return all_records

    async def _fetch_date(self, session, commodity, code, fetch_date, state):
        params = {
            "Tx_Commodity": code,
            "Tx_State": state or "0",
            "Tx_District": "0",
            "Tx_Market": "0",
            "DateFrom": fetch_date.strftime("%d-%b-%Y"),
            "DateTo": fetch_date.strftime("%d-%b-%Y"),
            "Fr_Date": fetch_date.strftime("%d-%b-%Y"),
            "To_Date": fetch_date.strftime("%d-%b-%Y"),
            "Tx_Trend": "0",
            "Tx_CommodityHead": commodity.title(),
            "Tx_StateHead": "--Select--",
            "Tx_DistrictHead": "--Select--",
            "Tx_MarketHead": "--Select--",
        }
        url = self.BASE_URL + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        html = await _retry_request(session, url)
        if not html:
            return []
        return self._parse_price_table(html, commodity, fetch_date)

    @staticmethod
    def _parse_price_table(html: str, commodity: str, fetch_date: date) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table", id="cphBody_GridPriceData")
        if not table:
            return []

        records = []
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) < 8:
                continue
            try:
                record = {
                    "commodity": commodity,
                    "date": datetime.combine(fetch_date, datetime.min.time()),
                    "state": cells[0],
                    "market": cells[2],
                    "min_price": float(cells[4].replace(",", "")) / 100 if cells[4] else None,  # Rs/kg
                    "max_price": float(cells[5].replace(",", "")) / 100 if cells[5] else None,
                    "modal_price_per_kg": float(cells[6].replace(",", "")) / 100 if cells[6] else None,
                    "arrivals_tonnes": float(cells[7].replace(",", "")) if cells[7] else None,
                    "source": "agmarknet",
                    "quality_score": 95.0,
                }
                if record["modal_price_per_kg"] and record["modal_price_per_kg"] > 0:
                    records.append(record)
            except (ValueError, IndexError) as e:
                logger.debug(f"Parse error in row: {e}")
        return records


class IMDWeatherCollector:
    """
    Fetches weather data from IMD Open Data API.
    Covers rainfall, temperature, humidity for major agricultural districts.
    """

    API_BASE = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    API_KEY = "your-data-gov-in-api-key"    # Set via environment variable

    AGRI_DISTRICTS = [
        "Nashik", "Pune", "Solapur",            # Onion/Tomato belt (Maharashtra)
        "Agra", "Aligarh", "Farrukhabad",        # Potato belt (UP)
        "Vidisha", "Sehore", "Raisen",           # Gram belt (MP)
        "Gulbarga", "Bidar", "Yadgir",           # Tur belt (Karnataka)
        "Akola", "Amravati", "Yavatmal",         # Pulses (Vidarbha)
        "Delhi", "Mumbai", "Chennai",            # Major consumption centers
    ]

    async def fetch_weather(self, start_date: date, end_date: date) -> list[dict]:
        records = []
        async with aiohttp.ClientSession() as session:
            for district in self.AGRI_DISTRICTS:
                district_records = await self._fetch_district(session, district, start_date, end_date)
                records.extend(district_records)
                await asyncio.sleep(0.2)

        logger.info(f"IMD: Fetched {len(records)} weather records.")
        return records

    async def _fetch_district(self, session, district, start_date, end_date):
        params = {
            "api-key": self.API_KEY,
            "format": "json",
            "filters[district]": district,
            "filters[from_date]": start_date.strftime("%Y-%m-%d"),
            "filters[to_date]": end_date.strftime("%Y-%m-%d"),
            "limit": 1000,
        }
        url = self.API_BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        response = await _retry_request(session, url)
        if not response:
            return []
        try:
            import json
            data = json.loads(response)
            records = []
            for item in data.get("records", []):
                records.append({
                    "date": datetime.strptime(item["date"], "%Y-%m-%d"),
                    "location": district,
                    "state": item.get("state", "Unknown"),
                    "rainfall_mm": self._safe_float(item.get("rainfall")),
                    "temp_max_c": self._safe_float(item.get("max_temp")),
                    "temp_min_c": self._safe_float(item.get("min_temp")),
                    "humidity_pct": self._safe_float(item.get("humidity")),
                    "source": "imd",
                })
            return records
        except Exception as e:
            logger.error(f"IMD parse error for {district}: {e}")
            return []

    @staticmethod
    def _safe_float(val) -> Optional[float]:
        try:
            return float(val) if val not in (None, "", "N/A", "-") else None
        except ValueError:
            return None


class DataValidator:
    """
    Validates incoming data using IQR-based outlier detection,
    completeness checks, and domain-knowledge validation.
    """

    PRICE_BOUNDS = {
        "onion": (1.0, 150.0),   "potato": (1.0, 80.0),    "tomato": (1.0, 200.0),
        "gram": (40.0, 120.0),   "tur": (50.0, 150.0),     "urad": (50.0, 160.0),
        "moong": (60.0, 160.0),  "masur": (40.0, 120.0),
    }
    WEATHER_BOUNDS = {
        "rainfall_mm": (-0.1, 500.0),
        "temp_max_c": (5.0, 50.0),
        "temp_min_c": (-5.0, 45.0),
        "humidity_pct": (0.0, 100.0),
    }

    def validate_prices(self, records: list[dict]) -> tuple[list[dict], list[str]]:
        valid, issues = [], []
        for r in records:
            commodity = r.get("commodity")
            price = r.get("modal_price_per_kg")
            if price is None:
                issues.append(f"Missing price for {commodity} on {r.get('date')}")
                continue
            bounds = self.PRICE_BOUNDS.get(commodity, (0.1, 500.0))
            if not (bounds[0] <= price <= bounds[1]):
                issues.append(f"Price {price} out of bounds {bounds} for {commodity} on {r.get('date')}")
                r["quality_score"] = max(0, r.get("quality_score", 100) - 30)
                r["modal_price_per_kg"] = max(bounds[0], min(bounds[1], price))  # Cap
            valid.append(r)
        return valid, issues

    def validate_weather(self, records: list[dict]) -> tuple[list[dict], list[str]]:
        valid, issues = [], []
        for r in records:
            row_ok = True
            for field, (lo, hi) in self.WEATHER_BOUNDS.items():
                val = r.get(field)
                if val is not None and not (lo <= val <= hi):
                    issues.append(f"Weather {field}={val} out of bounds for {r.get('location')} on {r.get('date')}")
                    r[field] = None
                    row_ok = False
            if row_ok:
                valid.append(r)
            else:
                r["quality_score"] = 60.0
                valid.append(r)
        return valid, issues

    def calculate_quality_score(self, record: dict, required_fields: list[str]) -> float:
        score = 100.0
        for field in required_fields:
            if record.get(field) is None:
                score -= 20.0
        return max(0.0, score)


class DataPreprocessor:
    """
    Cleans and standardizes raw data: handles missing values,
    deduplication, outlier capping, and format standardization.
    """

    def preprocess_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["commodity"] = df["commodity"].str.lower().str.strip()
        df["market"] = df["market"].str.strip()

        # Deduplicate: keep latest scraped_at per (commodity, date, market)
        df = df.sort_values("scraped_at").drop_duplicates(
            subset=["commodity", "date", "market"], keep="last"
        )

        # Forward-fill missing prices within each (commodity, market) group
        df = df.sort_values(["commodity", "market", "date"])
        df["modal_price_per_kg"] = df.groupby(["commodity", "market"])["modal_price_per_kg"].transform(
            lambda x: x.ffill().bfill()
        )

        # IQR-based outlier capping per commodity (rolling 30-day)
        df = self._cap_outliers_rolling(df, "modal_price_per_kg", window=30)

        return df

    def preprocess_weather(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"])
        # Interpolate missing weather values
        for col in ["rainfall_mm", "temp_max_c", "temp_min_c", "humidity_pct"]:
            if col in df.columns:
                df[col] = df[col].interpolate(method="linear", limit=3)
        return df

    @staticmethod
    def _cap_outliers_rolling(df, col, window=30):
        """Cap values outside rolling IQR bounds (per commodity)."""
        def cap_group(group):
            rolling = group[col].rolling(window, min_periods=5)
            q1 = rolling.quantile(0.25)
            q3 = rolling.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            group[col] = group[col].clip(lower=lower, upper=upper)
            return group
        return df.groupby("commodity", group_keys=False).apply(cap_group)
