# Moving-Up 마스터 | Richgo-Cortex AI Strategic Command Center v2.0 | Model C+ 2026-04-02
# Run: streamlit run app.py
# modules/data_loader.py | modules/report_engine.py | modules/styles.py
from typing import Optional, Tuple
from dotenv import load_dotenv
import streamlit as st

from modules.data_loader   import get_engine, get_all_danji_list, render_cascading_selector
from modules.report_engine import build_ai_report, build_delta, ALPHA_TRIGGER_DELTA, ALPHA_TRIGGER_MIN
from modules.styles import (
    inject_css,
    build_pir_band_chart,
    build_comparison_chart,
    render_danji_card,
    render_key_metrics,
    render_spatial_risk,
    score_class,
    MINT, GOLD, RED_NEO, YELLOW_NEO, BORDER,
)

load_dotenv()

# ── Page Config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Moving-Up 마스터 | AI 부동산 비서",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


# ── Sidebar ────────────────────────────────────────────────────────────────────
def render_sidebar() -> Tuple[Optional[dict], Optional[dict]]:
    """사이드바 렌더링 — 단지 선택 UI. Returns (cur_result, tgt_result)."""
    with st.sidebar:
        st.markdown(
            f"<div style='color:{MINT};font-size:22px;font-weight:800;'>Richgo-Cortex AI</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='color:#445566;font-size:12px;margin-bottom:16px;'>"
            "Strategic Command Center v2.0</div>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        engine = get_engine()
        conn_label = (
            f"<span style='color:{MINT};font-size:12px;'>● LIVE — Snowflake 연결됨</span>"
            if engine else
            f"<span style='color:{YELLOW_NEO};font-size:12px;'>● DEMO — 연결 없음</span>"
        )
        st.markdown(conn_label, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown(
            "<div class='section-header' "
            "title='지난 5년 동안의 평균을 바탕으로 현재 가격 수준을 진단합니다.'>"
            "과거 5년 가격 위치 (회색 밴드는 평균)</div>",
            unsafe_allow_html=True,
        )

        danji_list = get_all_danji_list(engine)
        if not danji_list:
            st.warning("데이터 동기화 대기 중... Snowflake 연결을 확인하세요.")
            st.stop()

        with st.expander("현재 단지 설정", expanded=True):
            selected_current = render_cascading_selector(danji_list, "cur")

        st.markdown(
            f"<div style='height:4px;background:linear-gradient(90deg,{MINT}44,{MINT});border-radius:2px;margin:4px 0 2px 0;'></div>",
            unsafe_allow_html=True,
        )
        with st.expander("🎯 목표 단지 설정", expanded=False):
            selected_target = render_cascading_selector(danji_list, "tgt")

        if selected_current and selected_target:
            is_same = selected_current["DANJI_ID"] == selected_target["DANJI_ID"]
        else:
            is_same = True

        if is_same:
            st.warning("현재 단지와 목표 단지가 동일합니다. 다른 단지를 선택하십시오.")

        if st.button("설정 완료", use_container_width=True, disabled=is_same):
            with st.spinner("AI가 실거래 데이터를 정밀 분석 중입니다..."):
                try:
                    cur_res = engine.analyze(selected_current["DANJI_ID"])
                    tgt_res = engine.analyze(selected_target["DANJI_ID"])
                    if cur_res is None or tgt_res is None:
                        st.info(
                            "해당 단지의 실거래 데이터 결측이 감지되어, "
                            "인근 구/동 평균 데이터로 정밀 보정 중입니다. (일시 분석 제한)"
                        )
                    else:
                        st.session_state["cur_data"] = cur_res
                        st.session_state["tgt_data"] = tgt_res
                        st.success("설정 완료")
                except Exception:
                    st.info(
                        "해당 단지의 실거래 데이터 결측이 감지되어, "
                        "인근 구/동 평균 데이터로 정밀 보정 중입니다. (일시 분석 제한)"
                    )

        st.markdown("---")
        st.markdown(
            "<div style='color:#445566;font-size:11px;line-height:1.8;'>"
            "Model C+ | Plan Freeze 2026-04-01<br>"
            "Richgo × Snowflake Cortex AI<br>"
            f"<span style='color:{MINT}'>Alpha-Trigger ≥ 80pt Δ≥20</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    return st.session_state.get("cur_data"), st.session_state.get("tgt_data")


# ── Dashboard ──────────────────────────────────────────────────────────────────
def render_dashboard(cur_data: dict, tgt_data: dict) -> None:
    """메인 대시보드 전체 오케스트레이션."""

    # Header
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:16px;margin-bottom:4px;'>"
        f"<span style='font-size:26px;font-weight:800;color:#E8EAF0;'>Moving-Up 마스터</span>"
        f"<span style='font-size:13px;color:#445566;font-family:monospace;'>AI REAL ESTATE ASSISTANT</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:12px;color:#445566;margin-bottom:8px;'>"
        f"{tgt_data['analysis_date']} &nbsp;|&nbsp; "
        f"현재: <span style='color:#667788;'>{cur_data['danji_name']}</span>"
        f" &nbsp;→&nbsp; 목표: <b style='color:{MINT};'>{tgt_data['danji_name']}</b>"
        f" &nbsp;|&nbsp; <span style='color:{MINT}'>Richgo-Cortex AI Model C+</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    # 🎯 목표 단지 분석 리포트 타이틀 배너
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:16px;"
        f"background:linear-gradient(135deg,#0A1A10 0%,#0D1F18 100%);"
        f"border:1px solid {MINT}44;border-left:4px solid {MINT};"
        f"border-radius:8px;padding:14px 20px;margin-bottom:20px;'>"
        f"<span style='font-size:22px;font-weight:900;color:{MINT};letter-spacing:-0.5px;'>"
        f"🎯 목표 단지 분석 리포트</span>"
        f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}55;"
        f"border-radius:20px;padding:4px 14px;font-size:13px;font-weight:700;'>"
        f"목표: {tgt_data['danji_name']}</span>"
        f"<span style='font-size:12px;color:#445566;margin-left:auto;'>"
        f"{tgt_data['sgg']} · {tgt_data['emd']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ROW 1: Score Gauge + Key Metrics
    col_gauge, col_metrics = st.columns([1, 2])

    with col_gauge:
        trigger_html = (
            f"<div style='color:{MINT};font-size:12px;font-weight:700;margin-top:8px;'>즉시 실행 트리거 발동</div>"
            if tgt_data["execution_trigger"] else ""
        )
        st.markdown(
            f"<div class='card' style='height:100%;display:flex;flex-direction:column;justify-content:center;"
            f"border-color:{MINT}44;'>"
            f"<div style='display:flex;align-items:center;gap:8px;margin-bottom:4px;'>"
            f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}55;"
            f"border-radius:12px;padding:2px 10px;font-size:11px;font-weight:700;'>목표 단지</span>"
            f"<span style='font-size:12px;color:#445566;font-weight:600;'>{tgt_data['danji_name']}</span>"
            f"</div>"
            f"<div class='section-header' style='margin-top:6px;' title='여러 지표를 종합한 상급지 이동 타당도 점수입니다.'>"
            f"목표 단지 종합 가치 점수</div>"
            f"<div class='score-value {score_class(tgt_data['s_alpha'])}' id='main-score'>{tgt_data['s_alpha']}</div>"
            f"<div style='color:#445566;font-size:11px;margin-top:12px;'>"
            f"Band 보정 전: {tgt_data['s_alpha_before_band']}pt &nbsp;"
            f"PIR 조정: {tgt_data['pir_band_adjustment']:+.0f}pt"
            f"</div>{trigger_html}</div>"
            f"<iframe srcdoc=\"<script>"
            f"const target={tgt_data['s_alpha']};let current=0;"
            f"const stepTime=Math.max(10,Math.floor(1000/target));"
            f"const timer=setInterval(()={{current+=1;"
            f"window.parent.document.querySelectorAll('.score-value').forEach(el=>{{if(el.id==='main-score')el.innerText=current;}});"
            f"if(current>=target)clearInterval(timer);}},stepTime);</script>\""
            f" style=\"display:none;\"></iframe>",
            unsafe_allow_html=True,
        )

    with col_metrics:
        render_key_metrics(tgt_data)

    # AI Executive Summary
    st.markdown(
        "<div class='section-header' title='AI가 분석한 최종 권고 사항입니다.'>"
        "AI 마스터의 전략 제안 (Executive Summary)</div>",
        unsafe_allow_html=True,
    )
    report = build_ai_report(cur_data, tgt_data)
    st.markdown(
        f"<div style='padding:22px;border-left:6px solid {report['color']};"
        f"background:#11141A;margin-bottom:32px;border-radius:6px;"
        f"box-shadow:0 4px 12px rgba(0,0,0,0.5);'>"
        f"<div style='font-size:18px;font-weight:800;color:{report['color']};margin-bottom:8px;'>[AI 분석 결론]</div>"
        f"<div style='font-size:16px;color:#E8EAF0;line-height:1.6;letter-spacing:-0.3px;'>{report['message']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ROW 2: PIR Band + Spatial Risk
    col_temporal, col_spatial = st.columns([3, 2])

    with col_temporal:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='section-header'>"
            f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}44;"
            f"border-radius:10px;padding:1px 8px;font-size:10px;font-weight:700;margin-right:8px;'>목표 단지</span>"
            f"🎯 가격 수준 (Temporal Band — 과거 5년 대비)</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            build_pir_band_chart(tgt_data),
            use_container_width=True,
            config={
                "scrollZoom": True,
                "displayModeBar": True,
                "modeBarButtonsToRemove": [
                    "select2d", "lasso2d", "autoScale2d",
                    "hoverClosestCartesian", "hoverCompareCartesian",
                    "toggleSpikelines",
                ],
                "modeBarButtonsToAdd": ["pan2d"],
                "displaylogo": False,
                "toImageButtonOptions": {"filename": "pir_band_chart"},
            },
        )
        idx     = tgt_data["pir_relative_index"]
        idx_clr = MINT if idx < 0.85 else (RED_NEO if idx > 1.15 else YELLOW_NEO)
        adj_lbl = "+15pt" if idx < 0.85 else ("-10pt" if idx > 1.15 else "±0pt")
        st.markdown(
            f"<div style='font-size:12px;color:#445566;'>"
            f"역사적 평균 대비 목표 단지 가격의 저렴함: <span style='color:{idx_clr};font-weight:700;'>{idx:.3f}</span>"
            f" &nbsp;|&nbsp; <span style='color:{idx_clr};'>{tgt_data['pir_band_label']}</span>"
            f" (<span style='color:{idx_clr};'>{adj_lbl}</span> 조정)</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_spatial:
        render_spatial_risk(tgt_data)

    # ROW 3: Comparison Simulator
    st.markdown(
        "<br><div style='font-size:20px;font-weight:800;color:#E8EAF0;margin-bottom:16px;'>"
        "상급지 갈아타기 시뮬레이터</div>",
        unsafe_allow_html=True,
    )
    col_cur, col_arrow, col_tgt = st.columns([5, 1, 5])
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

    # Radar + Delta
    col_radar, col_delta_ui = st.columns([3, 2])
    delta_info = build_delta(cur_data, tgt_data)
    d = delta_info

    with col_radar:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-header'>전략 비교 레이더</div>", unsafe_allow_html=True)
        st.plotly_chart(
            build_comparison_chart(cur_data, tgt_data),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_delta_ui:
        st.markdown(
            f"<div class='card' style='height:300px;display:flex;flex-direction:column;justify-content:center;'>"
            f"<div class='section-header'>점수 Delta</div>"
            f"<div style='font-size:60px;font-weight:900;color:{d['delta_color']};{d['delta_glow']}'>{d['delta']:+d}pt</div>"
            f"<div style='font-size:20px;font-weight:700;color:{d['delta_color']};margin-top:4px;'>({d['delta_pct']:+.1f}%)</div>"
            f"<hr style='border-color:{BORDER};margin:16px 0;'>"
            f"<div style='font-size:13px;color:#445566;line-height:1.8;'>"
            f"현재: <b style='color:#E8EAF0;'>{cur_data['s_alpha']}pt</b><br>"
            f"목표: <b style='color:#E8EAF0;'>{tgt_data['s_alpha']}pt</b><br>"
            f"Alpha-Trigger: {d['trigger_text']}</div></div>",
            unsafe_allow_html=True,
        )

    # Alpha-Trigger Banner
    if d["is_trigger"]:
        st.markdown(
            f"<div class='alpha-banner'>"
            f"<div class='alpha-title'>[STRATEGY CONFIRMED]</div>"
            f"<div style='font-size:26px;font-weight:800;color:{GOLD};text-shadow:0 0 20px {GOLD};'>"
            f"자산 가치 점프 구간! 상급지 이동을 권고합니다.</div>"
            f"<div style='margin-top:20px;'>"
            f"<span style='font-size:14px;color:#886600;'>점수 상승 폭</span><br>"
            f"<span class='alpha-delta'>{d['delta']:+d}pt &nbsp; ({d['delta_pct']:+.1f}%)</span></div>"
            f"<div style='margin-top:16px;font-size:13px;color:#664400;line-height:1.8;'>"
            f"조건 1: 목표 점수 {tgt_data['s_alpha']}pt ≥ {ALPHA_TRIGGER_MIN}pt<br>"
            f"조건 2: Delta {d['delta']:+d}pt ≥ {ALPHA_TRIGGER_DELTA}pt<br>"
            f"{cur_data['danji_name']} → {tgt_data['danji_name']} 이동 시 예상 자산 가치 상승 레버리지 확보"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='card' style='text-align:center;padding:20px;border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"Alpha-Trigger 미달성 &nbsp;|&nbsp; 조건: 목표 ≥ {ALPHA_TRIGGER_MIN}pt & Δ ≥ {ALPHA_TRIGGER_DELTA}pt"
            f"</span></div>",
            unsafe_allow_html=True,
        )

    # Footer
    st.markdown(
        "<br><div style='text-align:center;color:#2A3445;font-size:11px;padding:16px;'>"
        "Richgo-Cortex AI Assistant · Model C+ · Plan Freeze 2026-04-01 · "
        "Powered by Snowflake Cortex AI &amp; Richgo 46만 행 실측 데이터"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Entry Point ────────────────────────────────────────────────────────────────

cur_data, tgt_data = render_sidebar()

if cur_data and tgt_data:
    render_dashboard(cur_data, tgt_data)
else:
    st.info(
        "**[지능형 부동산 비서 온보딩 가이드]**\n\n"
        "1. 좌측 메뉴에서 현재 거주 중인 단지를 선택하세요.\n"
        "2. 이동을 희망하는 목표 단지를 선택하세요.\n"
        "3. 분석 실행 후 하단의 AI 마스터 전략 리포트를 확인하세요."
    )
