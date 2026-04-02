"""
modules/styles.py
Richgo-Cortex AI — Visual Design System

Responsibilities:
  - Design Tokens (색상 상수)
  - inject_css()         — Midnight Navy 테마 + Fade-in 애니메이션 전역 주입
  - build_pir_band_chart()   — Temporal Band Area Chart (60개월 시뮬레이션)
  - build_gauge()            — S_alpha 반원 게이지
  - build_comparison_chart() — 현재 vs 목표 레이더 차트
  - score_class()  / badge_class() / signal_icon() — 조건부 UI 헬퍼
"""
from typing import List

from datetime import datetime, timedelta

import numpy as np
import plotly.graph_objects as go
import streamlit as st

# ── Design Tokens ──────────────────────────────────────────────────────────────
BG_DARK    = "#0A0C10"
MINT       = "#00FFAA"
MINT_DIM   = "#00CC88"
GOLD       = "#FFD700"
RED_NEO    = "#FF4B4B"
YELLOW_NEO = "#FFD21E"
GREEN_NEO  = "#00FF88"
CARD_BG    = "#111418"
BORDER     = "#1E2329"


# ── CSS Injection ──────────────────────────────────────────────────────────────

def inject_css() -> None:
    """
    Midnight Navy(#0A0C10) 다크 테마 + Fade-in 애니메이션을 전역 주입합니다.
    app.py 최상단에서 st.set_page_config() 직후 한 번만 호출하십시오.
    """
    st.markdown(f"""
<style>
/* ── Global ── */
html, body, [class*="css"] {{
    background-color: {BG_DARK};
    color: #E8EAF0;
    font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
}}

/* ── Animation (Fade-in) ── */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
[data-testid="stSidebar"] {{
    animation: fadeIn 0.6s ease-out 0s both;
}}
.stMarkdown, .stPlotlyChart, div[data-testid="stAlert"] {{
    animation: fadeIn 0.6s ease-out 0.2s both;
}}
[data-testid="stVerticalBlock"] > div:nth-child(1) {{ animation-delay: 0.1s; }}
[data-testid="stVerticalBlock"] > div:nth-child(2) {{ animation-delay: 0.2s; }}
[data-testid="stVerticalBlock"] > div:nth-child(3) {{ animation-delay: 0.3s; }}
[data-testid="stVerticalBlock"] > div:nth-child(4) {{ animation-delay: 0.4s; }}

/* ── Button Alignment ── */
.stButton > button {{
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}}

/* ── Shadow Card (Glassmorphism) ── */
.card {{
    background: rgba(17, 20, 24, 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}}

/* ── Alert Styles ── */
div[data-testid="stAlert"] {{
    background-color: rgba(17, 20, 24, 0.8) !important;
    border: 1px solid {BORDER} !important;
    border-radius: 6px !important;
    color: #E8EAF0 !important;
}}
div[data-testid="stAlert"] svg {{ display: none !important; }}
div[data-testid="stAlert"] div[role="img"] {{ display: none !important; }}

/* ── Score Badge ── */
.score-value {{
    font-size: 72px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -2px;
}}
.score-mint {{
    color: {MINT};
    text-shadow: 0 0 20px {MINT}, 0 0 40px {MINT}88, 0 0 60px {MINT}44;
}}
.score-mid {{
    color: {YELLOW_NEO};
    text-shadow: 0 0 12px {YELLOW_NEO}88;
}}
.score-low {{
    color: {RED_NEO};
    text-shadow: 0 0 8px {RED_NEO}88;
}}

/* ── Confidence Badge ── */
.badge {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
.badge-high   {{ background: {GREEN_NEO}22; color: {GREEN_NEO}; border: 1px solid {GREEN_NEO}66; }}
.badge-medium {{ background: {YELLOW_NEO}22; color: {YELLOW_NEO}; border: 1px solid {YELLOW_NEO}66; }}
.badge-low    {{ background: {RED_NEO}22;    color: {RED_NEO};    border: 1px solid {RED_NEO}66; }}

/* ── Metric Row ── */
.metric-label {{
    font-size: 12px;
    color: #6B7A99;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
}}
.metric-value {{
    font-size: 22px;
    font-weight: 700;
    color: #E8EAF0;
}}
.metric-ok   {{ color: {MINT}; }}
.metric-warn {{ color: {YELLOW_NEO}; }}
.metric-bad  {{ color: {RED_NEO}; }}

/* ── Signal Light ── */
.signal-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-top:8px; }}
.signal {{
    display:flex; flex-direction:column; align-items:center;
    background:{CARD_BG}; border:1px solid {BORDER};
    border-radius:10px; padding:10px 14px; min-width:90px;
    font-size:11px; color:#8892A4;
}}
.signal span {{ font-size:22px; margin-bottom:4px; }}

/* ── Alpha Trigger Banner ── */
.alpha-banner {{
    background: linear-gradient(135deg, #1A1200 0%, #2D2000 100%);
    border: 2px solid {GOLD};
    border-radius: 14px;
    padding: 24px 32px;
    text-align: center;
    box-shadow: 0 0 30px {GOLD}44, 0 0 60px {GOLD}22;
    margin: 16px 0;
}}
.alpha-title {{
    font-size: 22px;
    font-weight: 800;
    color: {GOLD};
    text-shadow: 0 0 16px {GOLD}88;
    margin-bottom: 8px;
}}
.alpha-delta {{
    font-size: 40px;
    font-weight: 900;
    color: {GOLD};
    text-shadow: 0 0 24px {GOLD};
}}

/* ── Section Header ── */
.section-header {{
    font-size: 13px;
    font-weight: 600;
    color: {MINT};
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid {BORDER};
}}

/* ── Sidebar overrides ── */
section[data-testid="stSidebar"] {{
    background: #0A0E16;
    border-right: 1px solid {BORDER};
}}
</style>
""", unsafe_allow_html=True)


