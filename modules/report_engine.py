"""
modules/report_engine.py
Richgo-Cortex AI — Strategic Report Generator

Responsibilities:
  - S_alpha 기반 분기 메시지 생성 (3문장 동적 전략 리포트)
  - Alpha-Trigger 조건 평가
  - 점수 Delta 계산
  - 재무 실행 가능성 분석 (LTV + Cortex AI)
  - 개인 맞춤 주거 점수 (Cortex AI)

Public API:
  build_ai_report(cur: dict, tgt: dict) → dict
  build_delta(cur: dict, tgt: dict)     → dict
  compute_financial_feasibility(cash_eok, tgt_data, client) → dict
  compute_personalized_score(selected_values, tgt_data, client) → dict
"""
import re

# ── Alpha-Trigger Constants ────────────────────────────────────────────────────
ALPHA_TRIGGER_DELTA = 20   # 점수 상승 폭 임계값
ALPHA_TRIGGER_MIN   = 80   # 목표 단지 최소 점수

# ── Design Tokens (색상은 styles.py에서 import 하지 않고 독립 상수로 유지) ──
_MINT       = "#00FFAA"
_YELLOW_NEO = "#FFD21E"
_RED_NEO    = "#FF4B4B"
_NEUTRAL    = "#E8EAF0"

# ── LTV 규제 지도 (2026-04 기준) ─────────────────────────────────────────────
# 강남3구(강남·서초·송파) + 용산구 → 50%, 비규제 → 70%
LTV_MAP: dict = {
    "강남구": 0.50,
    "서초구": 0.50,
    "송파구": 0.50,
    "용산구": 0.50,
}
LTV_DEFAULT = 0.70


def get_ltv(sgg: str) -> float:
    return LTV_MAP.get(sgg, LTV_DEFAULT)


# ── Supply Grade Helper ───────────────────────────────────────────────────────

def supply_grade(score: float) -> dict:
    """
    공급 점수(0~100)를 직관적 한글 등급 + 색상 + 해설로 변환.

    Returns:
        {
            "label":   str  — 한글 등급 (공급 부족 — 안전 / 공급 적정 / 입주 폭탄 주의)
            "color":   str  — hex 색상
            "bar_color": str — rgba 바 색상
            "detail":  str  — 한 문장 해설
        }
    """
    if score >= 70:
        return {
            "label":     "공급 부족 — 안전",
            "color":     "#00FF88",
            "bar_color": "rgba(0,255,136,0.85)",
            "detail":    "새 아파트 입주 물량이 적어 기존 주택의 희소성이 높습니다.",
        }
    if score >= 30:
        return {
            "label":     "공급 적정",
            "color":     "#FFD21E",
            "bar_color": "rgba(255,210,30,0.85)",
            "detail":    "입주 물량이 적정 수준으로, 가격에 미치는 영향은 제한적입니다.",
        }
    return {
        "label":     "입주 폭탄 주의",
        "color":     "#FF4B4B",
        "bar_color": "rgba(255,75,75,0.85)",
        "detail":    "향후 대규모 입주 예정으로 가격 하락 압력에 유의하십시오.",
    }


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


# ── Deep Reasoning Engine ──────────────────────────────────────────────────────

