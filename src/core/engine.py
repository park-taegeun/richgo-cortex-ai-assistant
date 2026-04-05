"""
RichgoCortexEngine — Model C+ orchestrator.
Plan Freeze: 2026-04-01 | Calibrated: 2026-04-02

This module owns only:
  - Jeonse / PIR / S_alpha / Confidence computation
  - analyze() — calls sub-analyzers and assembles the result dict

Sub-analyzers injected via __init__:
  temporal  → PIRBandAnalyzer         (src.analytics.temporal)
  spatial   → SupplySpilloverAnalyzer (src.analytics.spatial)
  sentiment → SentimentAnalyzer       (src.core.sentiment)
"""
import os
from datetime import datetime
from typing import Optional

from src.utils.snowflake_client import SnowflakeClient
from src.analytics.temporal import (
    PIRBandAnalyzer,
    REGIONAL_INCOME_MAN_WON,
    PIR_RELATIVE_LOW,
)
from src.analytics.spatial import SupplySpilloverAnalyzer
from src.core.sentiment import SentimentAnalyzer

# ── Jeonse Safety Floor ──────────────────────────────────────────────────────
JEONSE_SAFETY_FLOOR = float(os.getenv("JEONSE_SAFETY_FLOOR", "0.65"))

# Adaptive Safety Floor — 460k-row analysis (2026-04-02)
# Method: MAX(regional_P20 × 1.15, regional_avg × 0.80)
ADAPTIVE_JEONSE_FLOOR: dict = {
    "강남구":   0.35,   # avg=0.39, P20=0.26
    "용산구":   0.35,   # avg=0.39, P20=0.30
    "성동구":   0.35,   # avg=0.41, P20=0.36
    "서초구":   0.38,   # avg=0.43, P20=0.31
    "송파구":   0.41,   # avg=0.44, P20=0.36
    "마포구":   0.48,   # avg=0.51, P20=0.42
    "종로구":   0.48,   # avg=0.59, P20=0.52
    "서울_기타": 0.55,  # 서울전체 avg=0.58, P20=0.49
    "경기":     0.65,
    "default":  0.65,
}

# ── PIR thresholds ───────────────────────────────────────────────────────────
PIR_UNDERVALUE_RATIO    = float(os.getenv("PIR_UNDERVALUE_THRESHOLD", "0.85"))

# ── S_alpha execution threshold ──────────────────────────────────────────────
MIGRATION_SCORE_EXECUTE = float(os.getenv("MIGRATION_SCORE_EXECUTE", "80"))

# ── S_alpha weights (sum = 1.0) ──────────────────────────────────────────────
W_SUPPLY  = 0.30
W_PIR     = 0.25
W_JEONSE  = 0.20
W_NEWS    = 0.15
W_COMMUTE = 0.10

EDUCATION_MULTIPLIER              = 1.5
EDUCATION_LIVING_SCORE_THRESHOLD  = 90


