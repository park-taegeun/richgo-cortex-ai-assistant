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

        산식: Score = (Price_Change * 0.7) + (Pop_Flow_Ratio * 0.3)

        Price_Change 기여 (가중 0.7):
          momentum_pct × 0.5 → [-5, +5] 연속 스케일
          (±10% 가격 변화 = ±5.0 최대 점수)

        Pop_Flow_Ratio 기여 (가중 0.3):
          population_net을 POP_SCALE(3,000명)으로 정규화 → [-1.0, +1.0]
          × 1.5 → 최대 ±1.5pt 기여
          ※ 절대 인구수(>10,000)가 반환될 경우 POP_SCALE을 자동 상향 조정

        Returns: (proxy_score: float [-5~+5], deduction: float)
        Deduction: -0.10 (프록시 사용 감점)
        """
        # ── 데이터 없음 → 0.0 명시 출력 (기본값 +0.5 완전 제거) ──────────────
        if momentum_pct == 0.0 and population_net == 0.0:
            print("⚠️  [PROXY] 모멘텀·인구 데이터 모두 누락 → 심리 점수 0.0 (데이터 누락)")
            return 0.0, 0.10

        # ── Price_Change 기여 ────────────────────────────────────────────────
        # momentum_pct × 0.5 → ±5.0 연속 스케일 (±10% 매매가 변화 = ±5.0)
        price_component = max(-5.0, min(5.0, momentum_pct * 0.5))

        # ── Pop_Flow_Ratio 기여 ──────────────────────────────────────────────
        # 스케일 자동 감지: |population_net| > 10,000 이면 절대 인구수로 판단
        if abs(population_net) > 10_000:
            POP_SCALE = 500_000.0  # 서울 자치구 총인구 기준 (~50만명)
        elif abs(population_net) > 500:
            POP_SCALE = 5_000.0   # 월 순이동 ±5,000명 기준
        else:
            POP_SCALE = 200.0     # 월 순이동 ±200명 기준 (소규모)

        pop_ratio     = max(-1.0, min(1.0, population_net / POP_SCALE))
        pop_component = pop_ratio * 1.5  # [-1.5, +1.5] 기여

        # ── 최종 산식 적용 ───────────────────────────────────────────────────
        proxy_score = round(
            max(-5.0, min(5.0, price_component * 0.7 + pop_component * 0.3)),
            4,
        )

        print(
            f"📊 [PROXY FORMULA] "
            f"momentum={momentum_pct:+.2f}% → price={price_component:+.2f}pt (×0.7={price_component*0.7:+.2f}) | "
            f"pop_net={population_net:+.0f} (scale={POP_SCALE:.0f}) "
            f"→ pop_ratio={pop_ratio:+.3f} → pop={pop_component:+.2f}pt (×0.3={pop_component*0.3:+.2f}) | "
            f"final={proxy_score:+.4f}pt"
        )
        return proxy_score, 0.10  # 프록시 사용 감점 -10%