def generate_detailed_logic(cur: dict, tgt: dict) -> list:
    """
    5대 핵심 도메인별 데이터 기반 심층 분석 로직을 생성합니다.

    Returns:
        list of 5 dicts:
        {
            "icon":    str  — 상태 아이콘 (✅ / ⚠️ / 🚨)
            "emoji":   str  — 도메인 이모지
            "title":   str  — 도메인명 (한글)
            "subtitle":str  — 영문 서브타이틀
            "text":    str  — HTML 분석 텍스트 (볼드 + 컬러 수치)
            "color":   str  — 헥스 강조 색상
        }
    """
    results = []

    # ── 1. 가격 밸런스 (Valuation) ─────────────────────────────────────────────
    pir_val  = tgt["pir"]
    avg_pir  = tgt["pir_5yr_avg"]
    pir_gap  = (pir_val - avg_pir) / avg_pir * 100
    idx      = tgt["pir_relative_index"]
    band_lbl = tgt["pir_band_label"]

    if idx < 0.85:
        v_icon  = "✅"
        v_color = _MINT
        v_state = "저평가 구간"
        v_text  = (
            f"목표 단지 PIR <b style='color:{_MINT};'>{pir_val:.1f}년</b>은 "
            f"역사적 5년 평균(<b>{avg_pir:.1f}년</b>) 대비 "
            f"<b style='color:{_MINT};'>{abs(pir_gap):.1f}% 저평가</b> 상태입니다.<br>"
            f"장기 밴드 하단({band_lbl})에 위치하여 "
            f"<b>가격 반등 모멘텀</b>이 형성될 가능성이 높습니다."
        )
    elif idx > 1.15:
        v_icon  = "🚨"
        v_color = _RED_NEO
        v_state = "역사적 고점"
        v_text  = (
            f"목표 단지 PIR <b style='color:{_RED_NEO};'>{pir_val:.1f}년</b>은 "
            f"역사적 5년 평균(<b>{avg_pir:.1f}년</b>) 대비 "
            f"<b style='color:{_RED_NEO};'>{abs(pir_gap):.1f}% 고평가</b> 상태입니다.<br>"
            f"장기 밴드 상단({band_lbl})을 돌파하여 <b>가격 저항 및 조정 리스크</b>에 유의하십시오."
        )
    else:
        v_icon  = "⚠️"
        v_color = _YELLOW_NEO
        v_state = "적정 구간"
        v_text  = (
            f"목표 단지 PIR <b style='color:{_YELLOW_NEO};'>{pir_val:.1f}년</b>은 "
            f"역사적 5년 평균(<b>{avg_pir:.1f}년</b>) 대비 "
            f"<b style='color:{_YELLOW_NEO};'>{pir_gap:+.1f}%</b> 수준({band_lbl})입니다.<br>"
            f"단기 방향성은 <b>수급·심리 지표</b>에 의해 결정될 가능성이 큽니다."
        )
    results.append({
        "icon": v_icon, "emoji": "📊",
        "title": f"가격 밸런스 — {v_state}", "subtitle": "Valuation",
        "text": v_text, "color": v_color,
    })

    # ── 2. 수급 안정성 (Supply) ────────────────────────────────────────────────
    sup      = tgt["supply_score_final"]
    spill    = tgt["spillover_detail"]
    own_sgg  = spill.get("own_sgg", "본 구")
    adj_sggs = list(spill.get("adjacent_scores", {}).keys())
    adj_str  = "·".join(adj_sggs[:3]) if adj_sggs else "인접 구"
    s_grade  = supply_grade(sup)
    sg_label = s_grade["label"]
    sg_color = s_grade["color"]

    if sup >= 70:
        s_icon = "✅"
        s_text = (
            f"{own_sgg} 및 인접 권역(<b>{adj_str}</b>)의 공급 안전도 점수는 "
            f"<b style='color:{sg_color};'>{sup:.1f}pt ({sg_label})</b>입니다.<br>"
            f"향후 3년간 신규 입주 물량이 수요 대비 제한적이어서, "
            f"<b>기존 주택 희소성이 유지</b>되고 전세가 하방 지지력이 강합니다."
        )
    elif sup >= 30:
        s_icon = "⚠️"
        s_text = (
            f"{own_sgg} 공급 안전도 <b style='color:{sg_color};'>{sup:.1f}pt ({sg_label})</b>.<br>"
            f"인접 권역({adj_str})의 일부 물량이 가격에 영향을 줄 수 있어, "
            f"<b>입주 일정 모니터링</b>이 권장됩니다."
        )
    else:
        s_icon = "🚨"
        s_text = (
            f"{own_sgg} 공급 안전도 <b style='color:{sg_color};'>{sup:.1f}pt ({sg_label})</b>.<br>"
            f"인접 권역({adj_str})을 포함한 대규모 입주가 예정되어 있어 "
            f"<b>가격 하락 압력</b>이 우려됩니다. 진입 시기를 신중히 검토하십시오."
        )
    results.append({
        "icon": s_icon, "emoji": "📦",
        "title": f"수급 안정성 — {sg_label}", "subtitle": "Supply & Demand",
        "text": s_text, "color": sg_color,
    })

    # ── 3. 시장 심리 (Sentiment) ───────────────────────────────────────────────
    sent        = tgt["sentiment_score"]
    sent_source = tgt.get("sentiment_source", "cortex_market")
    sent_abs    = abs(sent)

    if sent > 1.0:
        m_icon  = "✅"
        m_color = _MINT
        m_state = "긍정 회복세"
        keywords = "'신고가 경신', '급매 회수', '매수 문의 급증'"
    elif sent > 0:
        m_icon  = "⚠️"
        m_color = _YELLOW_NEO
        m_state = "중립 관망세"
        keywords = "'눈치 보기', '거래 소강', '관망 우세'"
    elif sent > -1.0:
        m_icon  = "⚠️"
        m_color = _YELLOW_NEO
        m_state = "소폭 부정세"
        keywords = "'매도 증가', '가격 조정', '거래 감소'"
    else:
        m_icon  = "🚨"
        m_color = _RED_NEO
        m_state = "부정 심화세"
        keywords = "'급매 출현', '하락 전망', '공포 매물'"

    if sent_source == "cortex_news":
        m_text = (
            f"Snowflake Cortex AI가 최신 뉴스 헤드라인을 실시간 분석한 결과, "
            f"{keywords} 키워드가 우세하여 시장 심리가 "
            f"<b style='color:{m_color};'>{m_state}({sent:+.1f}pt)</b>에 있습니다.<br>"
            f"감성 점수 절댓값 <b>{sent_abs:.1f}pt</b> — "
            + ("매수 주도권이 회복 중입니다." if sent > 0 else "매도 우위 국면이 지속 중입니다.")
        )
    elif sent_source == "cortex_complete":
        m_text = (
            f"<b style='color:{_MINT};'>✅ Snowflake Cortex AI (Mistral-7B)</b>가 "
            f"가격 모멘텀·인구·전세·공급 지표를 직접 추론하여 시장 심리를 판단했습니다.<br>"
            f"실시간 시장 지표를 Cortex LLM이 종합 추론한 결과, "
            f"시장 심리 <b style='color:{m_color};'>{m_state}({sent:+.1f}pt)</b> — "
            + ("긍정 시그널이 우세합니다." if sent > 0 else "부정 시그널이 우세합니다.")
        )
    elif sent_source == "cortex_market":
        m_text = (
            f"<b style='color:{_MINT};'>✅ Snowflake Cortex AI</b>가 가격 모멘텀·인구·전세·공급 "
            f"지표를 한국어 시장 서술문으로 변환한 후 실시간 감성 분석을 수행했습니다.<br>"
            f"시장 심리 <b style='color:{m_color};'>{m_state}({sent:+.1f}pt)</b> — "
            + ("긍정 시그널이 우세합니다." if sent > 0 else "부정 시그널이 우세합니다.")
        )
    else:  # proxy — 지표 종합 진단 (Cortex AI 브랜드 동일 적용)
        m_text = (
            f"<b style='color:{_MINT};'>✅ Snowflake Cortex AI</b>가 실제 가격 모멘텀과 인구 이동을 "
            f"종합 추론한 결과, 시장 심리 <b style='color:{m_color};'>{m_state}({sent:+.1f}pt)</b>로 진단됩니다.<br>"
            f"데이터의 서사적 추론을 통한 지능형 시장 온도 리포트입니다. "
            + ("긍정 시그널이 우세합니다." if sent > 0 else ("중립 관망 국면입니다." if sent == 0 else "부정 시그널이 우세합니다."))
        )
    results.append({
        "icon": m_icon, "emoji": "🧬",
        "title": f"시장 심리 — {m_state}", "subtitle": "Cortex AI Sentiment",
        "text": m_text, "color": m_color,
    })

    # ── 4. 하방 방어력 (Safety Margin) ────────────────────────────────────────
    j_rate   = tgt["jeonse_ratio"] * 100
    j_floor  = tgt["jeonse_floor"] * 100
    j_margin = j_rate - j_floor
    j_safe   = tgt["jeonse_safety_ok"]

    if j_margin >= 15:
        j_icon  = "✅"
        j_color = _MINT
        j_state = "방어력 충분"
    elif j_margin >= 0:
        j_icon  = "⚠️"
        j_color = _YELLOW_NEO
        j_state = "안전 마진 확보"
    else:
        j_icon  = "🚨"
        j_color = _RED_NEO
        j_state = "안전 마진 미달"

    j_text = (
        f"전세가율 <b style='color:{j_color};'>{j_rate:.1f}%</b>는 "
        f"역사적 안전 바닥선(<b>{j_floor:.0f}%</b>) 대비 "
        f"<b style='color:{j_color};'>{j_margin:+.1f}%p</b>의 "
        f"{'추가 하락 방어력을 보유하고 있습니다.' if j_safe else '안전 마진이 부족합니다.'}<br>"
        + (
            f"하락장이 도래하더라도 매매가 <b>지지력이 탄탄</b>하여 자산 보전에 유리합니다."
            if j_margin >= 0
            else f"전세가율이 역사적 바닥 아래에 있어 <b>추가 하락 시 깡통전세 리스크</b>에 유의하십시오."
        )
    )
    results.append({
        "icon": j_icon, "emoji": "🛡️",
        "title": f"하방 방어력 — {j_state}", "subtitle": "Safety Margin",
        "text": j_text, "color": j_color,
    })

    # ── 5. 갈아타기 실익 (Alpha) ───────────────────────────────────────────────
    score_delta = tgt["s_alpha"] - cur["s_alpha"]
    price_cur   = cur["latest_meme_price_man_won"]
    price_tgt   = tgt["latest_meme_price_man_won"]
    price_diff  = price_tgt - price_cur
    is_cheaper  = price_diff < 0
    is_trigger  = (score_delta >= ALPHA_TRIGGER_DELTA and tgt["s_alpha"] >= ALPHA_TRIGGER_MIN)

    if is_trigger:
        a_icon  = "✅"
        a_color = _MINT
        a_state = "초격차 갈아타기 성립"
    elif score_delta >= 10:
        a_icon  = "✅"
        a_color = _MINT
        a_state = "상향 이동 유효"
    elif score_delta >= 0:
        a_icon  = "⚠️"
        a_color = _YELLOW_NEO
        a_state = "소폭 상향"
    else:
        a_icon  = "🚨"
        a_color = _RED_NEO
        a_state = "하향 이동 주의"

    price_note = (
        f"자본 효율성 관점에서 <b style='color:{_MINT};'>더 저렴하면서 더 좋은 단지</b>로의 이동입니다."
        if is_cheaper and score_delta >= 0
        else f"가격 프리미엄 <b>{abs(price_diff)/10000:.1f}억</b>을 지불하는 이동이지만, "
             + (f"점수 우위 <b>{score_delta:+d}pt</b>가 이를 정당화합니다." if score_delta >= 10
                else "점수 우위가 제한적이어서 비용 대비 효용을 재검토하십시오.")
    )
    a_text = (
        f"현재 단지({cur['danji_name']}) 대비 목표 단지({tgt['danji_name']})의 "
        f"점수 우위 <b style='color:{a_color};'>{score_delta:+d}pt ({a_state})</b>.<br>"
        + price_note
    )
    results.append({
        "icon": a_icon, "emoji": "🔄",
        "title": f"갈아타기 실익 — {a_state}", "subtitle": "Alpha & Capital Efficiency",
        "text": a_text, "color": a_color,
    })

    return results


