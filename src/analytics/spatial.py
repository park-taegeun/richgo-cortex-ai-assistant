"""
Geospatial analysis — Supply Spillover.

Responsibilities:
  - SUPPLY_SPILLOVER dict      : adjacent-district interference mapping
  - score_from_R()             : piecewise supply score function
  - compute_supply_score()     : R ratio → score + confidence deduction
  - compute_with_spillover()   : own×0.7 + adjacent_avg×0.3
"""
import math
import os
from src.utils.snowflake_client import SnowflakeClient

# ── Supply Spillover mapping ─────────────────────────────────────────────────
# 근거: 행정구역 경계 공유 + 동일 생활권 이동 수요 실증
SUPPLY_SPILLOVER: dict = {
    "강남구":   ["서초구"],
    "서초구":   ["강남구"],
    "송파구":   ["강동구"],
    "강동구":   ["송파구"],
    "마포구":   ["용산구"],
    "용산구":   ["마포구"],
    "성동구":   ["광진구"],
    "광진구":   ["성동구"],
    "은평구":   ["마포구", "서대문구"],
    "동작구":   ["관악구", "서초구"],
    "강서구":   ["양천구"],
    "양천구":   ["강서구", "영등포구"],
    "영등포구": ["양천구", "동작구"],
}

SPILLOVER_OWN_WEIGHT = 0.70
SPILLOVER_ADJ_WEIGHT = 0.30

# ── Supply Score thresholds (env-overridable) ────────────────────────────────
SUPPLY_SAFE_UPPER = float(os.getenv("SUPPLY_DEMAND_RATIO_SAFE",   "0.8"))
SUPPLY_DANGER     = float(os.getenv("SUPPLY_DEMAND_RATIO_DANGER", "1.4"))


class SupplySpilloverAnalyzer:
    """
    공급 점수 + 인접구 Spillover 분석기.

    Usage:
        analyzer = SupplySpilloverAnalyzer(client)
        score, deduction, detail = analyzer.compute_with_spillover('송파구', region_prices)
    """

    def __init__(self, client: SnowflakeClient):
        self.client = client

    @staticmethod
    def score_from_R(R: float) -> float:
        """
        Supply Score 구간 함수 (Model C+ 확정 공식).
        R < 0.8          → 100점  (기회선)
        0.8 ≤ R ≤ 1.2   → 100 - 125*(R-0.8)   [선형 100→50]
        1.2 < R ≤ 1.4   → 50  - 250*(R-1.2)   [급경사 50→0]
        R > 1.4          → max(0, 50*exp(-3*(R-1.4)))  [지수 감쇠]
        """
        if R < SUPPLY_SAFE_UPPER:
            return 100.0
        elif R <= 1.2:
            return 100.0 - 125.0 * (R - SUPPLY_SAFE_UPPER)
        elif R <= SUPPLY_DANGER:
            return max(0.0, 50.0 - 250.0 * (R - 1.2))
        else:
            return max(0.0, 50.0 * math.exp(-3.0 * (R - SUPPLY_DANGER)))

    @staticmethod
    def compute_supply_score(region_prices: list = None) -> tuple:
        """
        R = 최근 총세대수 / 전년도 총세대수 → Supply Score.
        데이터 부족 시 R=1.0 가정, confidence deduction 0.10 적용.

        Returns: (score 0~100, confidence_deduction)
        """
        deduction = 0.0

        if region_prices and len(region_prices) >= 13:
            latest_hh   = region_prices[0].get("total_households") or 0
            prev_year_hh = region_prices[12].get("total_households") or 0
            if prev_year_hh and prev_year_hh > 0:
                R = latest_hh / prev_year_hh
            else:
                R = 1.0
                deduction = 0.10
        else:
            R = 1.0
            deduction = 0.10

        return round(SupplySpilloverAnalyzer.score_from_R(R), 2), deduction

    def compute_with_spillover(self, sgg: str, region_prices: list = None) -> tuple:
        """
        본 구 공급 점수에 인접 구 Spillover를 가중 합산.
        Final = own_score × 0.70 + adjacent_avg × 0.30

        Returns: (final_score, confidence_deduction, spillover_detail dict)
        """
        own_score, deduction = self.compute_supply_score(region_prices)

        adjacent_sggs = SUPPLY_SPILLOVER.get(sgg, [])
        detail = {
            "own_sgg":          sgg,
            "own_score":        own_score,
            "adjacent_sggs":    adjacent_sggs,
            "adjacent_scores":  {},
            "spillover_applied": False,
        }

        if not adjacent_sggs:
            detail["final_score"] = own_score
            return own_score, deduction, detail

        adj_scores = []
        for adj_sgg in adjacent_sggs:
            adj_prices = self.client.fetch_region_price(adj_sgg, months=13)
            adj_score, _ = self.compute_supply_score(adj_prices)
            adj_scores.append(adj_score)
            detail["adjacent_scores"][adj_sgg] = adj_score

        if adj_scores:
            adj_avg = round(sum(adj_scores) / len(adj_scores), 2)
            final   = round(own_score * SPILLOVER_OWN_WEIGHT + adj_avg * SPILLOVER_ADJ_WEIGHT, 2)
            detail["adjacent_avg"]      = adj_avg
            detail["final_score"]       = final
            detail["spillover_applied"] = True
        else:
            final = own_score
            detail["final_score"] = own_score

        return final, deduction, detail