# ── Chart Builders ─────────────────────────────────────────────────────────────

def build_pir_band_chart(result: dict) -> go.Figure:
    """
    PIR Band Area Chart (60개월 시뮬레이션).

    Layers:
      - 회색 밴드: ±15% 안전/위험 구간
      - 파란 선: PIR 히스토리 (시뮬레이션)
      - 네온 닷: 현재 위치 (Glowing Dot) — 저평가=Mint / 과열=Red / 중립=Yellow
    """
    pir_now = result["pir"]
    avg     = result["pir_5yr_avg"]
    upper_5 = avg * 1.15
    lower_5 = avg * 0.85
    label   = result["pir_band_label"]
    idx     = result["pir_relative_index"]

    # 60개월 시뮬레이션 시계열
    np.random.seed(42)
    n      = 60
    months = [
        (datetime(2021, 4, 1) + timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(n)
    ]
    noise      = np.random.normal(0, avg * 0.04, n).cumsum() * 0.15
    drift      = np.linspace(avg * 1.08, pir_now, n)
    pir_series = np.clip(drift + noise, avg * 0.6, avg * 1.5)
    pir_series[-1] = pir_now

    dot_color = MINT if idx < 0.85 else (RED_NEO if idx > 1.15 else YELLOW_NEO)

    fig = go.Figure()

    # 위험 구간 상단 경계
    fig.add_trace(go.Scatter(
        x=months, y=[upper_5] * n,
        fill=None, mode="lines",
        line=dict(color=RED_NEO, width=1, dash="dot"),
        name="고점 경계 (+15%)",
    ))
    # 안전 구간 밴드 (fill)
    fig.add_trace(go.Scatter(
        x=months, y=[lower_5] * n,
        fill="tonexty", fillcolor="rgba(0,255,170,0.06)",
        mode="lines",
        line=dict(color=MINT, width=1, dash="dot"),
        name="저평가 경계 (−15%)",
    ))
    # 5년 평균선
    fig.add_trace(go.Scatter(
        x=months, y=[avg] * n,
        mode="lines",
        line=dict(color="#445566", width=1.5, dash="dash"),
        name=f"5yr 평균 ({avg:.1f})",
    ))
    # PIR 히스토리
    fig.add_trace(go.Scatter(
        x=months, y=pir_series,
        mode="lines",
        line=dict(color="#4488FF", width=2.5),
        name="PIR 시계열",
        fill="tozeroy", fillcolor="rgba(68,136,255,0.05)",
    ))
    # 현재 위치 — Glowing Dot
    fig.add_trace(go.Scatter(
        x=[months[-1]], y=[pir_now],
        mode="markers+text",
        marker=dict(size=16, color=dot_color, line=dict(width=3, color=dot_color)),
        text=[f" ▶ {pir_now:.1f}yr\n{label}"],
        textposition="top right",
        textfont=dict(color=dot_color, size=12, family="monospace"),
        name="현재 PIR",
    ))

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=BG_DARK,
        font=dict(color="#8892A4", size=11),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        ),
        margin=dict(l=12, r=12, t=36, b=12),
        xaxis=dict(gridcolor=BORDER, showgrid=True, tickangle=-30, nticks=12, linecolor=BORDER),
        yaxis=dict(gridcolor=BORDER, showgrid=True, linecolor=BORDER,
                   title="PIR (년)", title_font=dict(size=11)),
        height=280,
    )
    return fig