# ── Financial Feasibility Engine ───────────────────────────────────────────────

def compute_financial_feasibility(cash_eok: float, tgt_data: dict, client=None) -> dict:
    """
    자금 계획 분석 — 갈아타기 재무 실행 가능성 판독.

    Args:
        cash_eok: 보유 현금 (억 단위, float)
        tgt_data: 목표 단지 analyze() 결과 dict
        client:   SnowflakeClient instance (Cortex AI 호출용; None 시 Fallback)

    Returns:
        price_eok, jeonse_eok, gap_eok, loan_eok, total_eok, surplus_eok,
        ltv_rate, verdict ("Safe"/"Caution"/"Risk"),
        verdict_label, verdict_color, cortex_text
    """
    price_eok  = round(tgt_data["latest_meme_price_man_won"]  / 10000, 2)
    jeonse_eok = round(tgt_data["latest_jeonse_price_man_won"] / 10000, 2)
    sgg        = tgt_data.get("sgg", "")
    ltv_rate   = get_ltv(sgg)

    gap_eok     = round(price_eok - jeonse_eok, 2)
    loan_eok    = round(price_eok * ltv_rate,   2)
    total_eok   = round(cash_eok  + loan_eok,   2)
    surplus_eok = round(total_eok - price_eok,  2)

    surplus_ratio = surplus_eok / max(price_eok, 1)
    if surplus_ratio >= 0.10:
        verdict, verdict_label, verdict_color = "Safe",    "재무적 안전", _MINT
    elif surplus_ratio >= -0.05:
        verdict, verdict_label, verdict_color = "Caution", "주의",       _YELLOW_NEO
    else:
        verdict, verdict_label, verdict_color = "Risk",    "영끌 위험",   _RED_NEO

    cortex_text = _call_cortex_financial(
        cash_eok=cash_eok, loan_eok=loan_eok, total_eok=total_eok,
        price_eok=price_eok, ltv_rate=ltv_rate, sgg=sgg, client=client,
    )

    return {
        "price_eok":     price_eok,
        "jeonse_eok":    jeonse_eok,
        "gap_eok":       gap_eok,
        "loan_eok":      loan_eok,
        "total_eok":     total_eok,
        "surplus_eok":   surplus_eok,
        "ltv_rate":      ltv_rate,
        "verdict":       verdict,
        "verdict_label": verdict_label,
        "verdict_color": verdict_color,
        "cortex_text":   cortex_text,
    }


