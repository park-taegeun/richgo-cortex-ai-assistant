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
