"""
Temporal analysis — PIR Band (5-year moving average).

Responsibilities:
  - fetch_pir_band()         : SGG 60-month PIR avg, fallback to SD
  - compute_adjustment()     : relative index → S_alpha ±adjustment
"""
import os
from src.utils.snowflake_client import SnowflakeClient

# ── PIR Band constants ──────────────────────────────────────────────────────
PIR_BAND_MONTHS        = 60
PIR_BAND_MIN_MONTHS    = 12
PIR_RELATIVE_LOW       = 0.85
PIR_RELATIVE_HIGH      = 1.15
PIR_BAND_UNDERVALUE_BONUS   = 15.0
PIR_BAND_OVERVALUE_PENALTY  = 10.0

# ── Regional income constants (KOSIS 2024 avg, 만원/year) ──────────────────────
REGIONAL_INCOME_MAN_WON: dict = {
    "서울": 5500.0, "경기": 4800.0, "인천": 4500.0,
    "부산": 4200.0, "대구": 4100.0, "광주": 4000.0,
    "대전": 4100.0, "울산": 4600.0, "세종": 5000.0,
    "default": 4500.0,
}


class PIRBandAnalyzer:
    def __init__(self, client: SnowflakeClient):
        self.client = client

    def fetch_pir_band(self, sgg: str, sd: str) -> tuple:
        annual_income = REGIONAL_INCOME_MAN_WON.get(sd, REGIONAL_INCOME_MAN_WON["default"])
        rows = self.client.fetch_region_price(sgg, months=PIR_BAND_MONTHS)
        used_fallback = False
        if len(rows) < PIR_BAND_MIN_MONTHS:
            rows = self.client.fetch_region_price_sd(sd, months=PIR_BAND_MONTHS)
            used_fallback = True
        if not rows:
            return None, used_fallback
        pir_values = [
            r["mean_meme_price"] / annual_income
            for r in rows
            if r.get("mean_meme_price") and r["mean_meme_price"] > 0
        ]
        if not pir_values:
            return None, used_fallback
        return round(sum(pir_values) / len(pir_values), 2), used_fallback

    @staticmethod
    def compute_adjustment(current_pir: float, pir_5yr_avg: float) -> tuple:
        if not pir_5yr_avg or pir_5yr_avg == 0:
            return 1.0, 0.0, "N/A"
        idx = round(current_pir / pir_5yr_avg, 4)
        if idx < PIR_RELATIVE_LOW:
            return idx, PIR_BAND_UNDERVALUE_BONUS, "역대급 저평가"
        elif idx > PIR_RELATIVE_HIGH:
            return idx, -PIR_BAND_OVERVALUE_PENALTY, "고점 경고"
        else:
            return idx, 0.0, "적정 구간"