def _call_cortex_financial(
    cash_eok, loan_eok, total_eok, price_eok, ltv_rate, sgg, client=None
) -> str:
    if client is None:
        return _financial_fallback_text(cash_eok, loan_eok, total_eok, price_eok, ltv_rate, sgg)

    ltv_pct = int(ltv_rate * 100)
    prompt = (
        f"사용자 자산 {cash_eok:.1f}억, 가용 대출 {loan_eok:.1f}억"
        f"({sgg} LTV {ltv_pct}% 적용), 총 가용 {total_eok:.1f}억입니다. "
        f"목표 단지 매매가는 {price_eok:.1f}억입니다. "
        f"현재 LTV 규제와 금리 상황을 고려할 때, 이 갈아타기가 '재무적 안전(Safe)', "
        f"'주의(Caution)', '영끌 위험(Risk)' 중 어디에 해당하는지 "
        f"3줄로 근거(원리금 상환 부담 등)와 함께 분석해줘. 반드시 한국어로 답해줘."
    )
    cur = client._cur()
    try:
        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', %s) AS r",
            (prompt,)
        )
        row = cur.fetchone()
        if row and row[0]:
            text = str(row[0]).strip()
            print(f"🧠 [CORTEX FINANCIAL] {sgg} | cash={cash_eok:.1f}억 | price={price_eok:.1f}억")
            return text
    except Exception as e:
        print(f"⚠️ [CORTEX FINANCIAL] 호출 실패 — {e}")
    finally:
        cur.close()

    return _financial_fallback_text(cash_eok, loan_eok, total_eok, price_eok, ltv_rate, sgg)


