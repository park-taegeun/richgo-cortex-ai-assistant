"""
Richgo-Cortex AI Assistant — Analysis Engine
Model C+ | Plan Freeze: 2026-04-01
Calibrated: 2026-04-02 (Adaptive Jeonse Floor — 460k row analysis)

Data flow:
  danji_id
    → fetch_danji_info() + fetch_market_price()
    → compute_jeonse_ratio()
    → compute_pir()
    → compute_supply_score()
    → compute_sentiment_score()
    → get_jeonse_floor()   ← Adaptive per-district floor
    → compute_s_alpha()
    → compute_confidence()
    → analyze() → recommendation dict
"""

import math
import os
from datetime import datetime
from typing import Optional

# ── Constants (env override → Model C+ defaults) ────────────────────────────
# Legacy single floor (kept for env-override fallback only)
JEONSE_SAFETY_FLOOR = float(os.getenv("JEONSE_SAFETY_FLOOR", "0.65"))

# Adaptive Safety Floor — calibrated from 460k-row analysis (2026-04-02)
# Method: MAX(regional_P20 x 1.15, regional_avg x 0.80)
# Finding: 강남3구 P80=50.9%, 서울전체 P80=66.95% → 70% 기준 전면 무효
ADAPTIVE_JEONSE_FLOOR = {
    "강남구": 0.35,   # avg=0.39, P20=0.26, P80=0.46
    "용산구": 0.35,   # avg=0.39, P20=0.30, P80=0.49
    "성동구": 0.35,   # avg=0.41, P20=0.36, P80=0.47
    "서초구": 0.38,   # avg=0.43, P20=0.31, P80=0.53
    "송파구": 0.41,   # avg=0.44, P20=0.36, P80=0.52
    "마포구": 0.48,   # avg=0.51, P20=0.42, P80=0.60
    "종로구": 0.48,   # avg=0.59, P20=0.52, P80=0.62
    "서울_기타": 0.55,  # 서울전체 avg=0.58, P20=0.49
    "경기": 0.65,
    "default": 0.65,
}

PIR_UNDERVALUE_RATIO      = float(os.getenv("PIR_UNDERVALUE_THRESHOLD",  "0.85"))
SUPPLY_SAFE_UPPER         = float(os.getenv("SUPPLY_DEMAND_RATIO_SAFE",  "0.8"))
SUPPLY_DANGER             = float(os.getenv("SUPPLY_DEMAND_RATIO_DANGER","1.4"))
MIGRATION_SCORE_EXECUTE   = float(os.getenv("MIGRATION_SCORE_EXECUTE",   "80"))
NEWS_TTL_HOURS            = int(os.getenv("NEWS_TTL_HOURS",              "168"))
NEWS_MIN_SAMPLE           = int(os.getenv("NEWS_MIN_SAMPLE",             "3"))
SENTIMENT_AGREE_THRESHOLD = float(os.getenv("SENTIMENT_AGREEMENT_THRESHOLD", "0.7"))

# Regional income constants (man-won/year) — KOSIS 2024 avg
# Used for PIR (no income table in HACKATHON_2026 schema)
REGIONAL_INCOME_MAN_WON = {
    "서울": 5500.0, "경기": 4800.0, "인천": 4500.0,
    "부산": 4200.0, "대구": 4100.0, "광주": 4000.0,
    "대전": 4100.0, "울산": 4600.0, "세종": 5000.0,
    "default": 4500.0,
}

# S_alpha weights (sum = 1.0)
W_SUPPLY  = 0.30
W_PIR     = 0.25
W_JEONSE  = 0.20
W_NEWS    = 0.15
W_COMMUTE = 0.10
EDUCATION_MULTIPLIER             = 1.5
EDUCATION_LIVING_SCORE_THRESHOLD = 90


