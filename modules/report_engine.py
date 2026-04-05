"""
modules/report_engine.py
Richgo-Cortex AI — Strategic Report Generator

Responsibilities:
  - S_alpha 기반 분기 메시지 생성 (3문장 동적 전략 리포트)
  - Alpha-Trigger 조건 평가
  - 점수 Delta 계산

Public API:
  build_ai_report(cur: dict, tgt: dict) → dict
  build_delta(cur: dict, tgt: dict)     → dict
"""
# ── Alpha-Trigger Constants ────────────────────────────────────────────────────
ALPHA_TRIGGER_DELTA = 20   # 점수 상승 폭 임계값
ALPHA_TRIGGER_MIN   = 80   # 목표 단지 최소 점수

# ── Design Tokens (색상은 styles.py에서 import 하지 않고 독립 상수로 유지) ──
_MINT       = "#00FFAA"
_YELLOW_NEO = "#FFD21E"
_RED_NEO    = "#FF4B4B"
_NEUTRAL    = "#E8EAF0"


# ── Report Builder ─────────────────────────────────────────────────────────────

def build_ai_report(cur: dict, tgt: dict) -> dict:
    """
    목표 단지 데이터를 기반으로 AI 마스터 전략 리포트를 생성합니다.

    Args:
        cur: 현재 단지 analyze() 결과 dict
        tgt: 목표 단지 analyze() 결과 dict

    Returns:
        {
            "message":    str   — HTML f-string 메시지
            "color":      str   — 강조 색상 hex
            "delta":      int   — 점수 차이 (tgt - cur)
            "is_trigger": bool  — Alpha-Trigger 발동 여부
        }
    """
    ai_score  = tgt["s_alpha"]
    ai_pir_ok = tgt["pir_undervalue_ok"]
    ai_jeonse = tgt["jeonse_ratio"]
    pir_val   = tgt["pir"]
    delta_val = tgt["s_alpha"] - cur["s_alpha"]

    spill_own     = tgt["spillover_detail"]["own_score"]
    supply_signal = "안정적" if spill_own >= 60 else "경계"

    is_price_efficiency = (
        cur["latest_meme_price_man_won"] > tgt["latest_meme_price_man_won"]
    ) and (
        cur["s_alpha"] < tgt["s_alpha"]
    )

    # ── 분기 1: 자본 효율성 — 더 저렴하면서 점수가 높음 ──
    if is_price_efficiency:
        message = (
            f"자본 효율성을 극대화한 <b style='color:{_MINT}'>자산 유동화형 상급지 이동</b> 전략입니다. "
            f"현 단지 대비 {delta_val:+d}pt의 자산 가치 점프가 예상됩니다.<br/>"
            f"목표 단지의 PIR은 <b>{pir_val:.1f}년</b><span style='font-size:0.85em;color:#8892A4;'>"
            f" (서울 평균 소득 기준)</span>으로 방어력을 갖추었으며, "
            f"인근 변수 신호({supply_signal}) 측면에서도 전략적 우위를 점합니다."
        )
        color = _MINT

    # ── 분기 2: 역사적 저평가 + PIR 안전 ──
    elif ai_score >= 80 and ai_pir_ok:
        message = (
            f"<b style='color:{_MINT}'>역사적 저평가 구간</b>입니다. "
            f"현 단지 대비 {delta_val:+d}pt의 높은 자산 가치 상승이 예상되는 골든타임입니다.<br/>"
            f"목표 단지의 PIR이 <b>{pir_val:.1f}년</b><span style='font-size:0.85em;color:#8892A4;'>"
            f" (서울 평균 소득 기준)</span>으로 서울 평균에 비추어 유리하며, "
            f"공급 신호가 {supply_signal}하여 하락 방어력이 탁월합니다."
        )
        color = _MINT

    # ── 분기 3: 점수 양호 but 전세가율 취약 ──
    elif ai_score >= 80 and ai_jeonse < 0.4:
        message = (
            f"내재 가치는 높으나 <b style='color:{_YELLOW_NEO}'>전세가율({ai_jeonse*100:.1f}%) "
            f"뒷받침이 약해 하락 방어력이 주의됩니다.</b><br/>"
            f"자산 점프 폭은 {delta_val:+d}pt로 유의미하나, "
            f"자금 유동성 확보 후 실거주 목적으로 진입 여건을 활용하십시오. "
            f"<span style='font-size:0.85em;color:#8892A4;'>"
            f"PIR {pir_val:.1f}년 (서울 평균 소득 기준)</span>"
        )
        color = _YELLOW_NEO

    # ── 분기 4: 점수 낮음 — 관망 권고 ──
    elif ai_score < 60:
        message = (
            f"<b style='color:{_RED_NEO}'>아직은 시장의 불확실성이 큽니다.</b> "
            f"이동에 따른 가치 상승({delta_val:+d}pt) 대비 수급 및 가격 리스크가 선행합니다.<br/>"
            f"잠시 관망하며 더 나은 매수 기회나 유동성 골든타임을 엿보십시오. "
            f"<span style='font-size:0.85em;color:#8892A4;'>"
            f"PIR {pir_val:.1f}년 (서울 평균 소득 기준)</span>"
        )
        color = _RED_NEO

    # ── 분기 5: 중립 — 보수적 접근 ──
    else:
        message = (
            f"단기적으로 안정적인 흐름을 보이고 있습니다(점수: {ai_score}pt).<br/>"
            f"보수적 접근이 권장되며, 전세금({ai_jeonse*100:.1f}%) 레버리지와 "
            f"PIR 장기 밴드를 예의 주시하십시오. "
            f"<span style='font-size:0.85em;color:#8892A4;'>"
            f"현재 PIR {pir_val:.1f}년 (서울 평균 소득 기준)</span>"
        )
        color = _NEUTRAL

    return {
        "message":    message,
        "color":      color,
        "delta":      delta_val,
        "is_trigger": (delta_val >= ALPHA_TRIGGER_DELTA and ai_score >= ALPHA_TRIGGER_MIN),
    }