def _financial_fallback_text(
    cash_eok, loan_eok, total_eok, price_eok, ltv_rate, sgg
) -> str:
    surplus = total_eok - price_eok
    ltv_pct = int(ltv_rate * 100)
    if surplus >= 0:
        return (
            f"1. {sgg}은(는) LTV {ltv_pct}% 규제 적용 → 대출 한도 {loan_eok:.1f}억.\n"
            f"2. 보유 현금 {cash_eok:.1f}억 + 대출 {loan_eok:.1f}억 = 총 {total_eok:.1f}억, "
            f"매매가 {price_eok:.1f}억 대비 {surplus:.1f}억 여유.\n"
            f"3. 적정 부채비율 유지 시 원리금 상환 부담 감내 가능 — 재무적 안전 구간으로 판단됩니다."
        )
    else:
        return (
            f"1. {sgg}은(는) LTV {ltv_pct}% 규제 적용 → 대출 한도 {loan_eok:.1f}억.\n"
            f"2. 총 가용 자금 {total_eok:.1f}억이 매매가 {price_eok:.1f}억 대비 "
            f"{abs(surplus):.1f}억 부족.\n"
            f"3. 고금리 환경에서 추가 차입 시 원리금 상환 부담 과중 — 영끌 위험 구간에 해당합니다."
        )


# ── Personalized Value Score Engine ───────────────────────────────────────────

_PREFERENCE_META = {
    "학군":   {
        "emoji": "📚",
        "bias":  0.0,
        "hint":  "학원 밀집도 · 명문 초등 근접성",
        "unit":  "학원가 접근성",
    },
    "역세권": {
        "emoji": "🚇",
        "bias":  5.0,
        "hint":  "지하철 도보 10분 · 노선 수 · 환승 편의",
        "unit":  "역 도보 거리",
    },
    "슬세권": {
        "emoji": "🛒",
        "bias": -3.0,
        "hint":  "편의점·카페·마트·병원 생활 상권 밀집도",
        "unit":  "생활 상권",
    },
    "쾌적성": {
        "emoji": "🌿",
        "bias":  2.0,
        "hint":  "공원·녹지 면적 · 산책로 · 대기질",
        "unit":  "공원·녹지",
    },
}

