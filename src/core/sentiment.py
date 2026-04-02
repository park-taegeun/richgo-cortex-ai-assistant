"""
Snowflake Cortex AI — news sentiment analysis.

Confirmed SQL: SELECT SNOWFLAKE.CORTEX.SENTIMENT('text') AS s
Banned:        TRY_CAST(AI_SENTIMENT(...) AS DOUBLE) → __round__ error
Scale:         raw FLOAT (-1~+1) × 5.0 in Python → -5~+5
"""
import os
from src.utils.snowflake_client import SnowflakeClient

NEWS_MIN_SAMPLE           = int(os.getenv("NEWS_MIN_SAMPLE",              "3"))
SENTIMENT_AGREE_THRESHOLD = float(os.getenv("SENTIMENT_AGREEMENT_THRESHOLD", "0.7"))


class SentimentAnalyzer:
    def __init__(self, client: SnowflakeClient):
        self.client = client

    def compute_score(self, news_texts: list) -> tuple:
        if not news_texts:
            return 0.0, 0.15
        scores = []
        cur = self.client._cur()
        for text in news_texts[:20]:
            try:
                cur.execute("SELECT SNOWFLAKE.CORTEX.SENTIMENT(%s) AS s", (text,))
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
        if max(positive, negative) / len(scores) < SENTIMENT_AGREE_THRESHOLD:
            deduction += 0.10
        return round(sum(scores) / len(scores) * 5.0, 4), deduction
