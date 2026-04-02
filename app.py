"""
Richgo-Cortex AI Assistant — Strategic Command Center (관제탑)
High-End Dashboard v1.0  |  Model C+  |  2026-04-02

Run:  streamlit run app.py
"""

import os
import math
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv

load_dotenv()

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Richgo-Cortex AI | 관제탑",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design Tokens ─────────────────────────────────────────────────────────────
BG_DARK    = "#0E1117"
MINT       = "#00FFAA"
MINT_DIM   = "#00CC88"
GOLD       = "#FFD700"
RED_NEO    = "#FF4B4B"
YELLOW_NEO = "#FFD21E"
GREEN_NEO  = "#00FF88"
CARD_BG    = "#161B25"
BORDER     = "#1E2736"

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* ── Global ── */
html, body, [class*="css"] {{
    background-color: {BG_DARK};
    color: #E8EAF0;
    font-family: 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
}}

/* ── Shadow Card ── */
.card {{
    background: #1A1A1A;
    border: 1px solid #333333;
    border-radius: 4px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: none;
}}

/* ── Alert Styles ── */
div[data-testid="stAlert"] {{
    background-color: #1E1E1E !important;
    border: 1px solid #333333 !important;
    border-radius: 4px !important;
    color: #E8EAF0 !important;
}}
div[data-testid="stAlert"] svg {{
    display: none !important;
}}
div[data-testid="stAlert"] div[role="img"] {{
    display: none !important;
}}

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


# ── Alpha-Trigger Constants ───────────────────────────────────────────────────
ALPHA_TRIGGER_DELTA = 20
ALPHA_TRIGGER_MIN   = 80

# ── Dynamic Danji List Loading ────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_all_danji_list(_engine):
    """Snowflake DB 전 지역 단지 실시간 동기화."""
    if not _engine:
        return []
    try:
        # 전국구 지역 개방형 쿼리 유지 (SD 필터링 없음)
        query = """
        SELECT DANJI_ID, SD, SGG, DANJI 
        FROM RICHGO_KR.HACKATHON_2026.DANJI_APT_INFO 
        ORDER BY SD ASC, SGG ASC, DANJI ASC
        """
        cur = _engine._client.conn.cursor()
        cur.execute(query)
        rows = cur.fetchall()
        return [{"DANJI_ID": r[0], "SD": r[1], "SGG": r[2], "DANJI_NAME": r[3]} for r in rows]
    except Exception as e:
        st.error(f"단지 목록 동기화 실패: {e}")
        return []


# ── Snowflake Connection ──────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_engine():
    """실제 Snowflake 연결 시도. 실패 시 None 반환 (Demo 모드 전환)."""
    try:
        import snowflake.connector
        from src.core.engine import RichgoCortexEngine
        conn = snowflake.connector.connect(
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            user=os.getenv("SNOWFLAKE_USER"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            role=os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "RICHGO_KR"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "HACKATHON_2026"),
        )
        return RichgoCortexEngine(conn)
    except Exception:
        return None