class RichgoCortexEngine:
    """
    Richgo + Snowflake Cortex AI 부동산 상급지 이동 전략 분석 엔진.

    Usage:
        import snowflake.connector
        conn = snowflake.connector.connect(...)
        engine = RichgoCortexEngine(conn)
        result = engine.analyze('a7qzYub')
    """

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def get_jeonse_floor(sgg, sd):
        """
        Adaptive Safety Floor 조회 (2026-04-02 460k행 실측 캘리브레이션).
        우선순위: SGG 직접 매핑 → 서울_기타 → SD 기본값 → default
        """
        if sgg in ADAPTIVE_JEONSE_FLOOR:
            return ADAPTIVE_JEONSE_FLOOR[sgg]
        if sd == "서울":
            return ADAPTIVE_JEONSE_FLOOR["서울_기타"]
        return ADAPTIVE_JEONSE_FLOOR.get(sd, ADAPTIVE_JEONSE_FLOOR["default"])

    # ── Private helpers ──────────────────────────────────────────────────────

    def _cur(self):
        return self.conn.cursor()

    # ── 1. Data Fetch ────────────────────────────────────────────────────────

    def fetch_danji_info(self, danji_id):
        """DANJI_APT_INFO에서 단지 메타데이터 조회."""
        cur = self._cur()
        cur.execute("""
            SELECT BJD_CODE, SD, SGG, EMD, DANJI_ID, DANJI,
                   BUILDING_TYPE, AGES_YEAR, TOTAL_HOUSEHOLDS,
                   LIVING_SCORE, CONSTRUCTOR_RANK
            FROM DANJI_APT_INFO
            WHERE DANJI_ID = %s
            LIMIT 1
        """, (danji_id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise ValueError(f"DANJI_ID '{danji_id}' not found in DANJI_APT_INFO")
        cols = ["bjd_code","sd","sgg","emd","danji_id","danji",
                "building_type","ages_year","total_households",
                "living_score","constructor_rank"]
        return dict(zip(cols, row))

    def fetch_market_price(self, danji_id, months=13):
        """DANJI_APT_RICHGO_MARKET_PRICE_M_H에서 최근 N개월 시세 조회."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE,
                   MEME_PRICE_PER_SUPPLY_PYEONG, JEONSE_PRICE_PER_SUPPLY_PYEONG,
                   MEME_CAP_PRICE
            FROM DANJI_APT_RICHGO_MARKET_PRICE_M_H
            WHERE DANJI_ID = %s
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (danji_id, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd","mean_meme_price","mean_jeonse_price",
                "meme_price_per_supply_pyeong","jeonse_price_per_supply_pyeong",
                "meme_cap_price"]
        return [dict(zip(cols, r)) for r in rows]

    def fetch_region_price(self, sgg, months=13):
        """REGION_APT_RICHGO_MARKET_PRICE_M_H에서 SGG 단위 시세 조회."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, TOTAL_HOUSEHOLDS, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE
            FROM REGION_APT_RICHGO_MARKET_PRICE_M_H
            WHERE SGG = %s AND REGION_LEVEL = 'sgg'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sgg, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd","total_households","mean_meme_price","mean_jeonse_price"]
        return [dict(zip(cols, r)) for r in rows]

    def fetch_population_movement(self, sgg, months=36):
        """REGION_POPULATION_MOVEMENT에서 SGG 순이동 인구 조회."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, POPULATION
            FROM REGION_POPULATION_MOVEMENT
            WHERE SGG = %s AND MOVEMENT_TYPE = '순이동' AND REGION_LEVEL = 'sgg'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sgg, months))
        rows = cur.fetchall()
        cur.close()
        return [{"yyyymmdd": r[0], "population": r[1]} for r in rows]

    # ── 2. Indicator Computation ─────────────────────────────────────────────

    def compute_jeonse_ratio(self, mean_jeonse, mean_meme, is_dong_avg=False):
        """ 전세가율. Returns (ratio, confidence_deduction)."""
        if not mean_meme or mean_meme == 0:
            return 0.0, 0.0
        ratio = round(mean_jeonse / mean_meme, 4)
        return ratio, (0.15 if is_dong_avg else 0.0)

    def compute_pir(self, mean_meme_price_man_won, sd):
        """
        PIR = 평균 매매가(만원) / 지역 연소득(만원).
        항상 SGG 추정소득 → -20% confidence deduction.
        """
        annual_income = REGIONAL_INCOME_MAN_WON.get(sd, REGIONAL_INCOME_MAN_WON["default"])
        pir = round(mean_meme_price_man_won / annual_income, 2)
        return pir, 0.20

    def compute_supply_score(self, sgg, region_prices=None):
        """
        공급점수 (Model C+ 구간함수).
        R = 최근 총세대수 / 전년도 총세대수
        Returns (supply_score 0~100, confidence_deduction).
        """
        deduction = 0.0
        if region_prices and len(region_prices) >= 13:
            latest_hh  = region_prices[0].get("total_households") or 0
            prev_yr_hh = region_prices[12].get("total_households") or 0
            R = (latest_hh / prev_yr_hh) if prev_yr_hh > 0 else 1.0
            if not prev_yr_hh:
                deduction = 0.10
        else:
            R = 1.0
            deduction = 0.10
        return round(self._supply_score_from_R(R), 2), deduction

    def _supply_score_from_R(self, R):
        """
        Supply Score 구간함수 (Model C+ 확정).
        R < 0.8          → 100
        0.8 <= R <= 1.2  → 100 - 125*(R-0.8)  [선형 100→50]
        1.2 < R <= 1.4   → 50  - 250*(R-1.2)  [급경사 50→0]
        R > 1.4          → max(0, 50*exp(-3*(R-1.4)))  [지수감쇠]
        """
        if R < SUPPLY_SAFE_UPPER:
            return 100.0
        elif R <= 1.2:
            return 100.0 - 125.0 * (R - SUPPLY_SAFE_UPPER)
        elif R <= SUPPLY_DANGER:
            return max(0.0, 50.0 - 250.0 * (R - 1.2))
        else:
            return max(0.0, 50.0 * math.exp(-3.0 * (R - SUPPLY_DANGER)))

    def compute_sentiment_score(self, news_texts):
        """
        뉴스 감성점수 (Snowflake Cortex SENTIMENT).
        확정패턴: SELECT SNOWFLAKE.CORTEX.SENTIMENT(%s) AS s
        (TRY_CAST + AI_SENTIMENT 패턴은 __round__ 에러 위험으로 사용 금지)
        Returns (scaled_score -5~+5, confidence_deduction).
        """
        if not news_texts:
            return 0.0, 0.15

        scores = []
        cur = self._cur()
        for text in news_texts[:20]:
            try:
                cur.execute("SELECT SNOWFLAKE.CORTEX.SENTIMENT(%s) AS s", (text,))
                row = cur.fetchone()
                if row and row[0] is not None:
                    scores.append(float(row[0]))
            except Exception:
                continue
        cur.close()

        deduction = 0.15 if len(scores) < NEWS_MIN_SAMPLE else 0.0
        if not scores:
            return 0.0, deduction

        positive = sum(1 for s in scores if s > 0)
        negative = sum(1 for s in scores if s < 0)
        if (max(positive, negative) / len(scores)) < SENTIMENT_AGREE_THRESHOLD:
            deduction += 0.10

        return round((sum(scores) / len(scores)) * 5.0, 4), deduction

    def compute_s_alpha(
        self, jeonse_ratio, pir, pir_10yr_avg, supply_score, sentiment_score,
        living_score=None, commute_score=50.0, is_chobuma=None,
    ):
        """
        S_alpha 하이브리드 점수 (0~100).
        초품아(LIVING_SCORE>=90) 시 x1.5 가중치 적용.
        """
        s_jeonse = min(100.0, max(0.0, jeonse_ratio * 100.0))

        undervalue = pir_10yr_avg * PIR_UNDERVALUE_RATIO
        overvalue  = pir_10yr_avg * 1.5
        if pir <= undervalue:
            s_pir = 100.0
        elif pir >= overvalue:
            s_pir = 0.0
        else:
            s_pir = 100.0 * (overvalue - pir) / (overvalue - undervalue)

        s_news = min(100.0, max(0.0, (sentiment_score + 5.0) * 10.0))

        if is_chobuma is None:
            is_chobuma = (living_score or 0) >= EDUCATION_LIVING_SCORE_THRESHOLD

        base = (
            W_SUPPLY  * supply_score +
            W_PIR     * s_pir +
            W_JEONSE  * s_jeonse +
            W_NEWS    * s_news +
            W_COMMUTE * commute_score
        )
        if is_chobuma:
            base = min(100.0, base * EDUCATION_MULTIPLIER)
        return round(base, 2)

    def compute_confidence(self, deductions):
        """
        신뢰도점수. Returns (confidence_pct, label).
        High>=85% / Medium 60~84% / Low<60%
        """
        confidence = max(0.0, round((1.0 - sum(deductions)) * 100.0, 1))
        label = "High" if confidence >= 85.0 else ("Medium" if confidence >= 60.0 else "Low")
        return confidence, label

    # ── 3. Master Analysis ────────────────────────────────────────────────────

    def analyze(self, danji_id, news_texts=None, commute_score=50.0, pir_10yr_avg=None):
        """단지 ID → Model C+ 전체 분석 → recommendation dict."""
        deductions = []

        info    = self.fetch_danji_info(danji_id)
        sd, sgg = info["sd"], info["sgg"]

        prices  = self.fetch_market_price(danji_id, months=13)
        if not prices:
            raise ValueError(f"No market price data for DANJI_ID '{danji_id}'")
        latest  = prices[0]

        jeonse_ratio, d_j = self.compute_jeonse_ratio(
            latest["mean_jeonse_price"], latest["mean_meme_price"])
        deductions.append(d_j)

        pir_val, d_p = self.compute_pir(latest["mean_meme_price"], sd)
        deductions.append(d_p)
        if pir_10yr_avg is None:
            pir_10yr_avg = pir_val * 1.1

        region_prices             = self.fetch_region_price(sgg, months=13)
        supply_score, d_s         = self.compute_supply_score(sgg, region_prices)
        deductions.append(d_s)

        sentiment_score, d_n      = self.compute_sentiment_score(news_texts or [])
        deductions.append(d_n)

        # Adaptive Safety Floor — 지역별 실측 캘리브레이션
        jeonse_floor = self.get_jeonse_floor(sgg, sd)

        s_alpha = self.compute_s_alpha(
            jeonse_ratio=jeonse_ratio, pir=pir_val, pir_10yr_avg=pir_10yr_avg,
            supply_score=supply_score, sentiment_score=sentiment_score,
            living_score=info.get("living_score"), commute_score=commute_score,
        )
        confidence_pct, confidence_label = self.compute_confidence(deductions)
        is_chobuma = (info.get("living_score") or 0) >= EDUCATION_LIVING_SCORE_THRESHOLD

        return {
            "danji_id":                   danji_id,
            "danji_name":                 info["danji"],
            "sd":                         sd,
            "sgg":                        sgg,
            "emd":                        info["emd"],
            "analysis_date":              datetime.now().strftime("%Y-%m-%d"),
            "s_alpha":                    s_alpha,
            "confidence_pct":             confidence_pct,
            "confidence_label":           confidence_label,
            "execution_trigger":          s_alpha >= MIGRATION_SCORE_EXECUTE,
            "jeonse_ratio":               jeonse_ratio,
            "jeonse_floor":               jeonse_floor,
            "jeonse_safety_ok":           jeonse_ratio >= jeonse_floor,
            "pir":                        pir_val,
            "pir_10yr_avg":               round(pir_10yr_avg, 2),
            "pir_undervalue_ok":          pir_val <= pir_10yr_avg * PIR_UNDERVALUE_RATIO,
            "supply_score":               supply_score,
            "sentiment_score":            sentiment_score,
            "living_score":               info.get("living_score"),
            "is_chobuma":                 is_chobuma,
            "latest_meme_price_man_won":  latest["mean_meme_price"],
            "latest_jeonse_price_man_won":latest["mean_jeonse_price"],
            "confidence_deductions":      deductions,
        }
