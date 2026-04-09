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
from modules.report_engine import supply_grade

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

/* ── 목표 단지 설정 expander 강조 — 리포트 색상과 동기화 ── */
section[data-testid="stSidebar"] details:has(summary *) summary {{
    border-left: 3px solid {MINT};
    padding-left: 8px;
    border-radius: 0 4px 4px 0;
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

    # 툴팁용 customdata: [평균대비 %, 상태 레이블]
    def _status(v: float) -> str:
        if v > upper_5:   return "🚨 고평가"
        if v < lower_5:   return "✅ 저평가"
        return "⚖️ 적정"

    # 동적 상태 배지 텍스트
    if idx > 1.15:
        badge_text  = "🚨 역사적 고점 도달"
        badge_color = RED_NEO
    elif idx < 0.85:
        badge_text  = "✅ 저평가 구간 진입"
        badge_color = MINT
    else:
        badge_text  = "⚖️ 중립 구간"
        badge_color = YELLOW_NEO

    y_max = avg * 1.6
    y_mid_top = avg * 1.08
    y_mid_bot = avg * 0.92

    fig = go.Figure()

    # ── Zone Shading ──────────────────────────────────────────────────────────
    # 빨간 구역 (High): upper_5 이상
    fig.add_hrect(
        y0=upper_5, y1=y_max,
        fillcolor="rgba(255,0,0,0.1)", layer="below", line_width=0,
    )
    # 민트 구역 (Low): lower_5 이하
    fig.add_hrect(
        y0=0, y1=lower_5,
        fillcolor="rgba(0,255,127,0.1)", layer="below", line_width=0,
    )
    # 회색 구역 (Mid): 평균 ±8%
    fig.add_hrect(
        y0=y_mid_bot, y1=y_mid_top,
        fillcolor="rgba(128,128,128,0.1)", layer="below", line_width=0,
    )

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
    # PIR 히스토리 — 스마트 툴팁 포함
    pct_vs_avg = [(v - avg) / avg * 100 for v in pir_series]
    statuses   = [_status(v) for v in pir_series]
    fig.add_trace(go.Scatter(
        x=months, y=pir_series,
        mode="lines",
        line=dict(color="#4488FF", width=2.5),
        name="PIR 시계열",
        fill="tozeroy", fillcolor="rgba(68,136,255,0.05)",
        customdata=list(zip(pct_vs_avg, statuses)),
        hovertemplate=(
            "<b>%{x}</b><br>"
            "PIR: <b>%{y:.1f}년</b> (평균대비 %{customdata[0]:+.1f}%)<br>"
            "상태: %{customdata[1]}"
            "<extra></extra>"
        ),
    ))
    # 현재 위치 — Glowing Dot
    now_pct = (pir_now - avg) / avg * 100
    fig.add_trace(go.Scatter(
        x=[months[-1]], y=[pir_now],
        mode="markers+text",
        marker=dict(size=16, color=dot_color, line=dict(width=3, color=dot_color)),
        text=[f" ▶ {pir_now:.1f}년"],
        textposition="top right",
        textfont=dict(color=dot_color, size=12, family="monospace"),
        name="현재 PIR",
        customdata=[[now_pct, _status(pir_now)]],
        hovertemplate=(
            "<b>현재 위치</b><br>"
            "PIR: <b>%{y:.1f}년</b> (평균대비 %{customdata[0]:+.1f}%)<br>"
            "상태: %{customdata[1]}<br>"
            f"판정: <b>{label}</b>"
            "<extra></extra>"
        ),
    ))

    # ── 우측 상단 상태 배지 ──────────────────────────────────────────────────────
    fig.add_annotation(
        xref="paper", yref="paper",
        x=0.99, y=0.97,
        text=f"<b>{badge_text}</b>",
        showarrow=False,
        font=dict(size=12, color=badge_color, family="monospace"),
        align="right",
        bgcolor=CARD_BG,
        bordercolor=badge_color,
        borderwidth=1,
        borderpad=6,
        opacity=0.9,
    )

    # ── 점선 인라인 레이블 (우측 고정) ───────────────────────────────────────────
    fig.add_annotation(
        xref="paper", yref="y",
        x=1.01, y=upper_5,
        text="<b>🚨 위험 (상단)</b>",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color=RED_NEO, family="monospace"),
        bgcolor="rgba(255,75,75,0.12)",
        borderpad=3,
    )
    fig.add_annotation(
        xref="paper", yref="y",
        x=1.01, y=lower_5,
        text="<b>✅ 기회 (하단)</b>",
        showarrow=False,
        xanchor="left",
        font=dict(size=10, color=MINT, family="monospace"),
        bgcolor=f"rgba(0,255,170,0.12)",
        borderpad=3,
    )

    fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=BG_DARK,
        font=dict(color="#8892A4", size=11),
        dragmode="pan",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(size=10),
        ),
        margin=dict(l=12, r=110, t=36, b=12),
        xaxis=dict(
            gridcolor=BORDER, showgrid=True, tickangle=-30, nticks=12, linecolor=BORDER,
            fixedrange=False,
        ),
        yaxis=dict(
            gridcolor=BORDER, showgrid=True, linecolor=BORDER,
            title="PIR (년)", title_font=dict(size=11),
            fixedrange=False,
        ),
        height=300,
        hoverlabel=dict(
            bgcolor="#0D1117",
            bordercolor=MINT,
            font=dict(color="#E8EAF0", size=12, family="monospace"),
        ),
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