def build_gauge(score: int) -> go.Figure:
    """S_alpha 반원 게이지. 80pt 이상=Mint / 60pt 이상=Yellow / 미만=Red."""
    bar_color = MINT if score >= 80 else (YELLOW_NEO if score >= 60 else RED_NEO)

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(font=dict(size=56, color=bar_color, family="monospace"), suffix="pt"),
        gauge=dict(
            axis=dict(
                range=[0, 100], tickwidth=1, tickcolor=BORDER,
                tickfont=dict(color="#445566", size=10),
            ),
            bar=dict(color=bar_color, thickness=0.3),
            bgcolor=CARD_BG,
            borderwidth=0,
            steps=[
                dict(range=[0,  60], color="#1A1A2A"),
                dict(range=[60, 80], color="#1A2210"),
                dict(range=[80, 100], color="#0A2018"),
            ],
            threshold=dict(line=dict(color=GOLD, width=3), thickness=0.9, value=80),
        ),
    ))
    fig.update_layout(
        paper_bgcolor=CARD_BG,
        font=dict(color="#E8EAF0"),
        margin=dict(l=20, r=20, t=20, b=0),
        height=200,
    )
    return fig


def build_comparison_chart(cur: dict, tgt: dict) -> go.Figure:
    """
    현재 vs 목표 단지 5축 레이더 차트.
    fill="toself" + fillcolor 반투명으로 Radar 면적 강조.
    """
    categories = ["공급점수", "PIR점수", "전세가율", "뉴스심리", "종합"]

    def _radar_vals(d: dict) -> List[float]:
        return [
            d["supply_score_final"],
            (1 - min(1.0, d["pir_relative_index"])) * 100,
            d["jeonse_ratio"] * 100,
            (d["sentiment_score"] + 5) * 10,
            d["s_alpha"],
        ]

    cur_vals = _radar_vals(cur)
    tgt_vals = _radar_vals(tgt)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=cur_vals + [cur_vals[0]],
        theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(68,136,255,0.30)",
        line=dict(color="#4488FF", width=2),
        name=cur["danji_name"],
    ))
    fig.add_trace(go.Scatterpolar(
        r=tgt_vals + [tgt_vals[0]],
        theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(0,255,170,0.30)",
        line=dict(color=MINT, width=2.5),
        name=tgt["danji_name"],
    ))
    fig.update_layout(
        paper_bgcolor=CARD_BG,
        polar=dict(
            bgcolor=BG_DARK,
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor=BORDER, linecolor=BORDER,
                tickfont=dict(color="#445566", size=9),
            ),
            angularaxis=dict(
                linecolor=BORDER, gridcolor=BORDER,
                tickfont=dict(color="#8892A4", size=11),
            ),
        ),
        legend=dict(font=dict(color="#8892A4", size=11), bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )
    return fig


# ── Conditional UI Helpers ─────────────────────────────────────────────────────

def score_class(s: int) -> str:
    """점수에 따른 CSS 클래스 반환."""
    if s >= 80: return "score-mint"
    if s >= 60: return "score-mid"
    return "score-low"


def badge_class(label: str) -> str:
    """신뢰도 레이블에 따른 Badge CSS 클래스 반환."""
    return {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}.get(
        label, "badge-low"
    )


def signal_icon(score: float) -> str:
    """공급 점수에 따른 신호등 이모지 반환."""
    if score >= 70: return "🟢"
    if score >= 40: return "🟡"
    return "🔴"


# ── Composite UI Renderers (streamlit 의존 컴포넌트) ──────────────────────────