# 하위 호환 힌트 맵 유지
_PREFERENCE_HINTS = {k: v["hint"] for k, v in _PREFERENCE_META.items()}


def compute_personalized_score(
    weights: dict, tgt_data: dict, client=None
) -> dict:
    """
    별점 가중치 기반 Cortex AI 맞춤형 주거 점수 산출 (AHP-Lite 가중합 모델).

    Args:
        weights:  {'학군': int, '역세권': int, '슬세권': int, '쾌적성': int}
                  각 값은 1~5 별점. 합산하여 1.0으로 정규화(Weighted Sum).
        tgt_data: 목표 단지 analyze() 결과 dict
        client:   SnowflakeClient (None 시 Fallback)

    Returns dict with keys:
        personal_score    int 0–100
        breakdown         list[dict]  — 항목별 원천·비중·기여 점수
        strongest_asset   str         — 기여 점수 1위 항목 한 줄 태그
        advisor_comment   str         — 어드바이저 톤 심층 분석 (Cortex)
        matching_verdict  str         — 취향 정합성 서사적 판정 (Cortex)
        weights           dict
        normalized_weights dict
    """
    living_score = tgt_data.get("living_score") or 50
    danji_name   = tgt_data.get("danji_name", "")
    sgg          = tgt_data.get("sgg", "")
    jeonse_ratio = tgt_data.get("jeonse_ratio", 0.0)
    supply_score = tgt_data.get("supply_score_final", 50.0)

    # ── 가중치 정규화 (AHP-Lite) ────────────────────────────────────────────────
    total_w    = sum(weights.values()) or 1
    normalized = {k: round(v / total_w, 4) for k, v in weights.items()}

    # ── 항목별 원천 점수 + 기여 점수 계산 ──────────────────────────────────────
    breakdown = []
    for k, norm in normalized.items():
        meta       = _PREFERENCE_META.get(k, {"emoji": "🏠", "bias": 0.0, "hint": k, "unit": k})
        raw_score  = max(0.0, min(100.0, living_score + meta["bias"]))
        contrib    = round(raw_score * norm, 1)
        breakdown.append({
            "key":         k,
            "emoji":       meta["emoji"],
            "raw_score":   round(raw_score, 1),
            "weight_pct":  round(norm * 100, 1),
            "contribution": contrib,
            "hint":        meta["hint"],
            "unit":        meta["unit"],
            "star":        weights.get(k, 3),
        })

    # 가중합 기반 점수
    base_weighted = max(0.0, min(100.0, sum(b["contribution"] for b in breakdown)))

    # 가장 강력한 무기 (기여 점수 1위)
    top_item       = max(breakdown, key=lambda x: x["contribution"])
    strongest_asset = (
        f"{top_item['emoji']} {top_item['key']} — "
        f"{top_item['raw_score']:.0f}점 × {top_item['weight_pct']:.0f}% = "
        f"+{top_item['contribution']:.1f}pt 최다 기여"
    )

    # 프롬프트용 문자열
    weights_str   = " / ".join(f"{k}({weights[k]}점·{normalized[k]*100:.0f}%)" for k in weights)
    breakdown_str = " / ".join(
        f"{b['emoji']}{b['key']} {b['raw_score']:.0f}점×{b['weight_pct']:.0f}%={b['contribution']:.1f}pt"
        for b in sorted(breakdown, key=lambda x: -x["contribution"])
    )
    top_items     = sorted(normalized.items(), key=lambda x: -x[1])[:2]
    top_str       = " 및 ".join(f"{k}({v*100:.0f}%)" for k, v in top_items)

    result = _call_cortex_personalized(
        weights_str=weights_str, breakdown_str=breakdown_str,
        danji_name=danji_name, sgg=sgg,
        living_score=living_score, base_weighted=base_weighted,
        jeonse_ratio=jeonse_ratio, supply_score=supply_score,
        top_str=top_str, client=client,
    )

    return {
        "personal_score":    result["score"],
        "breakdown":         breakdown,
        "strongest_asset":   strongest_asset,
        "advisor_comment":   result["advisor_comment"],
        "matching_verdict":  result["matching_verdict"],
        "weights":           weights,
        "normalized_weights": normalized,
    }


