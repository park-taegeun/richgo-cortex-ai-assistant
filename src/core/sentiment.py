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
        scaled  = round(raw_avg * 5.0, 4)  # -5 ~ +5

        print(
            f"📡 [CORTEX ACTUAL] 분석된 텍스트 수: {len(news_texts)} | "
            f"Cortex 성공: {len(scores)} | "
            f"raw_avg: {raw_avg:+.4f} | "
            f"평균 감성 점수: {scaled:+.4f}pt | "
            f"신뢰도 감점: -{deduction:.2f}"
        )
        return scaled, deduction  # -5 ~ +5

    @staticmethod
    def build_market_narratives(
        sgg: str,
        sd: str,
        momentum_pct: float,
        population_net: float,
        jeonse_ratio: float,
        supply_score: float,
    ) -> list:
        """
        DB 실측 데이터(가격/인구/전세/공급)를 Cortex SENTIMENT 입력용
        한국어 시장 서술문으로 변환.

        RSS 뉴스 테이블 부재 시 Cortex를 시장 데이터에 직접 적용하는 경로.
        생성된 텍스트는 실제 DB 수치를 기반으로 하므로 프록시와 구분됨.

        Returns: list[str] — 4~5개 한국어 서술문
        """
        texts = []

        # ── 1. 가격 모멘텀 ────────────────────────────────────────────────────
        if momentum_pct > 3.0:
            texts.append(
                f"{sgg} 아파트 매매가가 최근 3개월간 {momentum_pct:.1f}% 급등했습니다. "
                f"강한 매수세로 시장 열기가 매우 뜨겁습니다."
            )
        elif momentum_pct > 1.0:
            texts.append(
                f"{sgg} 아파트 매매가가 최근 3개월간 {momentum_pct:.1f}% 상승했습니다. "
                f"매수 심리가 회복되며 긍정적인 흐름이 이어지고 있습니다."
            )
        elif momentum_pct >= -1.0:
            texts.append(
                f"{sgg} 아파트 매매가는 최근 3개월간 보합세({momentum_pct:+.1f}%)를 "
                f"유지하고 있습니다. 시장이 관망세에 접어들었습니다."
            )
        elif momentum_pct >= -3.0:
            texts.append(
                f"{sgg} 아파트 매매가가 최근 3개월간 {momentum_pct:.1f}% 하락했습니다. "
                f"매도 우위 국면으로 관망세가 우세합니다."
            )
        else:
            texts.append(
                f"{sgg} 아파트 매매가가 최근 3개월간 {momentum_pct:.1f}% 급락했습니다. "
                f"매도 물량이 급증하고 시장 공포감이 높아지고 있습니다."
            )

        # ── 2. 인구 순이동 ────────────────────────────────────────────────────
        if population_net > 200:
            texts.append(
                f"{sgg}의 최근 인구 순유입이 {population_net:.0f}명으로 활발합니다. "
                f"주거 수요가 견조하게 증가하고 있습니다."
            )
        elif population_net > 50:
            texts.append(
                f"{sgg}의 인구가 {population_net:.0f}명 소폭 순유입되었습니다. "
                f"수요가 안정적으로 유지되고 있습니다."
            )
        elif population_net >= -50:
            texts.append(
                f"{sgg}의 인구 이동은 보합 수준({population_net:+.0f}명)입니다. "
                f"주거 수요에 큰 변화가 없습니다."
            )
        elif population_net >= -200:
            texts.append(
                f"{sgg}의 인구가 {abs(population_net):.0f}명 소폭 유출되었습니다. "
                f"수요가 다소 위축되는 추세입니다."
            )
        else:
            texts.append(
                f"{sgg}의 인구가 {abs(population_net):.0f}명 순유출되었습니다. "
                f"지역 선호도 하락으로 주거 수요가 감소하고 있습니다."
            )

        # ── 3. 전세가율 (하방 방어력) ─────────────────────────────────────────
        if jeonse_ratio >= 0.65:
            texts.append(
                f"{sgg} 아파트 전세가율이 {jeonse_ratio*100:.0f}%로 높아 "
                f"하락장에서도 매매가 지지력이 탁월합니다. 안전 자산으로 평가됩니다."
            )
        elif jeonse_ratio >= 0.50:
            texts.append(
                f"{sgg} 아파트 전세가율은 {jeonse_ratio*100:.0f}%로 "
                f"안정적인 수준을 유지하고 있습니다."
            )
        else:
            texts.append(
                f"{sgg} 아파트 전세가율이 {jeonse_ratio*100:.0f}%로 낮아 "
                f"하락 시 자산 손실 리스크가 우려됩니다."
            )

        # ── 4. 공급 안전도 ────────────────────────────────────────────────────
        if supply_score >= 70:
            texts.append(
                f"{sgg} 인근 신규 아파트 공급이 부족하여 기존 아파트 희소성이 높습니다. "
                f"중장기 가격 상승 기대감이 형성되고 있습니다."
            )
        elif supply_score >= 40:
            texts.append(
                f"{sgg} 인근 신규 아파트 공급 물량은 적정 수준으로 "
                f"가격에 미치는 영향이 제한적입니다."
            )
        else:
            texts.append(
                f"{sgg} 인근에 대규모 신규 아파트 입주가 예정되어 있어 "
                f"가격 하락 압력이 우려됩니다."
            )

        print(
            f"📝 [CORTEX MARKET] {sgg}({sd}) 시장 서술문 {len(texts)}개 생성 | "
            f"momentum={momentum_pct:+.1f}% | pop={population_net:+.0f}명 | "
            f"jeonse={jeonse_ratio*100:.0f}% | supply={supply_score:.0f}pt"
        )
        return texts

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
        # 데이터 기반 교정 (DB 실측 감사 2026-04-05):
        #   REGION_POPULATION_MOVEMENT 순이동 컬럼 통계
        #   MIN=-4,331 / MAX=+10,153 / AVG=-9.6 / STD=616.6
        #
        #   POP_SCALE = 1,000 (STD 기준 1.62σ)
        #     ±1,000명 → pop_ratio ±1.0 (최대 반응)
        #     ±600명   → pop_ratio ±0.6 (1σ, 중간 반응)
        #     ±200명   → pop_ratio ±0.2 (소폭 반응)
        #   STD의 극단값 ±4,331은 클리핑 처리
        POP_SCALE     = 1_000.0
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
            f"pop_net={population_net:+.0f}/1000 "
            f"→ pop_ratio={pop_ratio:+.3f} → pop={pop_component:+.2f}pt (×0.3={pop_component*0.3:+.2f}) | "
            f"final={proxy_score:+.4f}pt"
        )
        return proxy_score, 0.10  # 프록시 사용 감점 -10%