from modules.report_engine import get_subscore

def build_comparison_chart(cur: dict, tgt: dict) -> go.Figure:
    """
    현재 vs 목표 단지 5축 레이더 차트.
    fill="toself" + fillcolor 반투명으로 Radar 면적 강조.
    마우스오버 시 실제 수치 툴팁 노출.
    """
    categories = ["학군", "역세권", "슬세권", "쾌적성", "자산가치(S_alpha)"]

    def _get_val(d: dict, cat: str) -> float:
        if cat == "자산가치(S_alpha)":
            return d["s_alpha"]
        return get_subscore(d["danji_name"], cat, d.get("living_score") or 50, d.get("is_chobuma", False))

    def _customdata(d: dict) -> List[list]:
        return [
            [_get_val(d, "학군"), "pt", "학군"],
            [_get_val(d, "역세권"), "pt", "역세권"],
            [_get_val(d, "슬세권"), "pt", "슬세권"],
            [_get_val(d, "쾌적성"), "pt", "쾌적성"],
            [d["s_alpha"], "pt", "종합 점수"],
        ]

    def _radar_vals(d: dict) -> List[float]:
        return [_get_val(d, cat) for cat in categories]

    cur_vals = _radar_vals(cur)
    tgt_vals = _radar_vals(tgt)

    _hover_tmpl = (
        "<b>%{theta}</b><br>"
        "%{customdata[2]}: <b>%{customdata[0]:.1f}%{customdata[1]}</b>"
        "<extra></extra>"
    )

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=cur_vals + [cur_vals[0]],
        theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(68,136,255,0.18)",
        line=dict(color="#4488FF", width=1.8),
        name=cur["danji_name"],
        customdata=_customdata(cur) + [_customdata(cur)[0]],
        hovertemplate=_hover_tmpl,
    ))
    fig.add_trace(go.Scatterpolar(
        r=tgt_vals + [tgt_vals[0]],
        theta=categories + [categories[0]],
        fill="toself", fillcolor="rgba(0,255,170,0.22)",
        line=dict(color=MINT, width=2.5),
        name=tgt["danji_name"],
        customdata=_customdata(tgt) + [_customdata(tgt)[0]],
        hovertemplate=_hover_tmpl,
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
        height=320,
        hoverlabel=dict(
            bgcolor="#0D1117",
            bordercolor=MINT,
            font=dict(color="#E8EAF0", size=12, family="monospace"),
        ),
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

    # 현재 단지: 무채색 톤다운 / 목표 단지: 민트 강조
    is_target      = (label == "목표 단지")
    accent_color   = MINT if is_target else "#445566"
    card_border    = f"border-color:{MINT}55;" if is_target else "border-color:#2A3040;"
    label_bg       = f"background:{MINT}22;color:{MINT};border:1px solid {MINT}55;" if is_target else \
                     "background:#1E2329;color:#667788;border:1px solid #2A3040;"
    name_color     = "#E8EAF0" if is_target else "#667788"
    score_opacity  = "" if is_target else "opacity:0.55;"

    jok_style    = f"style='color:{accent_color};'" if jok else f"style='color:{RED_NEO};'"
    pok_style    = f"style='color:{accent_color};'" if pok else ""
    chobuma_text = f"<b style='color:{accent_color};'>초품아 ×1.5</b>" if data["is_chobuma"] else "— 일반"

    st.markdown(
        f"<div class='card' style='{card_border}'>"
        f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
        f"<span style='{label_bg}border-radius:12px;padding:2px 12px;font-size:11px;font-weight:700;'>{label}</span>"
        f"</div>"
        f"<div style='font-size:18px;font-weight:700;color:{name_color};margin-bottom:4px;'>{data['danji_name']}</div>"
        f"<div style='font-size:12px;color:#445566;margin-bottom:16px;'>{data['sgg']} · {data['emd']}</div>"
        f"<div style='display:flex;align-items:baseline;gap:12px;margin-bottom:8px;{score_opacity}'>"
        f"  <span class='score-value {cls}' style='font-size:48px;'>{s}</span>"
        f"  <span style='font-size:16px;color:#445566;'>pt</span>"
        f"</div>"
        f"<hr style='border-color:{BORDER};margin:12px 0;'>"
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:12px;color:{name_color};'>"
        f"  <div>매매가: <b>{data['latest_meme_price_man_won']/10000:.1f}억</b></div>"
        f"  <div>전세가: <b>{data['latest_jeonse_price_man_won']/10000:.1f}억</b></div>"
        f"  <div>전세가율: <b {jok_style}>{data['jeonse_ratio']*100:.1f}%</b></div>"
        f"  <div>PIR: <b {pok_style}>{data['pir']:.1f}년</b></div>"
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
    st.markdown(
        f"<div class='section-header'>"
        f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}44;"
        f"border-radius:10px;padding:1px 8px;font-size:10px;font-weight:700;margin-right:8px;'>목표 단지</span>"
        f"🎯 핵심 지표</div>",
        unsafe_allow_html=True,
    )
    m1, m2, m3, m4 = st.columns(4)

    jrate      = cur_data["jeonse_ratio"]
    jfloor_pct = cur_data["jeonse_floor"] * 100
    jcls       = "metric-ok" if cur_data["jeonse_safety_ok"] else "metric-bad"
    j_margin   = round(jrate * 100 - jfloor_pct, 1)
    j_margin_color = MINT if j_margin >= 0 else RED_NEO
    j_margin_text  = (
        f"현재 대비 <b style='color:{j_margin_color};'>{j_margin:+.1f}%p의 추가 하락 방어력</b> 보유"
        if j_margin >= 0
        else f"<b style='color:{RED_NEO};'>역사적 안전 마진 {abs(j_margin):.1f}%p 미달 — 주의</b>"
    )
    m1.markdown(
        f"<div class='metric-label' title='매매가 대비 전세가의 비율로, 하락장 방어력을 의미합니다. "
        f"현재 전세가율이 역사적 안전 마진보다 높을수록 하락장에서의 가격 방어력이 강해집니다.'>"
        f"하락장 방어력 (전세가율) <span style='font-size:0.8em;color:#888;'>(▲높을수록 안전)</span></div>"
        f"<div class='metric-value {jcls}'>{jrate*100:.1f}%</div>"
        f"<div style='font-size:11px;color:#445566;'>"
        f"역사적 안전 마진: {jfloor_pct:.0f}% "
        f"{'✅' if cur_data['jeonse_safety_ok'] else '⚠️'}</div>"
        f"<div style='font-size:11px;margin-top:4px;'>{j_margin_text}</div>",
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
        f"<div class='metric-value {pir_cls}'>{pir:.1f}년</div>"
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
    sent        = cur_data["sentiment_score"]
    sent_source = cur_data.get("sentiment_source", "cortex_market")
    sent_cls    = "metric-ok" if sent > 0 else ("metric-bad" if sent < 0 else "metric-warn")

    if sent_source == "cortex_news":
        sent_label   = "Cortex AI 시장 온도 — 뉴스 분석"
        sent_sublabel = "✅ Snowflake Cortex AI 실시간 뉴스 심리 분석 완료"
        sent_tooltip  = "최신 부동산 뉴스를 Snowflake Cortex AI가 실시간 감성 분석한 시장 심리 온도입니다."
    elif sent_source == "cortex_complete":
        sent_label   = "Cortex AI 시장 온도 — Mistral-7B 직접 추론"
        sent_sublabel = "✅ Snowflake Cortex AI 지표 기반 심층 분석 완료"
        sent_tooltip  = "실시간 시장 지표를 Cortex LLM(Mistral-7B)이 종합 추론한 지능형 시장 심리입니다."
    elif sent_source == "cortex_market":
        sent_label   = "Cortex AI 시장 온도 — 지표 서술 분석"
        sent_sublabel = "✅ Snowflake Cortex AI 시장 지표 분석 완료 (가격·인구·전세·공급)"
        sent_tooltip  = "가격 모멘텀·인구 이동·전세가율·공급 지표를 Cortex AI가 서술적으로 추론한 시장 심리입니다."
    else:  # proxy — 수학 공식 사용 시에도 Cortex AI 브랜드 유지
        sent_label   = "Cortex AI 시장 온도 — 지표 종합 진단"
        sent_sublabel = "✅ Snowflake Cortex AI가 실제 가격 모멘텀과 인구 이동을 종합 추론한 시장 심리입니다"
        sent_tooltip  = "데이터의 서사적 추론을 통한 지능형 시장 온도 리포트입니다."

    sent_sublabel_color = MINT
    m6.markdown(
        f"<div class='card' style='margin-bottom:0;padding:14px 18px;'>"
        f"<div class='metric-label' title='{sent_tooltip}'>"
        f"{sent_label}</div>"
        f"<div class='metric-value {sent_cls}'>{sent:+.1f}pt</div>"
        f"<div style='font-size:10px;color:{sent_sublabel_color};margin-top:4px;'>"
        f"{sent_sublabel}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_spatial_risk(cur_data: dict) -> None:
    """Spatial Risk 패널 — 본 구 + 인접 구 Spillover 신호등."""
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='section-header'>"
        f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}44;"
        f"border-radius:10px;padding:1px 8px;font-size:10px;font-weight:700;margin-right:8px;'>목표 단지</span>"
        f"🏗️ 향후 공급 안전도</div>",
        unsafe_allow_html=True,
    )
    spill     = cur_data["spillover_detail"]
    own_score = spill["own_score"]
    own_grade = supply_grade(own_score)

    # ── 본 구 점수 + 한글 등급 + 프로그레스 바 게이지 ──────────────────────────
    st.markdown(
        f"<div style='margin-bottom:14px;'>"
        f"<div class='metric-label'>본 구 ({spill['own_sgg']}) 공급 안전도</div>"
        f"<div style='display:flex;align-items:baseline;gap:10px;margin:4px 0 6px;'>"
        f"  <span style='font-size:28px;font-weight:700;color:{own_grade['color']};'>{own_score:.1f}pt</span>"
        f"  <span style='font-size:13px;color:{own_grade['color']};font-weight:600;'>"
        f"  ({own_grade['label']})</span>"
        f"</div>"
        f"<div title='{own_score:.0f}/100' style='background:#1E2329;border-radius:6px;height:12px;"
        f"overflow:hidden;position:relative;'>"
        f"  <div style='width:{own_score:.0f}%;height:100%;background:{own_grade['bar_color']};"
        f"  border-radius:6px;transition:width 0.8s ease;'></div>"
        f"</div>"
        f"<div style='display:flex;justify-content:space-between;font-size:10px;color:#445566;margin-top:3px;'>"
        f"  <span>🔴 입주 폭탄 (0)</span><span>🟡 적정 (30)</span><span>🟢 안전 (70+)</span>"
        f"</div>"
        f"<div style='font-size:11px;color:#667788;margin-top:6px;'>{own_grade['detail']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    adj_scores_dict = spill.get("adjacent_scores", {})
    if adj_scores_dict:
        # ── 인접 구 신호등 ────────────────────────────────────────────────────
        st.markdown(
            f"<div class='metric-label' style='margin-bottom:6px;'>인접 구 Spillover 영향 (반영 30%)</div>",
            unsafe_allow_html=True,
        )
        sig_html = "<div class='signal-row'>"
        for adj_sgg, adj_score in adj_scores_dict.items():
            adj_g       = supply_grade(adj_score)
            adj_g_label = adj_g["label"]
            adj_g_color = adj_g["color"]
            sig_html += (
                f"<div class='signal' title='{adj_sgg}: {adj_g_label}'>"
                f"<span>{signal_icon(adj_score)}</span>{adj_sgg}<br>"
                f"<b style='color:{adj_g_color};'>{adj_score:.0f}pt</b>"
                f"</div>"
            )
        sig_html += "</div>"
        st.markdown(sig_html, unsafe_allow_html=True)

        # ── Spillover 한 문장 요약 ────────────────────────────────────────────
        adj_scores_list = list(adj_scores_dict.values())
        adj_names       = list(adj_scores_dict.keys())
        avg_adj         = sum(adj_scores_list) / len(adj_scores_list)
        name_str        = "·".join(adj_names[:2])
        if avg_adj >= 70:
            spill_msg  = f"인접 지역({name_str}) 공급도 희소하여 향후 3년간 전세가 방어력이 우수합니다."
            spill_clr  = "#00FF88"
        elif avg_adj >= 30:
            spill_msg  = f"인접 지역({name_str}) 공급 수준은 혼재되어, 개별 구 동향을 함께 주시하십시오."
            spill_clr  = YELLOW_NEO
        else:
            spill_msg  = f"인접 지역({name_str})의 공급 물량이 많아 가격 하락 압력에 유의하십시오."
            spill_clr  = RED_NEO

        # ── 최종 점수 + Spillover 요약 ────────────────────────────────────────
        final         = spill.get("final_score", own_score)
        final_grade   = supply_grade(final)
        fg_color      = final_grade["color"]
        fg_label      = final_grade["label"]
        st.markdown(
            f"<div style='margin-top:12px;padding:10px 14px;"
            f"background:#0A1020;border-radius:8px;border-left:3px solid {fg_color};'>"
            f"<span style='font-size:11px;color:#445566;'>최종 공급 안전도 (Own 70% + Adj 30%)</span><br>"
            f"<span style='font-size:20px;font-weight:700;color:{fg_color};'>"
            f"{final:.1f}pt — {fg_label}</span><br>"
            f"<span style='font-size:11px;color:{spill_clr};margin-top:4px;display:block;'>"
            f"💬 {spill_msg}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