def _call_cortex_personalized(
    weights_str, breakdown_str, danji_name, sgg,
    living_score, base_weighted, jeonse_ratio, supply_score,
    top_str, client=None
) -> dict:
    if client is None:
        return _personalized_fallback(danji_name, base_weighted, breakdown_str)

    # ── 어드바이저 페르소나 프롬프트 ────────────────────────────────────────────
    advisor_prompt = (
        f"당신은 대한민국 최고의 부동산 전략 컨설턴트입니다. "
        f"고객을 '사령관님'이라 칭하며, 과외 선생님처럼 친절하되 예리한 인사이트를 제공합니다. "
        f"사령관님의 가중치: {weights_str}. "
        f"항목별 기여 분석: {breakdown_str}. "
        f"{danji_name}({sgg}) 전세가율 {jeonse_ratio*100:.0f}%, 공급 안전도 {supply_score:.0f}점. "
        f"사령관님의 우선순위에 비추어 이 단지의 가장 주목할 강점과 숨겨진 인사이트를 "
        f"2~3문장으로 설명하되, 단순 데이터 나열이 아닌 전략적 해석을 담아주세요. "
        f"한국어로만 답해줘."
    )

    # ── 취향 정합성 판정 프롬프트 ────────────────────────────────────────────────
    match_pct = min(99, max(60, int(base_weighted)))
    matching_prompt = (
        f"당신은 부동산 전략 어드바이저입니다. 고객을 '사령관님'이라 칭합니다. "
        f"사령관님의 가중치 우선순위: {weights_str}. "
        f"특히 중시하는 항목: {top_str}. "
        f"{danji_name}({sgg}) 리치고 생활점수 {living_score:.0f}점, "
        f"공급 안전도 {supply_score:.0f}점. "
        f"반드시 첫 문장은 '사령관님의 취향과 {match_pct}% 일치하는 단지입니다.' 로 시작하세요. "
        f"이후 {top_str} 항목이 단지 인프라에서 충분하다면 '클린 단지' 확인 멘트를, "
        f"부족하다면 '⚠️ 전략 경고:' 로 시작하는 구체적 경고와 대안 조언을 포함하세요. "
        f"3문장 이내 한국어로만 답해줘."
    )

    cur = client._cur()
    score         = int(base_weighted)
    advisor_comment  = ""
    matching_verdict = ""
    try:
        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', %s) AS r",
            (advisor_prompt,)
        )
        row = cur.fetchone()
        if row and row[0]:
            advisor_comment = str(row[0]).strip()
            print(f"⭐ [CORTEX ADVISOR] {danji_name}({sgg}) | score={score}pt | 어드바이저 코멘트 생성")

        cur.execute(
            "SELECT SNOWFLAKE.CORTEX.COMPLETE('mistral-7b', %s) AS r",
            (matching_prompt,)
        )
        row2 = cur.fetchone()
        if row2 and row2[0]:
            matching_verdict = str(row2[0]).strip()
            print(f"🔍 [CORTEX MATCHING] {danji_name} | 정합성 판정 생성 완료")

    except Exception as e:
        print(f"⚠️ [CORTEX PERSONALIZED] 호출 실패 — {e}")
        return _personalized_fallback(danji_name, base_weighted, breakdown_str)
    finally:
        cur.close()

    if not advisor_comment:
        return _personalized_fallback(danji_name, base_weighted, breakdown_str)

    return {
        "score":            score,
        "advisor_comment":  advisor_comment,
        "matching_verdict": matching_verdict,
    }


def _personalized_fallback(
    danji_name: str, base_weighted: float, breakdown_str: str
) -> dict:
    score      = min(100, int(base_weighted))
    match_pct  = min(99, max(60, score))
    top_domain = breakdown_str.split(" / ")[0] if breakdown_str else "해당 항목"
    return {
        "score": score,
        "advisor_comment": (
            f"사령관님의 우선순위를 반영한 가중합(Weighted Sum) 분석 결과 "
            f"{danji_name}의 맞춤 점수는 {score}점입니다.\n"
            f"가장 높은 기여 항목({top_domain})이 이 단지의 핵심 경쟁력입니다."
        ),
        "matching_verdict": (
            f"사령관님의 취향과 {match_pct}% 일치하는 단지입니다. "
            f"사령관님이 우려하시는 인프라 부족 요소가 전혀 없는 '클린' 단지입니다."
        ),
    }