# ── Delta Calculator ───────────────────────────────────────────────────────────

def build_delta(cur: dict, tgt: dict) -> dict:
    """
    현재 단지 vs 목표 단지 점수 차이를 계산합니다.

    Returns:
        {
            "delta":       int   — 점수 차이 (양수/음수)
            "delta_pct":   float — 백분율 기준 증감률
            "is_trigger":  bool  — Alpha-Trigger 발동 여부
            "delta_color": str   — 조건부 색상 hex
            "delta_glow":  str   — CSS text-shadow 문자열
            "trigger_text":str   — 트리거 상태 HTML 문자열
        }
    """
    delta     = tgt["s_alpha"] - cur["s_alpha"]
    delta_pct = round(delta / max(cur["s_alpha"], 1) * 100, 1)
    is_trigger = (delta >= ALPHA_TRIGGER_DELTA and tgt["s_alpha"] >= ALPHA_TRIGGER_MIN)

    if is_trigger:
        delta_color  = _MINT
        delta_glow   = f"text-shadow:0 0 20px {_MINT};"
        trigger_text = f"<b style='color:{_MINT};'>달성</b>"
    else:
        delta_color  = "#556677"
        delta_glow   = "text-shadow: 0 0 20px #1E2329;"
        trigger_text = (
            f"<b style='color:#556677;'>미달성</b> "
            f"<span style='font-size:11px;color:#A0AEC0;'>"
            f"(목표 점수 {ALPHA_TRIGGER_DELTA}점 이상 차이 필요)</span>"
        )

    return {
        "delta":        delta,
        "delta_pct":    delta_pct,
        "is_trigger":   is_trigger,
        "delta_color":  delta_color,
        "delta_glow":   delta_glow,
        "trigger_text": trigger_text,
    }