# ── Chart Builders ────────────────────────────────────────────────────────────
def build_pir_band_chart(result: dict) -> go.Figure:
    """
    PIR Band Area Chart (60개월).
    - 회색 밴드: ±15% 구간
    - 파란 선: PIR 히스토리 (시뮬레이션)
    - 네온 닷: 현재 위치 (Glowing Dot)
    """
    pir_now   = result["pir"]
    avg       = result["pir_5yr_avg"]
    upper_5   = avg * 1.15
    lower_5   = avg * 0.85
    label     = result["pir_band_label"]
    idx       = result["pir_relative_index"]

    # 60개월 시뮬레이션 시계열 생성
    np.random.seed(42)
    n = 60
    months = [
        (datetime(2021, 4, 1) + timedelta(days=30 * i)).strftime("%Y-%m")
        for i in range(n)
    ]
    noise = np.random.normal(0, avg * 0.04, n).cumsum() * 0.15
    drift = np.linspace(avg * 1.08, pir_now, n)
    pir_series = np.clip(drift + noise, avg * 0.6, avg * 1.5)
    pir_series[-1] = pir_now

    # 색상 결정
    if idx < 0.85:
        dot_color = MINT
        dot_glow  = MINT
    elif idx > 1.15:
        dot_color = RED_NEO
        dot_glow  = RED_NEO
    else:
        dot_color = YELLOW_NEO
        dot_glow  = YELLOW_NEO

    fig = go.Figure()

    # 위험 구간 (upper 이상)
    fig.add_trace(go.Scatter(
        x=months, y=[upper_5] * n,
        fill=None, mode="lines",
        line=dict(color=RED_NEO, width=1, dash="dot"),
        name="고점 경계 (+15%)",
    ))
    # 안전 구간 밴드
    fig.add_trace(go.Scatter(
        x=months, y=[lower_5] * n,
        fill="tonexty",
        fillcolor="rgba(0,255,170,0.06)",
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
        fill="tozeroy",
        fillcolor="rgba(68,136,255,0.05)",
    ))
    # 현재 위치 — Glowing Dot
    fig.add_trace(go.Scatter(
        x=[months[-1]], y=[pir_now],
        mode="markers+text",
        marker=dict(
            size=16, color=dot_color,
            line=dict(width=3, color=dot_color),
            symbol="circle",
        ),
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
        xaxis=dict(
            gridcolor=BORDER, showgrid=True, tickangle=-30,
            nticks=12, linecolor=BORDER,
        ),
        yaxis=dict(
            gridcolor=BORDER, showgrid=True, linecolor=BORDER,
            title="PIR (년)", title_font=dict(size=11),
        ),
        height=280,
    )
    return fig


def build_gauge(score: int) -> go.Figure:
    """S_alpha 반원 게이지."""
    if score >= 80:
        bar_color = MINT
    elif score >= 60:
        bar_color = YELLOW_NEO
    else:
        bar_color = RED_NEO

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(
            font=dict(size=56, color=bar_color, family="monospace"),
            suffix="pt",
        ),
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
            threshold=dict(
                line=dict(color=GOLD, width=3),
                thickness=0.9,
                value=80,
            ),
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
    """현재 vs 목표 레이더 차트."""
    categories = ["공급점수", "PIR점수", "전세가율", "뉴스심리", "종합"]

    def pct(v, lo, hi):
        return round(max(0, min(100, (v - lo) / (hi - lo) * 100)))

    cur_vals = [
        cur["supply_score_final"],
        (1 - min(1, cur["pir_relative_index"])) * 100,
        cur["jeonse_ratio"] * 100,
        (cur["sentiment_score"] + 5) * 10,
        cur["s_alpha"],
    ]
    tgt_vals = [
        tgt["supply_score_final"],
        (1 - min(1, tgt["pir_relative_index"])) * 100,
        tgt["jeonse_ratio"] * 100,
        (tgt["sentiment_score"] + 5) * 10,
        tgt["s_alpha"],
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=cur_vals + [cur_vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(68,136,255,0.15)",
        line=dict(color="#4488FF", width=2),
        name=cur["danji_name"],
    ))
    fig.add_trace(go.Scatterpolar(
        r=tgt_vals + [tgt_vals[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"rgba(0,255,170,0.12)",
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
        legend=dict(
            font=dict(color="#8892A4", size=11),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=40, r=40, t=40, b=40),
        height=300,
    )
    return fig


# ── Score Color Helper ────────────────────────────────────────────────────────
def score_class(s: int) -> str:
    if s >= 80:  return "score-mint"
    if s >= 60:  return "score-mid"
    return "score-low"

def badge_class(label: str) -> str:
    return {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}.get(label, "badge-low")

def signal_icon(score: float) -> str:
    if score >= 70: return ""
    if score >= 40: return ""
    return ""


# ── Helper: Cascading Selector ────────────────────────────────────────────────
def render_cascading_selector(danji_list: list, prefix: str):
    sd_list = sorted(list(set([d["SD"] for d in danji_list if d.get("SD")])))
    if not sd_list: return None
    
    sd_key = f"{prefix}_sd"
    sgg_key = f"{prefix}_sgg"
    danji_key = f"{prefix}_danji"
    
    if sd_key not in st.session_state:
        st.session_state[sd_key] = sd_list[0]
        
    selected_sd = st.selectbox("시/도", sd_list, key=sd_key)
    
    sgg_list = sorted(list(set([d["SGG"] for d in danji_list if d.get("SD") == selected_sd and d.get("SGG")])))
    if not sgg_list: return None
    
    if sgg_key not in st.session_state or st.session_state[sgg_key] not in sgg_list:
        st.session_state[sgg_key] = sgg_list[0]
        
    selected_sgg = st.selectbox("시/군/구", sgg_list, key=sgg_key)
    
    filtered_danji = sorted([d for d in danji_list if d.get("SD") == selected_sd and d.get("SGG") == selected_sgg], key=lambda x: x.get("DANJI_NAME", ""))
    if not filtered_danji: return None
        
    selected_danji = st.selectbox(
        "단지명", 
        filtered_danji, 
        format_func=lambda x: x.get("DANJI_NAME", ""),
        key=danji_key
    )
    return selected_danji


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<div style='color:{MINT};font-size:22px;font-weight:800;'>Richgo-Cortex AI</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#445566;font-size:12px;margin-bottom:16px;'>Strategic Command Center v1.0</div>", unsafe_allow_html=True)
    st.markdown("---")

    engine = get_engine()
    if engine:
        st.markdown(f"<span style='color:{MINT};font-size:12px;'>● LIVE — Snowflake 연결됨</span>", unsafe_allow_html=True)
        mode = "live"
    else:
        st.markdown(f"<span style='color:{YELLOW_NEO};font-size:12px;'>● DEMO — 연결 없음</span>", unsafe_allow_html=True)
        mode = "demo"

    st.markdown("---")
    st.markdown("<div class='section-header'>전 지역 단지 검색</div>", unsafe_allow_html=True)

    danji_list = get_all_danji_list(engine)
    if not danji_list:
        st.warning("데이터 동기화 대기 중... Snowflake 연결을 확인하세요.")
        st.stop()

    with st.expander("현재 단지 설정", expanded=True):
        selected_current = render_cascading_selector(danji_list, "cur")
        
    with st.expander("목표 단지 설정", expanded=False):
        selected_target = render_cascading_selector(danji_list, "tgt")


    if selected_current and selected_target:
        is_same_danji = selected_current['DANJI_ID'] == selected_target['DANJI_ID']
    else:
        is_same_danji = True

    if is_same_danji:
        st.warning("현재 단지와 목표 단지가 동일합니다. 다른 단지를 선택하십시오.")
        
    if st.button("통합 분석 실행", use_container_width=True, disabled=is_same_danji):
        with st.spinner("Snowflake 라이브 쿼리 중..."):
            try:
                st.session_state["cur_data"] = engine.analyze(selected_current["DANJI_ID"])
                st.session_state["tgt_data"] = engine.analyze(selected_target["DANJI_ID"])
                st.success("분석 완료! 관제탑을 갱신합니다.")
            except Exception as e:
                st.error(f"오류 발생: {e}")

    st.markdown("---")
    st.markdown(
        "<div style='color:#445566;font-size:11px;line-height:1.8;'>"
        "Model C+ | Plan Freeze 2026-04-01<br>"
        "Richgo × Snowflake Cortex AI<br>"
        f"<span style='color:{MINT}'>Alpha-Trigger ≥ 80pt Δ≥20</span>"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Data Loading ──────────────────────────────────────────────────────────────
if "cur_data" in st.session_state and "tgt_data" in st.session_state:
    cur_data = st.session_state["cur_data"]
    tgt_data = st.session_state["tgt_data"]
else:
    st.info("좌측 사이드바에서 단지를 검색하고 **[통합 분석 실행]** 버튼을 클릭하십시오.")
    st.stop()
# Variables are correctly loaded from session state above.


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f"<div style='display:flex;align-items:baseline;gap:16px;margin-bottom:4px;'>"
    f"<span style='font-size:26px;font-weight:800;color:#E8EAF0;'>관제탑</span>"
    f"<span style='font-size:13px;color:#445566;font-family:monospace;'>STRATEGIC COMMAND CENTER</span>"
    f"</div>",
    unsafe_allow_html=True,
)
st.markdown(
    f"<div style='font-size:12px;color:#445566;margin-bottom:24px;'>"
    f"{cur_data['analysis_date']} &nbsp;|&nbsp; "
    f"{cur_data['danji_name']} ({cur_data['sgg']}) &nbsp;|&nbsp; "
    f"<span style='color:{MINT}'>Richgo-Cortex AI Model C+</span>"
    f"</div>",
    unsafe_allow_html=True,
)


# ── ROW 1: Main Score + Key Metrics ──────────────────────────────────────────
col_gauge, col_metrics = st.columns([1, 2])

with col_gauge:
    conf_lbl = cur_data["confidence_label"]
    trigger_html = f"<div style='color:{MINT};font-size:12px;font-weight:700;margin-top:8px;'>즉시 실행 트리거 발동</div>" if cur_data['execution_trigger'] else ""
    st.markdown(
        f"<div class='card'>"
        f"<div class='section-header'>S_alpha 종합 점수</div>"
        f"<div class='score-value {score_class(cur_data['s_alpha'])}'>{cur_data['s_alpha']}</div>"
        f"<div style='margin-top:8px;'>"
        f"<span class='badge {badge_class(conf_lbl)}'>"
        f"{conf_lbl} &nbsp; {cur_data['confidence_pct']:.0f}%"
        f"</span>"
        f"</div>"
        f"<div style='color:#445566;font-size:11px;margin-top:12px;'>"
        f"Band 보정 전: {cur_data['s_alpha_before_band']}pt &nbsp;"
        f"PIR 조정: {cur_data['pir_band_adjustment']:+.0f}pt"
        f"</div>"
        f"{trigger_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(build_gauge(cur_data["s_alpha"]), use_container_width=True, config={"displayModeBar": False})

with col_metrics:
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>핵심 지표</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)

    # 전세가율
    jrate = cur_data["jeonse_ratio"]
    jfloor = cur_data["jeonse_floor"]
    jcls = "metric-ok" if cur_data["jeonse_safety_ok"] else "metric-bad"
    m1.markdown(
        f"<div class='metric-label'>전세가율</div>"
        f"<div class='metric-value {jcls}'>{jrate*100:.1f}%</div>"
        f"<div style='font-size:11px;color:#445566;'>바닥 {jfloor*100:.0f}% {'' if cur_data['jeonse_safety_ok'] else ''}</div>",
        unsafe_allow_html=True,
    )

    # PIR
    pir = cur_data["pir"]
    pir_avg = cur_data["pir_5yr_avg"]
    pir_lbl = cur_data["pir_band_label"]
    pir_cls = "metric-ok" if cur_data["pir_undervalue_ok"] else ("metric-warn" if cur_data["pir_relative_index"] < 1.15 else "metric-bad")
    m2.markdown(
        f"<div class='metric-label'>PIR 지수</div>"
        f"<div class='metric-value {pir_cls}'>{pir:.1f}yr</div>"
        f"<div style='font-size:11px;color:#445566;'>5yr avg {pir_avg:.1f} | {pir_lbl}</div>",
        unsafe_allow_html=True,
    )

    # 공급점수
    sup = cur_data["supply_score_final"]
    sup_cls = "metric-ok" if sup >= 70 else ("metric-warn" if sup >= 40 else "metric-bad")
    m3.markdown(
        f"<div class='metric-label'>공급 점수</div>"
        f"<div class='metric-value {sup_cls}'>{sup:.1f}pt</div>"
        f"<div style='font-size:11px;color:#445566;'>Raw {cur_data['supply_score_raw']:.1f} | Spillover 적용</div>",
        unsafe_allow_html=True,
    )

    # 매매가
    price = cur_data["latest_meme_price_man_won"]
    price_eok = price / 10000
    m4.markdown(
        f"<div class='metric-label'>매매가 (Richgo)</div>"
        f"<div class='metric-value'>{price_eok:.1f}억</div>"
        f"<div style='font-size:11px;color:#445566;'>전세 {cur_data['latest_jeonse_price_man_won']/10000:.1f}억</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # 초품아 & 뉴스
    m5, m6 = st.columns(2)
    chobuma_icon = "초품아 ×1.5 가중" if cur_data["is_chobuma"] else "— 초품아 비해당"
    chobuma_clr = MINT if cur_data["is_chobuma"] else "#445566"
    m5.markdown(
        f"<div class='card' style='margin-bottom:0;padding:14px 18px;'>"
        f"<div class='metric-label'>생활/교육 점수</div>"
        f"<div style='font-size:20px;font-weight:700;color:#E8EAF0;'>{cur_data['living_score']}/100</div>"
        f"<div style='font-size:11px;color:{chobuma_clr};margin-top:4px;'>{chobuma_icon}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    sent = cur_data["sentiment_score"]
    sent_cls = "metric-ok" if sent > 0 else "metric-bad"
    m6.markdown(
        f"<div class='card' style='margin-bottom:0;padding:14px 18px;'>"
        f"<div class='metric-label'>Cortex 뉴스 심리</div>"
        f"<div class='metric-value {sent_cls}'>{sent:+.1f}pt</div>"
        f"<div style='font-size:11px;color:#445566;margin-top:4px;'>스케일 −5 ~ +5</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── ROW 2: PIR Band Chart + Spatial Risk ─────────────────────────────────────
col_temporal, col_spatial = st.columns([3, 2])

with col_temporal:
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Temporal Band — PIR 60개월 시계열</div>", unsafe_allow_html=True)
    st.plotly_chart(build_pir_band_chart(cur_data), use_container_width=True, config={"displayModeBar": False})
    idx = cur_data["pir_relative_index"]
    idx_clr = MINT if idx < 0.85 else (RED_NEO if idx > 1.15 else YELLOW_NEO)
    st.markdown(
        f"<div style='font-size:12px;color:#445566;'>"
        f"현재 PIR 상대 지수: <span style='color:{idx_clr};font-weight:700;'>{idx:.3f}</span> &nbsp;|&nbsp;"
        f"<span style='color:{idx_clr};'>{cur_data['pir_band_label']}</span>"
        f" &nbsp; (<span style='color:{MINT if idx < 0.85 else (RED_NEO if idx > 1.15 else YELLOW_NEO)};'>"
        f"{'+15pt' if idx < 0.85 else ('-10pt' if idx > 1.15 else '±0pt')}</span> 조정)"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

with col_spatial:
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>Spatial Risk — 인접구 공급 신호</div>", unsafe_allow_html=True)

    spill = cur_data["spillover_detail"]
    own_score = spill["own_score"]
    own_icon  = signal_icon(own_score)

    st.markdown(
        f"<div style='margin-bottom:12px;'>"
        f"<div class='metric-label'>본 구 ({spill['own_sgg']})</div>"
        f"<div style='font-size:28px;font-weight:700;'>"
        f"{own_icon} <span style='color:#E8EAF0;'>{own_score:.1f}pt</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    if spill.get("adjacent_sggs"):
        st.markdown("<div class='metric-label'>인접 구 Spillover (30%)</div>", unsafe_allow_html=True)
        sig_html = "<div class='signal-row'>"
        for adj_sgg, adj_score in spill.get("adjacent_scores", {}).items():
            icon = signal_icon(adj_score)
            sig_html += (
                f"<div class='signal' title='{adj_sgg}'>"
                f"<span>{icon}</span>{adj_sgg}<br>"
                f"<b style='color:#E8EAF0;'>{adj_score:.0f}pt</b>"
                f"</div>"
            )
        sig_html += "</div>"
        st.markdown(sig_html, unsafe_allow_html=True)

        final = spill.get("final_score", own_score)
        adj_avg = spill.get("adjacent_avg", own_score)
        st.markdown(
            f"<div style='margin-top:14px;padding:10px 14px;"
            f"background:#0A1020;border-radius:8px;border-left:3px solid {MINT};'>"
            f"<span style='font-size:11px;color:#445566;'>최종 공급 점수 (Own 70% + Adj 30%)</span><br>"
            f"<span style='font-size:20px;font-weight:700;color:{MINT};'>{final:.1f}pt</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ── ROW 3: COMPARISON SIMULATOR ──────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<div style='font-size:20px;font-weight:800;color:#E8EAF0;margin-bottom:16px;'>"
    f"상급지 갈아타기 시뮬레이터</div>",
    unsafe_allow_html=True,
)

col_cur, col_arrow, col_tgt = st.columns([5, 1, 5])

def render_danji_card(data: dict, label: str):
    s = data["s_alpha"]
    cls = score_class(s)
    jok = data["jeonse_safety_ok"]
    pok = data["pir_undervalue_ok"]
    badge = badge_class(data["confidence_label"])

    jok_style = f"style='color:{MINT};'" if jok else f"style='color:{RED_NEO};'"
    pok_style = f"style='color:{MINT};'" if pok else ""
    chobuma_text = f"<b style='color:{MINT};'>초품아 ×1.5</b>" if data['is_chobuma'] else "— 일반"

    st.markdown(
        f"<div class='card'>"
        f"<div class='section-header'>{label}</div>"
        f"<div style='font-size:18px;font-weight:700;color:#E8EAF0;margin-bottom:4px;'>{data['danji_name']}</div>"
        f"<div style='font-size:12px;color:#445566;margin-bottom:16px;'>{data['sgg']} · {data['emd']}</div>"
        f"<div style='display:flex;align-items:baseline;gap:12px;margin-bottom:8px;'>"
        f"  <span class='score-value {cls}' style='font-size:48px;'>{s}</span>"
        f"  <span style='font-size:16px;color:#445566;'>pt</span>"
        f"  <span class='badge {badge}'>{data['confidence_label']} {data['confidence_pct']:.0f}%</span>"
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

with col_cur:
    render_danji_card(cur_data, "현재 단지")

with col_arrow:
    st.markdown(
        "<div style='display:flex;align-items:center;justify-content:center;"
        "height:100%;padding-top:80px;font-size:36px;'>→</div>",
        unsafe_allow_html=True,
    )

with col_tgt:
    render_danji_card(tgt_data, "목표 단지")

# 레이더 차트
col_radar, col_delta = st.columns([3, 2])
with col_radar:
    st.markdown(f"<div class='card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-header'>전략 비교 레이더</div>", unsafe_allow_html=True)
    st.plotly_chart(build_comparison_chart(cur_data, tgt_data), use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

with col_delta:
    delta = tgt_data["s_alpha"] - cur_data["s_alpha"]
    delta_pct = round(delta / max(cur_data["s_alpha"], 1) * 100, 1)

    st.markdown(
        f"<div class='card' style='height:300px;display:flex;flex-direction:column;justify-content:center;'>"
        f"<div class='section-header'>점수 Delta</div>"
        f"<div style='font-size:60px;font-weight:900;"
        f"color:{MINT if delta > 0 else RED_NEO};"
        f"text-shadow:0 0 20px {MINT if delta > 0 else RED_NEO}88;'>"
        f"{delta:+d}pt</div>"
        f"<div style='font-size:20px;font-weight:700;color:{MINT if delta > 0 else RED_NEO};margin-top:4px;'>"
        f"({delta_pct:+.1f}%)</div>"
        f"<hr style='border-color:{BORDER};margin:16px 0;'>"
        f"<div style='font-size:13px;color:#445566;line-height:1.8;'>"
        f"현재: <b style='color:#E8EAF0;'>{cur_data['s_alpha']}pt</b><br>"
        f"목표: <b style='color:#E8EAF0;'>{tgt_data['s_alpha']}pt</b><br>"
        f"Alpha-Trigger: <b style='color:{MINT};'>{'달성' if (delta >= ALPHA_TRIGGER_DELTA and tgt_data['s_alpha'] >= ALPHA_TRIGGER_MIN) else '미달성'}</b>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

# ── ALPHA-TRIGGER ─────────────────────────────────────────────────────────────
if delta >= ALPHA_TRIGGER_DELTA and tgt_data["s_alpha"] >= ALPHA_TRIGGER_MIN:
    st.balloons()
    st.markdown(
        f"<div class='alpha-banner'>"
        f"<div class='alpha-title'>[STRATEGY CONFIRMED]</div>"
        f"<div style='font-size:26px;font-weight:800;color:{GOLD};text-shadow:0 0 20px {GOLD};'>"
        f"자산 가치 점프 구간! 상급지 이동을 권고합니다."
        f"</div>"
        f"<div style='margin-top:20px;'>"
        f"<span style='font-size:14px;color:#886600;'>점수 상승 폭</span><br>"
        f"<span class='alpha-delta'>{delta:+d}pt &nbsp; ({delta_pct:+.1f}%)</span>"
        f"</div>"
        f"<div style='margin-top:16px;font-size:13px;color:#664400;line-height:1.8;'>"
        f"조건 1: 목표 점수 {tgt_data['s_alpha']}pt ≥ {ALPHA_TRIGGER_MIN}pt<br>"
        f"조건 2: Delta {delta:+d}pt ≥ {ALPHA_TRIGGER_DELTA}pt<br>"
        f"{cur_data['danji_name']} → {tgt_data['danji_name']} 이동 시 "
        f"예상 자산 가치 상승 레버리지 확보"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f"<div class='card' style='text-align:center;padding:20px;border-color:{BORDER};'>"
        f"<span style='color:#445566;font-size:13px;'>"
        f"Alpha-Trigger 미달성 &nbsp;|&nbsp; 조건: 목표 ≥ {ALPHA_TRIGGER_MIN}pt & Δ ≥ {ALPHA_TRIGGER_DELTA}pt"
        f"</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f"<div style='text-align:center;color:#2A3445;font-size:11px;padding:16px;'>"
    f"Richgo-Cortex AI Assistant · Model C+ · Plan Freeze 2026-04-01 · "
    f"Powered by Snowflake Cortex AI &amp; Richgo 46만 행 실측 데이터"
    f"</div>",
    unsafe_allow_html=True,
)