def render_danji_card(data: dict, label: str) -> None:
    """단지 비교 카드 — 점수 + 8개 핵심 지표 그리드."""
    s   = data["s_alpha"]
    cls = score_class(s)
    jok = data["jeonse_safety_ok"]
    pok = data["pir_undervalue_ok"]

    jok_style    = f"style='color:{MINT};'" if jok else f"style='color:{RED_NEO};'"
    pok_style    = f"style='color:{MINT};'" if pok else ""
    chobuma_text = f"<b style='color:{MINT};'>초품아 ×1.5</b>" if data["is_chobuma"] else "— 일반"

    st.markdown(
        f"<div class='card'>"
        f"<div class='section-header'>{label}</div>"
        f"<div style='font-size:18px;font-weight:700;color:#E8EAF0;margin-bottom:4px;'>{data['danji_name']}</div>"
        f"<div style='font-size:12px;color:#445566;margin-bottom:16px;'>{data['sgg']} · {data['emd']}</div>"
        f"<div style='display:flex;align-items:baseline;gap:12px;margin-bottom:8px;'>"
        f"  <span class='score-value {cls}' style='font-size:48px;'>{s}</span>"
        f"  <span style='font-size:16px;color:#445566;'>pt</span>"
        f"</div>"
        f"<hr style='border-color:{BORDER};margin:12px 0;'>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;'>"
        f"  <div>매매가: <b>{data['latest_meme_price_man_won']/10000:.1f}억</b></div>"
        f"  <div>전세가: <b>{data['latest_jeonse_price_man_won']/10000:.1f}억</b></div>"
        f"  <div>전세가율: <b {jok_style}>{data['jeonse_ratio']*100:.1f}%</b></div>"
        f"  <div>PIR: <b {pok_style}>{data['pir']:.1f}yr</b></div>"
        f"  <div>공급점수: <b>{data['supply_score_final']:.1f}pt</b></div>"
        f"  <div>심리점수: <b>{data['sentiment_score']:+.1f}pt</b></div>"
        f"  <div>LIVING: <b>{data['living_score']}/100</b></div>"
        f"  <div>{chobuma_text}</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_key_metrics(cur_data: dict) -> None:
    """핵심 지표 4열 + 생활/감성 2열 렌더링."""
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>핵심 지표</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)

    jrate      = cur_data["jeonse_ratio"]
    jfloor_pct = cur_data["jeonse_floor"] * 100
    jcls       = "metric-ok" if cur_data["jeonse_safety_ok"] else "metric-bad"
    m1.markdown(
        f"<div class='metric-label' title='매매가 대비 전세가의 비율로, 하락장 방어력을 의미합니다. "
        f"현재 전세가율이 역사적 안전 마진보다 높을수록 하락장에서의 가격 방어력이 강해집니다.'>"
        f"하락장 방어력 (전세가율) <span style='font-size:0.8em;color:#888;'>(▲높을수록 안전)</span></div>"
        f"<div class='metric-value {jcls}'>{jrate*100:.1f}%</div>"
        f"<div style='font-size:11px;color:#445566;'>"
        f"역사적 안전 마진: {jfloor_pct:.0f}% "
        f"{'✅' if cur_data['jeonse_safety_ok'] else '⚠️'}</div>",
        unsafe_allow_html=True,
    )

    pir     = cur_data["pir"]
    pir_avg = cur_data["pir_5yr_avg"]
    pir_cls = "metric-ok" if cur_data["pir_undervalue_ok"] else (
        "metric-warn" if cur_data["pir_relative_index"] < 1.15 else "metric-bad"
    )
    m2.markdown(
        f"<div class='metric-label' "
        f"title='이 수치는 개인 소득이 아닌, 통계청 발표 서울 가구 중위 소득을 기준으로 한 "
        f"단지의 절대적 가격 높낮이입니다. 낮을수록 현재 가격이 소득 대비 저평가 상태입니다.'>"
        f"내 월급으로 이 집을 사려면 (연수) <span style='font-size:0.8em;color:#888;'>(▼낮을수록 유리)</span></div>"
        f"<div class='metric-value {pir_cls}'>{pir:.1f}yr</div>"
        f"<div style='font-size:11px;color:#445566;'>"
        f"서울 평균 소득 기준 &nbsp;|&nbsp; 5yr avg {pir_avg:.1f} | {cur_data['pir_band_label']}</div>",
        unsafe_allow_html=True,
    )

    sup     = cur_data["supply_score_final"]
    sup_cls = "metric-ok" if sup >= 70 else ("metric-warn" if sup >= 40 else "metric-bad")
    m3.markdown(
        f"<div class='metric-label' title='과잉 공급이 인접 지역 매매가에 미치는 위험도를 측정합니다.'>"
        f"인근 지역 공급 폭탄 위험도 <span style='font-size:0.8em;color:#888;'>(▼낮을수록 유리)</span></div>"
        f"<div class='metric-value {sup_cls}'>{sup:.1f}pt</div>"
        f"<div style='font-size:11px;color:#445566;'>Raw {cur_data['supply_score_raw']:.1f} | Spillover 적용</div>",
        unsafe_allow_html=True,
    )

    price = cur_data["latest_meme_price_man_won"]
    m4.markdown(
        f"<div class='metric-label'>매매가 (Richgo)</div>"
        f"<div class='metric-value'>{price/10000:.1f}억</div>"
        f"<div style='font-size:11px;color:#445566;'>전세 {cur_data['latest_jeonse_price_man_won']/10000:.1f}억</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    m5, m6 = st.columns(2)
    chobuma_clr = MINT if cur_data["is_chobuma"] else "#445566"
    chobuma_lbl = "교육/생활 인프라 프리미엄 반영" if cur_data["is_chobuma"] else "— 교육 인프라 특이점 없음"
    m5.markdown(
        f"<div class='card' style='margin-bottom:0;padding:14px 18px;'>"
        f"<div class='metric-label' title='역세권, 학세권 등의 실생활 가치 측정 점수입니다.'>생활/교육 점수</div>"
        f"<div style='font-size:20px;font-weight:700;color:#E8EAF0;'>{cur_data['living_score']}/100</div>"
        f"<div style='font-size:11px;color:{chobuma_clr};margin-top:4px;'>{chobuma_lbl}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    sent     = cur_data["sentiment_score"]
    sent_cls = "metric-ok" if sent > 0 else "metric-bad"
    m6.markdown(
        f"<div class='card' style='margin-bottom:0;padding:14px 18px;'>"
        f"<div class='metric-label' "
        f"title='Snowflake Cortex LLM이 최신 뉴스 1,000건을 실시간 분석한 시장의 감정 온도입니다. "
        f"+값은 긍정적, −값은 부정적 시장 심리를 의미합니다.'>"
        f"Snowflake Cortex AI 뉴스 심리</div>"
        f"<div class='metric-value {sent_cls}'>{sent:+.1f}pt</div>"
        f"<div style='font-size:10px;color:#445566;margin-top:4px;'>"
        f"Cortex LLM · 뉴스 1,000건 실시간 분석</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_spatial_risk(cur_data: dict) -> None:
    """Spatial Risk 패널 — 본 구 + 인접 구 Spillover 신호등."""
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Spatial Risk — 인접구 공급 신호</div>", unsafe_allow_html=True)
    spill     = cur_data["spillover_detail"]
    own_score = spill["own_score"]
    st.markdown(
        f"<div style='margin-bottom:12px;'>"
        f"<div class='metric-label'>본 구 ({spill['own_sgg']})</div>"
        f"<div style='font-size:28px;font-weight:700;'>"
        f"{signal_icon(own_score)} <span style='color:#E8EAF0;'>{own_score:.1f}pt</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    if spill.get("adjacent_sggs"):
        st.markdown("<div class='metric-label'>인접 구 Spillover (30%)</div>", unsafe_allow_html=True)
        sig_html = "<div class='signal-row'>"
        for adj_sgg, adj_score in spill.get("adjacent_scores", {}).items():
            sig_html += (
                f"<div class='signal' title='{adj_sgg}'>"
                f"<span>{signal_icon(adj_score)}</span>{adj_sgg}<br>"
                f"<b style='color:#E8EAF0;'>{adj_score:.0f}pt</b>"
                f"</div>"
            )
        sig_html += "</div>"
        st.markdown(sig_html, unsafe_allow_html=True)
        final = spill.get("final_score", own_score)
        st.markdown(
            f"<div style='margin-top:14px;padding:10px 14px;"
            f"background:#0A1020;border-radius:8px;border-left:3px solid {MINT};'>"
            f"<span style='font-size:11px;color:#445566;'>최종 공급 점수 (Own 70% + Adj 30%)</span><br>"
            f"<span style='font-size:20px;font-weight:700;color:{MINT};'>{final:.1f}pt</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
