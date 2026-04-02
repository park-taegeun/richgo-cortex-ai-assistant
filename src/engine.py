"""
Richgo-Cortex AI Assistant — Analysis Engine
Model C+ | Plan Freeze: 2026-04-01

Data flow:
  danji_id
    → fetch_danji_info() + fetch_market_price()   [parallel]
    → compute_jeonse_ratio()
    → compute_pir()
    → compute_supply_score()
    → compute_sentiment_score()
    → compute_s_alpha()
    → compute_confidence()
    → analyze() → recommendation dict
"""

import math
import os
from datetime import datetime
from typing import Optional

# ── Constants (env override → Model C+ defaults) ────────────────────────────
# Legacy single floor (kept for env-override fallback)
JEONSE_SAFETY_FLOOR       = float(os.getenv("JEONSE_SAFETY_FLOOR",       "0.65"))

# Adaptive Safety Floor — calibrated from 460k-row analysis (2026-04-02)
# Method: MAX(regional_P20 × 1.15, regional_avg × 0.80)
# Key finding: 강남3구 P80=50.9%, 서울전체 P80=66.95% → 70% 기준 전면 무효
ADAPTIVE_JEONSE_FLOOR: dict = {
    "강남구": 0.35,  # avg=0.39, P20=0.26
    "용산구": 0.35,  # avg=0.39, P20=0.30
    "성동구": 0.35,  # avg=0.41, P20=0.36
    "서초구": 0.38,  # avg=0.43, P20=0.31
    "송파구": 0.41,  # avg=0.44, P20=0.36
    "마포구": 0.48,  # avg=0.51, P20=0.42
    "종로구": 0.48,  # avg=0.59, P20=0.52
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

# ── PIR Band (Temporal Analysis) constants ──────────────────────────────────
PIR_BAND_MONTHS         = 60    # 5년 시계열
PIR_BAND_MIN_MONTHS     = 12    # SGG 데이터 최소 기준 (미달 시 SD Fallback)
PIR_RELATIVE_LOW        = 0.85  # 이하 → '역대급 저평가' +15점
PIR_RELATIVE_HIGH       = 1.15  # 초과 → '고점 경고' -10점
PIR_BAND_UNDERVALUE_BONUS   = 15.0
PIR_BAND_OVERVALUE_PENALTY  = 10.0

# ── Supply Spillover (Geospatial) — 공급 간섭 인접구 매핑 ────────────────────
# 근거: 행정구역 경계 공유 + 동일 생활권 이동 수요 실증
SUPPLY_SPILLOVER: dict = {
    "강남구": ["서초구"],
    "서초구": ["강남구"],
    "송파구": ["강동구"],
    "강동구": ["송파구"],
    "마포구": ["용산구"],
    "용산구": ["마포구"],
    "성동구": ["광진구"],
    "광진구": ["성동구"],
    "은평구": ["마포구", "서대문구"],
    "동작구": ["관악구", "서초구"],
    "강서구": ["양천구"],
    "양천구": ["강서구", "영등포구"],
    "영등포구": ["양천구", "동작구"],
}
SPILLOVER_OWN_WEIGHT = 0.70
SPILLOVER_ADJ_WEIGHT = 0.30

# Regional household income constants (만원/year) — KOSIS 2024 avg
# Used for PIR computation (no income table in HACKATHON_2026 schema)
REGIONAL_INCOME_MAN_WON: dict = {
    "서울": 5500.0,
    "경기": 4800.0,
    "인천": 4500.0,
    "부산": 4200.0,
    "대구": 4100.0,
    "광주": 4000.0,
    "대전": 4100.0,
    "울산": 4600.0,
    "세종": 5000.0,
    "default": 4500.0,
}

# S_alpha weights (sum = 1.0)
W_SUPPLY  = 0.30
W_PIR     = 0.25
W_JEONSE  = 0.20
W_NEWS    = 0.15
W_COMMUTE = 0.10
EDUCATION_MULTIPLIER = 1.5  # 초품아 가중치
EDUCATION_LIVING_SCORE_THRESHOLD = 90  # LIVING_SCORE proxy for 초품아


class RichgoCortexEngine:
    """
    Richgo + Snowflake Cortex AI 부동산 상급지 이동 전략 분석 엔진.

    Usage:
        import snowflake.connector
        conn = snowflake.connector.connect(...)
        engine = RichgoCortexEngine(conn)
        result = engine.analyze("a7qzYub")
    """

    def __init__(self, conn):
        self.conn = conn

    @staticmethod
    def get_jeonse_floor(sgg: str, sd: str) -> float:
        """
        Adaptive Safety Floor 조회 (2026-04-02 460k행 실측 캘리브레이션).
        우선순위: SGG 직접 매핑 → 서울_기타 → SD 기본값 → default

        강남3구 P80=50.9%, 서울전체 P80=66.95% 실측으로 70% 기준 폐기.
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

    def fetch_danji_info(self, danji_id: str) -> dict:
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

    def fetch_market_price(self, danji_id: str, months: int = 12) -> list:
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

    def fetch_region_price(self, sgg: str, months: int = 12) -> list:
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

    def fetch_region_price_sd(self, sd: str, months: int = 60) -> list:
        """REGION_APT_RICHGO_MARKET_PRICE_M_H에서 SD(시도) 단위 시세 조회 (PIR Band fallback용)."""
        cur = self._cur()
        cur.execute("""
            SELECT YYYYMMDD, TOTAL_HOUSEHOLDS, MEAN_MEME_PRICE, MEAN_JEONSE_PRICE
            FROM REGION_APT_RICHGO_MARKET_PRICE_M_H
            WHERE SD = %s AND REGION_LEVEL = 'sd'
            ORDER BY YYYYMMDD DESC
            LIMIT %s
        """, (sd, months))
        rows = cur.fetchall()
        cur.close()
        cols = ["yyyymmdd", "total_households", "mean_meme_price", "mean_jeonse_price"]
        return [dict(zip(cols, r)) for r in rows]

    def fetch_population_movement(self, sgg: str, months: int = 36) -> list:
        """REGION_POPULATION_MOVEMENT에서 SGG 순이동 인구 조회 (Supply Score용)."""
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

    def fetch_pir_band(self, sgg: str, sd: str) -> tuple:
        """
        PIR 5년 밴드 평균 산출.
        SGG 단위 데이터가 PIR_BAND_MIN_MONTHS(12개월) 미만이면 SD 전체 평균으로 Fallback.
        Returns: (pir_5yr_avg, used_fallback: bool)
        """
        annual_income = REGIONAL_INCOME_MAN_WON.get(sd, REGIONAL_INCOME_MAN_WON["default"])

        # 1차 시도: SGG 단위
        rows = self.fetch_region_price(sgg, months=PIR_BAND_MONTHS)
        used_fallback = False

        if len(rows) < PIR_BAND_MIN_MONTHS:
            # Fallback → SD 단위
            rows = self.fetch_region_price_sd(sd, months=PIR_BAND_MONTHS)
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

    def compute_pir_band_adjustment(self, current_pir: float, pir_5yr_avg: float) -> tuple:
        """
        PIR 상대 지수 산출 → S_alpha 보정치 반환.
        pir_relative_index < 0.85 → '역대급 저평가' → +15점
        pir_relative_index > 1.15 → '고점 경고'     → -10점
        Returns: (pir_relative_index, s_alpha_adjustment, label)
        """
        if not pir_5yr_avg or pir_5yr_avg == 0:
            return 1.0, 0.0, "N/A"

        pir_relative_index = round(current_pir / pir_5yr_avg, 4)

        if pir_relative_index < PIR_RELATIVE_LOW:
            return pir_relative_index, PIR_BAND_UNDERVALUE_BONUS, "역대급 저평가"
        elif pir_relative_index > PIR_RELATIVE_HIGH:
            return pir_relative_index, -PIR_BAND_OVERVALUE_PENALTY, "고점 경고"
        else:
            return pir_relative_index, 0.0, "적정 구간"

    def compute_supply_score_with_spillover(
        self,
        sgg: str,
        region_prices: Optional[list] = None,
    ) -> tuple:
        """
        Supply Spillover 적용 공급 점수.
        인접 구의 공급 데이터를 가중 합산:
          Final = own_score * 0.7 + adjacent_avg * 0.3

        Returns: (final_supply_score, confidence_deduction, spillover_detail dict)
        """
        # 1. 본 구 점수
        own_score, deduction = self.compute_supply_score(region_prices)

        adjacent_sggs = SUPPLY_SPILLOVER.get(sgg, [])
        spillover_detail = {
            "own_sgg":          sgg,
            "own_score":        own_score,
            "adjacent_sggs":    adjacent_sggs,
            "adjacent_scores":  {},
            "spillover_applied": False,
        }

        if not adjacent_sggs:
            spillover_detail["final_score"] = own_score
            return own_score, deduction, spillover_detail

        # 2. 인접 구 점수 수집
        adj_scores = []
        for adj_sgg in adjacent_sggs:
            adj_prices = self.fetch_region_price(adj_sgg, months=13)
            adj_score, _ = self.compute_supply_score(adj_prices)
            adj_scores.append(adj_score)
            spillover_detail["adjacent_scores"][adj_sgg] = adj_score

        if adj_scores:
            adj_avg = round(sum(adj_scores) / len(adj_scores), 2)
            final_score = round(
                own_score * SPILLOVER_OWN_WEIGHT + adj_avg * SPILLOVER_ADJ_WEIGHT, 2
            )
            spillover_detail["adjacent_avg"]     = adj_avg
            spillover_detail["final_score"]      = final_score
            spillover_detail["spillover_applied"] = True
        else:
            final_score = own_score
            spillover_detail["final_score"] = own_score

        return final_score, deduction, spillover_detail

    def compute_jeonse_ratio(
        self,
        mean_jeonse: float,
        mean_meme: float,
        is_dong_avg: bool = False,
    ) -> tuple:
        """
        전세가율 계산.
        Returns: (jeonse_ratio, confidence_deduction)
        confidence_deduction: 동 단위 평균 사용 시 -0.15
        """
        if not mean_meme or mean_meme == 0:
            return 0.0, 0.0
        ratio = round(mean_jeonse / mean_meme, 4)
        deduction = 0.15 if is_dong_avg else 0.0
        return ratio, deduction

    def compute_pir(
        self,
        mean_meme_price_man_won: float,
        sd: str,
    ) -> tuple:
        """
        PIR (Price-to-Income Ratio) 계산.
        PIR = 평균 매매가(만원) / 지역 연 소득(만원)
        Returns: (pir, confidence_deduction)
        confidence_deduction: 구 단위 평균 소득 사용 시 -0.20
        """
        annual_income = REGIONAL_INCOME_MAN_WON.get(sd, REGIONAL_INCOME_MAN_WON["default"])
        pir = round(mean_meme_price_man_won / annual_income, 2)
        return pir, 0.20  # 항상 SGG 단위 추정치 사용 → -20%

    def compute_supply_score(
        self,
        region_prices: Optional[list] = None,
    ) -> tuple:
        """
        공급 점수 계산.
        R = 최근 총세대수 / 전년도 총세대수 (공급 증가 비율 프록시)
        Returns: (supply_score 0~100, confidence_deduction)
        """
        deduction = 0.0

        if region_prices and len(region_prices) >= 13:
            latest_hh = region_prices[0].get("total_households") or 0
            prev_year_hh = region_prices[12].get("total_households") or 0
            if prev_year_hh and prev_year_hh > 0:
                R = latest_hh / prev_year_hh
            else:
                R = 1.0
                deduction = 0.10
        else:
            R = 1.0
            deduction = 0.10

        score = self._supply_score_from_R(R)
        return round(score, 2), deduction

    def _supply_score_from_R(self, R: float) -> float:
        """
        Supply Score 구간 함수 (Model C+ 확정 공식).
        R < 0.8          → S = 100  (기회선)
        0.8 ≤ R ≤ 1.2   → S = 100 - 125*(R - 0.8)  [선형 100→50]
        1.2 < R ≤ 1.4   → S = 50  - 250*(R - 1.2)  [급경사 50→0]
        R > 1.4          → S = max(0, 50 * exp(-3*(R-1.4)))  [지수 감쇠]
        """
        if R < SUPPLY_SAFE_UPPER:
            return 100.0
        elif R <= 1.2:
            return 100.0 - 125.0 * (R - SUPPLY_SAFE_UPPER)
        elif R <= SUPPLY_DANGER:
            return max(0.0, 50.0 - 250.0 * (R - 1.2))
        else:
            return max(0.0, 50.0 * math.exp(-3.0 * (R - SUPPLY_DANGER)))

    def compute_sentiment_score(
        self,
        news_texts: list,
    ) -> tuple:
        """
        뉴스 감성 점수 계산 (Snowflake Cortex SENTIMENT).
        - 각 뉴스 헤드라인을 개별 쿼리 후 평균
        - 스케일: raw(-1~+1) × 5 → -5~+5
        Returns: (sentiment_score -5~+5, confidence_deduction)

        Note: SQL 패턴 확정 → SELECT SNOWFLAKE.CORTEX.SENTIMENT('text') AS s
        (TRY_CAST + AI_SENTIMENT 패턴은 __round__ 에러 위험으로 사용 금지)
        """
        if not news_texts:
            return 0.0, 0.15  # 표본 없음 → -15%

        scores = []
        cur = self._cur()
        for text in news_texts[:20]:
            try:
                cur.execute(
                    "SELECT SNOWFLAKE.CORTEX.SENTIMENT(%s) AS s",
                    (text,)
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    scores.append(float(row[0]))
            except Exception:
                continue
        cur.close()

        deduction = 0.0
        if len(scores) < NEWS_MIN_SAMPLE:
            deduction += 0.15

        if not scores:
            return 0.0, deduction

        positive_count = sum(1 for s in scores if s > 0)
        negative_count = sum(1 for s in scores if s < 0)
        dominant_ratio = max(positive_count, negative_count) / len(scores)
        if dominant_ratio < SENTIMENT_AGREE_THRESHOLD:
            deduction += 0.10

        raw_avg = sum(scores) / len(scores)
        scaled = round(raw_avg * 5.0, 4)
        return scaled, deduction

    def compute_s_alpha(
        self,
        jeonse_ratio: float,
        pir: float,
        pir_10yr_avg: float,
        supply_score: float,
        sentiment_score: float,
        living_score: Optional[float] = None,
        commute_score: float = 50.0,
        is_chobuma: Optional[bool] = None,
    ) -> float:
        """
        S_alpha 하이브리드 점수 계산 (0~100).
        """
        s_jeonse = min(100.0, max(0.0, jeonse_ratio * 100.0))

        undervalue_threshold = pir_10yr_avg * PIR_UNDERVALUE_RATIO
        overvalue_ceiling    = pir_10yr_avg * 1.5
        if pir <= undervalue_threshold:
            s_pir = 100.0
        elif pir >= overvalue_ceiling:
            s_pir = 0.0
        else:
            s_pir = 100.0 * (overvalue_ceiling - pir) / (overvalue_ceiling - undervalue_threshold)

        s_news = min(100.0, max(0.0, (sentiment_score + 5.0) * 10.0))

        if is_chobuma is None:
            is_chobuma = (living_score or 0) >= EDUCATION_LIVING_SCORE_THRESHOLD

        base_score = (
            W_SUPPLY  * supply_score +
            W_PIR     * s_pir +
            W_JEONSE  * s_jeonse +
            W_NEWS    * s_news +
            W_COMMUTE * commute_score
        )

        if is_chobuma:
            base_score = min(100.0, base_score * EDUCATION_MULTIPLIER)

        return round(base_score, 2)

    def compute_confidence(self, deductions: list) -> tuple:
        """
        신뢰도 점수 계산.
        Returns: (confidence_pct 0~100, label 'High'/'Medium'/'Low')
        """
        total_deduction = sum(deductions)
        confidence = max(0.0, round((1.0 - total_deduction) * 100.0, 1))
        if confidence >= 85.0:
            label = "High"
        elif confidence >= 60.0:
            label = "Medium"
        else:
            label = "Low"
        return confidence, label

    # ── 3. Master Analysis Method ────────────────────────────────────────────

    def analyze(
        self,
        danji_id: str,
        news_texts: Optional[list] = None,
        commute_score: float = 50.0,
    ) -> dict:
        """
        단지 ID를 받아 Model C+ 전체 분석 수행 (Mission 3-3: Temporal + Spatial).
        """
        deductions = []

        # ── 1. 메타데이터 조회
        info = self.fetch_danji_info(danji_id)
        sd  = info["sd"]
        sgg = info["sgg"]

        # ── 2. 시세 조회 (최근 13개월)
        prices = self.fetch_market_price(danji_id, months=13)
        if not prices:
            raise ValueError(f"No market price data for DANJI_ID '{danji_id}'")
        latest = prices[0]

        # ── 3. 전세가율
        jeonse_ratio, d_jeonse = self.compute_jeonse_ratio(
            latest["mean_jeonse_price"],
            latest["mean_meme_price"],
            is_dong_avg=False,
        )
        deductions.append(d_jeonse)

        # ── 4. PIR 기본값
        pir_val, d_pir = self.compute_pir(latest["mean_meme_price"], sd)
        deductions.append(d_pir)

        # ── 5. PIR Band (Temporal) — 5년 평균 + 상대 지수
        pir_5yr_avg, pir_band_fallback = self.fetch_pir_band(sgg, sd)
        if pir_5yr_avg is None:
            pir_5yr_avg = pir_val * 1.10

        pir_relative_index, pir_band_adj, pir_band_label = self.compute_pir_band_adjustment(
            pir_val, pir_5yr_avg
        )

        # ── 6. Supply Score with Spillover (Geospatial)
        region_prices = self.fetch_region_price(sgg, months=13)
        supply_score_final, d_supply, spillover_detail = self.compute_supply_score_with_spillover(
            sgg, region_prices
        )
        supply_score_raw = spillover_detail["own_score"]
        deductions.append(d_supply)

        # ── 7. 뉴스 감성
        sentiment_score, d_sentiment = self.compute_sentiment_score(news_texts or [])
        deductions.append(d_sentiment)

        # ── 8. Adaptive Safety Floor
        jeonse_floor = self.get_jeonse_floor(sgg, sd)

        # ── 9. S_alpha 기본 계산
        s_alpha_raw = self.compute_s_alpha(
            jeonse_ratio=jeonse_ratio,
            pir=pir_val,
            pir_10yr_avg=pir_5yr_avg,
            supply_score=supply_score_final,
            sentiment_score=sentiment_score,
            living_score=info.get("living_score"),
            commute_score=commute_score,
        )

        # ── 10. PIR Band 보정 + Score Clamping (0~100 정수)
        s_alpha_adjusted = s_alpha_raw + pir_band_adj
        s_alpha = int(max(0, min(100, round(s_alpha_adjusted))))

        # ── 11. 신뢰도
        confidence_pct, confidence_label = self.compute_confidence(deductions)

        # ── 12. 초품아 판단
        is_chobuma = (info.get("living_score") or 0) >= EDUCATION_LIVING_SCORE_THRESHOLD

        return {
            "danji_id":               danji_id,
            "danji_name":             info["danji"],
            "sd":                     sd,
            "sgg":                    sgg,
            "emd":                    info["emd"],
            "analysis_date":          datetime.now().strftime("%Y-%m-%d"),
            # ── 종합 점수
            "s_alpha":                s_alpha,
            "s_alpha_before_band":    round(s_alpha_raw, 2),
            "pir_band_adjustment":    pir_band_adj,
            "confidence_pct":         confidence_pct,
            "confidence_label":       confidence_label,
            "execution_trigger":      s_alpha >= MIGRATION_SCORE_EXECUTE,
            # ── 전세가율
            "jeonse_ratio":           jeonse_ratio,
            "jeonse_floor":           jeonse_floor,
            "jeonse_safety_ok":       jeonse_ratio >= jeonse_floor,
            # ── PIR Band (Temporal)
            "pir":                    pir_val,
            "pir_5yr_avg":            pir_5yr_avg,
            "pir_band_fallback":      pir_band_fallback,
            "pir_relative_index":     pir_relative_index,
            "pir_band_label":         pir_band_label,
            "pir_undervalue_ok":      pir_val <= pir_5yr_avg * PIR_UNDERVALUE_RATIO,
            # ── Supply Spillover (Spatial)
            "supply_score_raw":       supply_score_raw,
            "supply_score_final":     supply_score_final,
            "spillover_detail":       spillover_detail,
            # ── 감성
            "sentiment_score":        sentiment_score,
            # ── 단지 속성
            "living_score":           info.get("living_score"),
            "is_chobuma":             is_chobuma,
            "latest_meme_price_man_won":   latest["mean_meme_price"],
            "latest_jeonse_price_man_won": latest["mean_jeonse_price"],
            # ── 신뢰도 세부
            "confidence_deductions":  deductions,
        }