class RichgoCortexEngine:
    """
    Richgo + Snowflake Cortex AI 부동산 상급지 이동 전략 분석 엔진.

    External interface (unchanged after refactor):
        conn   = snowflake.connector.connect(...)
        engine = RichgoCortexEngine(conn)
        result = engine.analyze("a7qzYub")
    """

    def __init__(self, conn):
        self._client   = SnowflakeClient(conn)
        self.temporal  = PIRBandAnalyzer(self._client)
        self.spatial   = SupplySpilloverAnalyzer(self._client)
        self.sentiment = SentimentAnalyzer(self._client)

    # ── Static helpers ───────────────────────────────────────────────────────

    @staticmethod
    def get_jeonse_floor(sgg: str, sd: str) -> float:
        """
        Adaptive Safety Floor 조회.
        Priority: SGG direct → 서울_기타 → SD → default
        """
        if sgg in ADAPTIVE_JEONSE_FLOOR:
            return ADAPTIVE_JEONSE_FLOOR[sgg]
        if sd == "서울":
            return ADAPTIVE_JEONSE_FLOOR["서울_기타"]
        return ADAPTIVE_JEONSE_FLOOR.get(sd, ADAPTIVE_JEONSE_FLOOR["default"])

    # ── Indicator computation ────────────────────────────────────────────────

    @staticmethod
    def compute_jeonse_ratio(
        mean_jeonse: float,
        mean_meme: float,
        is_dong_avg: bool = False,
    ) -> tuple:
        """전세가율 = mean_jeonse / mean_meme. Returns (ratio, deduction)."""
        if not mean_meme or mean_meme == 0:
            return 0.0, 0.0
        ratio     = round(mean_jeonse / mean_meme, 4)
        deduction = 0.15 if is_dong_avg else 0.0
        return ratio, deduction

    @staticmethod
    def compute_pir(mean_meme_price_man_won: float, sd: str) -> tuple:
        """
        PIR = 평균 매매가(만원) / 지역 연 소득(만원).
        Returns (pir, confidence_deduction=-0.20) — always SGG-level estimate.
        """
        annual_income = REGIONAL_INCOME_MAN_WON.get(sd, REGIONAL_INCOME_MAN_WON["default"])
        return round(mean_meme_price_man_won / annual_income, 2), 0.20

    @staticmethod
    def compute_s_alpha(
        jeonse_ratio: float,
        pir: float,
        pir_5yr_avg: float,
        supply_score: float,
        sentiment_score: float,
        living_score: Optional[float] = None,
        commute_score: float = 50.0,
        is_chobuma: Optional[bool] = None,
    ) -> float:
        """
        S_alpha 하이브리드 점수 (PIR Band 보정 전 기본값, 0~100).
        초품아(LIVING_SCORE≥90) 확인 시 ×1.5 가중치 적용.
        """
        s_jeonse = min(100.0, max(0.0, jeonse_ratio * 100.0))

        undervalue_threshold = pir_5yr_avg * PIR_UNDERVALUE_RATIO
        overvalue_ceiling    = pir_5yr_avg * 1.5
        if pir <= undervalue_threshold:
            s_pir = 100.0
        elif pir >= overvalue_ceiling:
            s_pir = 0.0
        else:
            s_pir = 100.0 * (overvalue_ceiling - pir) / (overvalue_ceiling - undervalue_threshold)

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

    @staticmethod
    def compute_confidence(deductions: list) -> tuple:
        """
        신뢰도 점수 = (1 - Σdeductions) × 100.
        Returns: (confidence_pct, label 'High'/'Medium'/'Low')
        """
        confidence = max(0.0, round((1.0 - sum(deductions)) * 100.0, 1))
        if confidence >= 85.0:
            label = "High"
        elif confidence >= 60.0:
            label = "Medium"
        else:
            label = "Low"
        return confidence, label

    # ── Master analysis ──────────────────────────────────────────────────────

    def analyze(
        self,
        danji_id: str,
        news_texts: Optional[list] = None,
        commute_score: float = 50.0,
    ) -> dict:
        """
        Model C+ 전체 분석 파이프라인.
        Returns identical schema as pre-refactor engine.analyze().
        """
        deductions = []

        # 1. Metadata
        try:
            info = self._client.fetch_danji_info(danji_id)
        except ValueError:
            return None
            
        sd, sgg = info["sd"], info["sgg"]

        # 2. Market price (13 months)
        prices = self._client.fetch_market_price(danji_id, months=13)
        if not prices:
            return None
            
        latest = prices[0]
        if latest.get("mean_meme_price") is None or latest.get("mean_jeonse_price") is None:
            return None

        # 3. Jeonse ratio
        jeonse_ratio, d_jeonse = self.compute_jeonse_ratio(
            latest["mean_jeonse_price"], latest["mean_meme_price"]
        )
        deductions.append(d_jeonse)

        # 4. PIR
        pir_val, d_pir = self.compute_pir(latest["mean_meme_price"], sd)
        deductions.append(d_pir)

        # 5. PIR Band (temporal)
        pir_5yr_avg, pir_band_fallback = self.temporal.fetch_pir_band(sgg, sd)
        if pir_5yr_avg is None:
            pir_5yr_avg = pir_val * 1.10  # conservative fallback
        pir_relative_index, pir_band_adj, pir_band_label = self.temporal.compute_adjustment(
            pir_val, pir_5yr_avg
        )

        # 6. Supply + Spillover (spatial)
        region_prices = self._client.fetch_region_price(sgg, months=13)
        supply_score_final, d_supply, spillover_detail = self.spatial.compute_with_spillover(
            sgg, region_prices
        )
        supply_score_raw = spillover_detail["own_score"]
        deductions.append(d_supply)

        # 7. Sentiment — 3단계 파이프라인
        #
        #  ┌─ Path A: 명시적 news_texts 전달 (테스트/오버라이드)
        #  ├─ Path B: STAGING.REAL_ESTATE_RSS_FEEDS 3단계 Fallback → Cortex
        #  ├─ Path C: RSS 테이블 부재 시 → 시장 지표 서술문 생성 → Cortex (★ 주경로)
        #  └─ Path D: Cortex 실패 시 → 수학적 Proxy (최후 보루)
        #
        #  sentiment_source: "cortex_news" | "cortex_market" | "proxy"
        sentiment_proxy_used = False
        sentiment_source     = "proxy"  # 기본값 — 아래에서 덮어쓰기

        # Path A / B: 명시 전달 또는 RSS 자동 수집
        if not news_texts:
            news_texts = self._client.fetch_news_texts(
                danji_name=info["danji"],
                sgg=sgg,
                sd=sd,
            )

        # Path A / B 성공
        if news_texts:
            sentiment_score, d_sentiment = self.sentiment.compute_score(news_texts)
            sentiment_source = "cortex_news"

        else:
            # Path C: 시장 지표 → 서술문 → Cortex (RSS 테이블 없을 때 주경로)
            momentum_data  = self._client.fetch_price_momentum(danji_id)
            population_net = self._client.fetch_population_net(sgg)

            narratives = self.sentiment.build_market_narratives(
                sgg=sgg,
                sd=sd,
                momentum_pct=momentum_data["momentum_pct"],
                population_net=population_net,
                jeonse_ratio=jeonse_ratio,
                supply_score=supply_score_final,
            )

            if narratives:
                sentiment_score, d_sentiment = self.sentiment.compute_score(narratives)
                sentiment_source = "cortex_market"
                print(
                    f"✅ [CORTEX MARKET] {info['danji']} — "
                    f"시장 서술문 {len(narratives)}개 Cortex 분석 완료 | "
                    f"score={sentiment_score:+.4f}pt"
                )
            else:
                # Path D: 최후 수학적 Proxy
                sentiment_score, d_sentiment = self.sentiment.compute_proxy_score(
                    momentum_pct=momentum_data["momentum_pct"],
                    population_net=population_net,
                )
                sentiment_proxy_used = True
                sentiment_source     = "proxy"

        print(
            f"📡 [PIPELINE] {info['danji']} | "
            f"source={sentiment_source} | "
            f"score={sentiment_score:+.4f}pt | "
            f"deduction={d_sentiment}"
        )
        deductions.append(d_sentiment)

        # 8. Adaptive jeonse floor
        jeonse_floor = self.get_jeonse_floor(sgg, sd)

        # 9. S_alpha base
        s_alpha_raw = self.compute_s_alpha(
            jeonse_ratio=jeonse_ratio,
            pir=pir_val,
            pir_5yr_avg=pir_5yr_avg,
            supply_score=supply_score_final,
            sentiment_score=sentiment_score,
            living_score=info.get("living_score"),
            commute_score=commute_score,
        )

        # 10. PIR Band adjustment + Score Clamping → int 0~100
        s_alpha = int(max(0, min(100, round(s_alpha_raw + pir_band_adj))))

        # 11. Confidence
        confidence_pct, confidence_label = self.compute_confidence(deductions)

        # 12. 초품아
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
            "sentiment_proxy_used":   sentiment_proxy_used,
            "sentiment_source":       sentiment_source,
            # ── 단지 속성
            "living_score":           info.get("living_score"),
            "is_chobuma":             is_chobuma,
            "latest_meme_price_man_won":   latest["mean_meme_price"],
            "latest_jeonse_price_man_won": latest["mean_jeonse_price"],
            # ── 신뢰도 세부
            "confidence_deductions":  deductions,
        }
