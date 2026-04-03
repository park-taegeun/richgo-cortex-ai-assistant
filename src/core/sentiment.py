"""
Snowflake Cortex AI — news sentiment analysis.

Confirmed SQL pattern: SELECT SNOWFLAKE.CORTEX.SENTIMENT('text') AS s
Banned pattern:        TRY_CAST(AI_SENTIMENT(...) AS DOUBLE) → __round__ error
Scale:                 raw FLOAT (-1~+1) × 5.0 in Python → -5~+5
"""
import os
from src.utils.snowflake_client import SnowflakeClient

NEWS_MIN_SAMPLE           = int(os.getenv("NEWS_MIN_SAMPLE",              "3"))
SENTIMENT_AGREE_THRESHOLD = float(os.getenv("SENTIMENT_AGREEMENT_THRESHOLD", "0.7"))


class SentimentAnalyzer:
    """
    Snowflake Cortex SENTIMENT 기반 뉴스 감성 분석기.

    Usage:
        analyzer = SentimentAnalyzer(client)
        score, deduction = analyzer.compute_score(news_texts)
    """

    def __init__(self, client: SnowflakeClient):
        self.client = client

    def compute_score(self, news_texts: list) -> tuple:
        """
        뉴스 헤드라인 리스트 → 감성 점수 (-5~+5) + 신뢰도 감점.

        Deductions:
          - 표본 < 3건:              -0.15
          - 일관성 비율 < 0.7:      -0.10

        Returns: (scaled_score, confidence_deduction)
        """
        if not news_texts:
            return 0.0, 0.15  # 표본 없음 → -15%

        scores = []
        cur = self.client._cur()
        for text in news_texts[:20]:  # 최대 20건 (비용 관리)
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

        positive = sum(1 for s in scores if s > 0)
        negative = sum(1 for s in scores if s < 0)
        dominant_ratio = max(positive, negative) / len(scores)
        if dominant_ratio < SENTIMENT_AGREE_THRESHOLD:
            deduction += 0.10

        raw_avg = sum(scores) / len(scores)
        return round(raw_avg * 5.0, 4), deduction  # -5 ~ +5

    @staticmethod
    def compute_proxy_score(momentum_pct: float, population_net: float = 0.0) -> tuple:
        """
        뉴스 RSS 데이터 부재 시 가격 모멘텀 + 인구 유입으로 대체 심리 점수 산출.

        Proxy 산출 기준 (가격 모멘텀):
          momentum > +5%  → +3.0  (시장 급등 심리)
          momentum > +2%  → +1.5  (상승 심리)
          -2% ~ +2%       →  0.0  (중립)
          momentum < -2%  → -1.5  (하락 심리)
          momentum < -5%  → -3.0  (시장 급락 심리)

        인구 유입 보정 (±0.5):
          net_inflow > 50  → +0.5
          net_outflow < -50 → -0.5

        Returns: (proxy_score: float [-5~+5], deduction: float)
        Deduction: -0.10 (프록시 사용 감점 — 직접 뉴스 분석 대비 신뢰도 낮음)
        """
        if momentum_pct > 5.0:
            base = 3.0
        elif momentum_pct > 2.0:
            base = 1.5
        elif momentum_pct < -5.0:
            base = -3.0
        elif momentum_pct < -2.0:
            base = -1.5
        else:
            base = 0.0

        pop_adj = 0.5 if population_net > 50 else (-0.5 if population_net < -50 else 0.0)
        proxy_score = round(max(-5.0, min(5.0, base + pop_adj)), 4)

        print(f"📊 [PROXY] momentum={momentum_pct:+.2f}% | pop_net={population_net:.0f} → proxy_score={proxy_score:+.4f}")
        return proxy_score, 0.10  # 프록시 사용 감점 -10%
