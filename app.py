# Moving-Up 마스터 | Richgo-Cortex AI Strategic Command Center v2.0 | Model C+ 2026-04-02
# Run: streamlit run app.py
# modules/data_loader.py | modules/report_engine.py | modules/styles.py
from typing import Optional, Tuple
from dotenv import load_dotenv
import streamlit as st

from modules.data_loader   import get_engine, get_all_danji_list, render_cascading_selector
from modules.report_engine import (
    build_ai_report, build_delta, generate_detailed_logic,
    compute_financial_feasibility, compute_personalized_score,
    ALPHA_TRIGGER_DELTA, ALPHA_TRIGGER_MIN,
)
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
                        # Cortex 재무·개인화 결과 초기화 (단지 변경 시 재산출)
                        st.session_state.pop("financial_result", None)
                        st.session_state.pop("personal_result",  None)
                        st.success("설정 완료")
                except Exception:
                    st.info(
                        "해당 단지의 실거래 데이터 결측이 감지되어, "
                        "인근 구/동 평균 데이터로 정밀 보정 중입니다. (일시 분석 제한)"
                    )

        # ── 엔진 세션 저장 (대시보드 Cortex 호출용) ──────────────────────────
        if engine:
            st.session_state["_engine"] = engine

        st.markdown("---")

        # ── MISSION 1: 보유 현금 입력 ────────────────────────────────────────
        st.markdown(
            f"<div class='section-header' style='margin-top:4px;' "
            f"title='갈아타기 실행을 위한 보유 현금(억 단위)을 입력하세요.'>"
            f"💰 보유 현금 (억 단위)</div>",
            unsafe_allow_html=True,
        )
        cash_eok = st.number_input(
            label="보유 현금",
            min_value=0.0, max_value=100.0, step=0.5,
            value=float(st.session_state.get("cash_eok", 5.0)),
            format="%.1f",
            label_visibility="collapsed",
        )
        st.session_state["cash_eok"] = cash_eok
        st.markdown(
            f"<div style='font-size:11px;color:#445566;margin-top:-8px;margin-bottom:8px;'>"
            f"강남3구·용산 LTV 50% / 그 외 LTV 70% 자동 적용</div>",
            unsafe_allow_html=True,
        )

        # ── MISSION 2: 라이프스타일 별점 가중치 ──────────────────────────────
        st.markdown(
            f"<div class='section-header' style='margin-top:8px;' "
            f"title='각 항목이 갈아타기 결정에 얼마나 중요한가요? (1=낮음 ~ 5=필수)'>"
            f"⭐ 나만의 주거 가치 우선순위</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:11px;color:#445566;margin:-6px 0 8px 0;'>"
            "이 요소가 갈아타기 결정에 얼마나 중요한가요?</div>",
            unsafe_allow_html=True,
        )
        _STAR_OPTIONS = [1, 2, 3, 4, 5]
        _STAR_LABELS  = {1: "1 낮음", 2: "2", 3: "3 보통", 4: "4", 5: "5 필수"}
        prev_weights  = st.session_state.get("lifestyle_weights", {})

        w_hak   = st.select_slider(
            "📚 학군",   options=_STAR_OPTIONS,
            format_func=lambda x: _STAR_LABELS[x],
            value=prev_weights.get("학군",   3),
        )
        w_rail  = st.select_slider(
            "🚇 역세권", options=_STAR_OPTIONS,
            format_func=lambda x: _STAR_LABELS[x],
            value=prev_weights.get("역세권", 3),
        )
        w_shop  = st.select_slider(
            "🛒 슬세권", options=_STAR_OPTIONS,
            format_func=lambda x: _STAR_LABELS[x],
            value=prev_weights.get("슬세권", 3),
        )
        w_green = st.select_slider(
            "🌿 쾌적성", options=_STAR_OPTIONS,
            format_func=lambda x: _STAR_LABELS[x],
            value=prev_weights.get("쾌적성", 3),
        )
        lifestyle_weights = {"학군": w_hak, "역세권": w_rail, "슬세권": w_shop, "쾌적성": w_green}
        st.session_state["lifestyle_weights"] = lifestyle_weights

        # 정규화된 비중 미리보기
        _total_w = sum(lifestyle_weights.values()) or 1
        _norm_preview = " · ".join(
            f"<b style='color:#7EC8E3;'>{k}</b> {v/_total_w*100:.0f}%"
            for k, v in lifestyle_weights.items()
        )
        st.markdown(
            f"<div style='font-size:11px;color:#445566;margin-top:4px;line-height:1.8;'>"
            f"반영 비중 — {_norm_preview}</div>",
            unsafe_allow_html=True,
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
    # ── Layer 1: 상시 노출 요약 ───────────────────────────────────────────────
    st.markdown(
        f"<div style='padding:22px;border-left:6px solid {report['color']};"
        f"background:#11141A;margin-bottom:8px;border-radius:6px;"
        f"box-shadow:0 4px 12px rgba(0,0,0,0.5);'>"
        f"<div style='font-size:18px;font-weight:800;color:{report['color']};margin-bottom:8px;'>"
        f"[AI 분석 결론]</div>"
        f"<div style='font-size:16px;color:#E8EAF0;line-height:1.6;letter-spacing:-0.3px;'>"
        f"{report['message']}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    # ── Layer 2: 심층 분석 Expander ───────────────────────────────────────────
    with st.expander("🔍 AI 마스터의 5대 핵심 근거 및 데이터 정밀 진단"):
        logic_items = generate_detailed_logic(cur_data, tgt_data)
        for i, item in enumerate(logic_items):
            icon     = item["icon"]
            emoji    = item["emoji"]
            title    = item["title"]
            subtitle = item["subtitle"]
            text     = item["text"]
            color    = item["color"]
            separator = "" if i == len(logic_items) - 1 else \
                f"<hr style='border-color:#1E2329;margin:0;'/>"
            st.markdown(
                f"<div style='padding:16px 20px;background:#0D1117;"
                f"border-left:4px solid {color};border-radius:0 6px 6px 0;"
                f"margin-bottom:4px;'>"
                f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:8px;'>"
                f"  <span style='font-size:20px;'>{emoji}</span>"
                f"  <div>"
                f"    <span style='font-size:14px;font-weight:800;color:{color};'>"
                f"    {icon} {title}</span>"
                f"    <span style='font-size:11px;color:#445566;margin-left:8px;font-family:monospace;'>"
                f"    {subtitle}</span>"
                f"  </div>"
                f"</div>"
                f"<div style='font-size:13px;color:#C8D0E0;line-height:1.7;padding-left:30px;'>"
                f"{text}</div>"
                f"</div>"
                f"{separator}",
                unsafe_allow_html=True,
            )
    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

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
            config={
                "displayModeBar": True,
                "modeBarButtonsToRemove": ["select2d", "lasso2d", "toggleSpikelines"],
                "displaylogo": False,
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with col_delta_ui:
        move_dir   = "상향 이동 ▲" if d["delta"] >= 0 else "하향 이동 ▼"
        move_color = d["delta_color"]
        st.markdown(
            f"<div class='card' style='display:flex;flex-direction:column;justify-content:center;"
            f"min-height:340px;'>"
            f"<div class='section-header'>갈아타기 가치 (이동 시 이득)</div>"
            f"<div style='font-size:56px;font-weight:900;color:{move_color};{d['delta_glow']}'>"
            f"{d['delta']:+d}pt</div>"
            f"<div style='display:flex;align-items:center;gap:10px;margin-top:4px;'>"
            f"  <span style='font-size:18px;font-weight:700;color:{move_color};'>({d['delta_pct']:+.1f}%)</span>"
            f"  <span style='background:{move_color}22;color:{move_color};border:1px solid {move_color}55;"
            f"  border-radius:12px;padding:2px 10px;font-size:12px;font-weight:700;'>{move_dir}</span>"
            f"</div>"
            f"<hr style='border-color:{BORDER};margin:14px 0;'>"
            f"<div style='font-size:13px;color:#445566;line-height:1.9;'>"
            f"현재 단지: <b style='color:#667788;'>{cur_data['s_alpha']}pt</b><br>"
            f"목표 단지: <b style='color:#E8EAF0;'>{tgt_data['s_alpha']}pt</b><br>"
            f"<span style='font-size:11px;color:#334455;'>초격차 갈아타기 성립 조건:</span><br>"
            f"{d['trigger_text']}</div></div>",
            unsafe_allow_html=True,
        )

    # ════════════════════════════════════════════════════════════════════════════
    # MISSION 1: 재무 실행 가능성 (Financial Feasibility)
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div style='font-size:20px;font-weight:800;color:#E8EAF0;margin:28px 0 12px 0;'>"
        f"재무 실행 가능성 분석</div>",
        unsafe_allow_html=True,
    )

    cash_eok       = float(st.session_state.get("cash_eok", 5.0))
    engine_obj     = st.session_state.get("_engine")
    sf_client      = engine_obj._client if engine_obj else None

    col_fin_btn, col_fin_hint = st.columns([2, 5])
    with col_fin_btn:
        run_financial = st.button(
            "Cortex AI 재무 판독 실행",
            key="btn_financial",
            use_container_width=True,
        )
    with col_fin_hint:
        st.markdown(
            f"<div style='padding-top:10px;font-size:12px;color:#445566;'>"
            f"보유 현금 <b style='color:#E8EAF0;'>{cash_eok:.1f}억</b> 기준 "
            f"— 사이드바에서 현금을 수정 후 재실행하세요.</div>",
            unsafe_allow_html=True,
        )

    if run_financial:
        with st.spinner("Cortex AI가 재무 실행 가능성을 판독 중입니다..."):
            fin = compute_financial_feasibility(cash_eok, tgt_data, sf_client)
            st.session_state["financial_result"] = fin

    fin = st.session_state.get("financial_result")
    if fin:
        vc   = fin["verdict_color"]
        vl   = fin["verdict_label"]
        col_fin1, col_fin2 = st.columns([1, 2])
        with col_fin1:
            st.markdown(
                f"<div class='card' style='border-color:{vc}44;text-align:center;'>"
                f"<div style='font-size:12px;color:#445566;margin-bottom:6px;'>재무 판정 배지</div>"
                f"<div style='font-size:26px;font-weight:900;color:{vc};"
                f"text-shadow:0 0 16px {vc};margin-bottom:10px;'>{vl}</div>"
                f"<div style='font-size:11px;color:#445566;line-height:1.8;'>"
                f"매매가: <b style='color:#E8EAF0;'>{fin['price_eok']:.1f}억</b><br>"
                f"전세가: <b style='color:#667788;'>{fin['jeonse_eok']:.1f}억</b><br>"
                f"실투자금(Gap): <b style='color:{vc};'>{fin['gap_eok']:.1f}억</b><br>"
                f"LTV {int(fin['ltv_rate']*100)}% 대출 한도: <b>{fin['loan_eok']:.1f}억</b><br>"
                f"총 가용 자금: <b style='color:#E8EAF0;'>{fin['total_eok']:.1f}억</b><br>"
                f"여유/부족: <b style='color:{vc};'>{fin['surplus_eok']:+.1f}억</b>"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with col_fin2:
            # Cortex AI 3줄 분석 텍스트
            lines = [l.strip() for l in fin["cortex_text"].split("\n") if l.strip()]
            lines_html = "".join(
                f"<div style='margin-bottom:8px;padding:10px 14px;"
                f"background:#0D1117;border-left:3px solid {vc}44;"
                f"border-radius:0 6px 6px 0;font-size:13px;color:#C8D0E0;'>"
                f"{line}</div>"
                for line in lines
            )
            st.markdown(
                f"<div class='card' style='border-color:{vc}33;'>"
                f"<div style='font-size:13px;font-weight:700;color:{vc};"
                f"margin-bottom:12px;'>"
                f"Snowflake Cortex AI 재무 판독 결과</div>"
                f"{lines_html}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"<div class='card' style='text-align:center;padding:20px;"
            f"border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"위의 버튼을 눌러 Cortex AI 재무 판독을 실행하세요.</span></div>",
            unsafe_allow_html=True,
        )

    # ════════════════════════════════════════════════════════════════════════════
    # MISSION 2: 나만의 맞춤 가치 (Personalized Value Score)
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div style='font-size:20px;font-weight:800;color:#E8EAF0;margin:28px 0 12px 0;'>"
        f"나만의 맞춤 가치 점수</div>",
        unsafe_allow_html=True,
    )

    lifestyle_weights = st.session_state.get("lifestyle_weights", {"학군": 3, "역세권": 3, "슬세권": 3, "쾌적성": 3})
    col_per_btn, col_per_hint = st.columns([2, 5])
    with col_per_btn:
        run_personal = st.button(
            "Cortex AI 맞춤 점수 산출",
            key="btn_personal",
            use_container_width=True,
        )
    with col_per_hint:
        _tw = sum(lifestyle_weights.values()) or 1
        _wt_preview = " · ".join(
            f"<b style='color:{MINT};'>{k}</b> {v/_tw*100:.0f}%"
            for k, v in lifestyle_weights.items()
        )
        st.markdown(
            f"<div style='padding-top:10px;font-size:12px;color:#445566;'>"
            f"가중 반영 비중 — {_wt_preview}</div>",
            unsafe_allow_html=True,
        )

    if run_personal:
        with st.spinner("Cortex AI가 맞춤 주거 점수를 산출 중입니다..."):
            per = compute_personalized_score(lifestyle_weights, tgt_data, sf_client)
            st.session_state["personal_result"] = per

    per = st.session_state.get("personal_result")
    if per:
        pscore = per["personal_score"]
        pcolor = MINT if pscore >= 75 else (YELLOW_NEO if pscore >= 50 else RED_NEO)
        col_per1, col_per2 = st.columns([1, 2])
        with col_per1:
            # 가중치 태그 렌더링
            _weights_display = per.get("weights", {})
            _tw2 = sum(_weights_display.values()) or 1
            weight_tags = "".join(
                f"<span style='background:{MINT}22;color:{MINT};border:1px solid {MINT}44;"
                f"border-radius:10px;padding:2px 8px;font-size:11px;font-weight:700;"
                f"margin-right:4px;margin-bottom:4px;display:inline-block;'>"
                f"{'⭐'*v} {k} {v/_tw2*100:.0f}%</span>"
                for k, v in _weights_display.items()
            ) or f"<span style='color:#445566;font-size:11px;'>전체 기준</span>"
            st.markdown(
                f"<div class='card' style='border-color:{pcolor}44;text-align:center;'>"
                f"<div style='font-size:12px;color:#445566;margin-bottom:6px;'>"
                f"⭐ 가중합 맞춤 가치 점수</div>"
                f"<div class='score-value {score_class(pscore)}' "
                f"style='font-size:64px;color:{pcolor};"
                f"text-shadow:0 0 20px {pcolor};'>{pscore}</div>"
                f"<div style='font-size:11px;color:#445566;margin-top:8px;'>/100점 (Weighted Sum)</div>"
                f"<div style='margin-top:10px;line-height:2;'>{weight_tags}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_per2:
            exp_lines = [l.strip() for l in per["explanation"].split("\n") if l.strip()]
            exp_html = "".join(
                f"<div style='margin-bottom:8px;padding:10px 14px;"
                f"background:#0D1117;border-left:3px solid {pcolor}44;"
                f"border-radius:0 6px 6px 0;font-size:13px;color:#C8D0E0;'>"
                f"{line}</div>"
                for line in exp_lines
            )
            st.markdown(
                f"<div class='card' style='border-color:{pcolor}33;'>"
                f"<div style='font-size:13px;font-weight:700;color:{pcolor};"
                f"margin-bottom:12px;'>"
                f"Snowflake Cortex AI 가중합 분석 근거</div>"
                f"{exp_html}</div>",
                unsafe_allow_html=True,
            )

        # ── MISSION 3: 취향 정합성 코멘트 ─────────────────────────────────
        matching_comment = per.get("matching_comment", "")
        if matching_comment:
            has_warning = "⚠️" in matching_comment or "경고" in matching_comment or "부족" in matching_comment
            mc_color = YELLOW_NEO if has_warning else MINT
            mc_lines = [l.strip() for l in matching_comment.split("\n") if l.strip()]
            mc_html = "".join(
                f"<div style='margin-bottom:8px;padding:10px 14px;"
                f"background:#0D1117;border-left:3px solid {mc_color}55;"
                f"border-radius:0 6px 6px 0;font-size:13px;color:#C8D0E0;'>"
                f"{line}</div>"
                for line in mc_lines
            )
            st.markdown(
                f"<div class='card' style='border-color:{mc_color}44;margin-top:12px;'>"
                f"<div style='font-size:13px;font-weight:700;color:{mc_color};margin-bottom:12px;'>"
                f"🔍 Cortex AI 취향 정합성(Matching) 분석</div>"
                f"{mc_html}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"<div class='card' style='text-align:center;padding:20px;"
            f"border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"위의 버튼을 눌러 Cortex AI 맞춤 점수를 산출하세요.</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)

    # 초격차 갈아타기 성립 배너
    if d["is_trigger"]:
        st.markdown(
            f"<div class='alpha-banner'>"
            f"<div class='alpha-title'>✅ 초격차 갈아타기 성립 조건 달성</div>"
            f"<div style='font-size:26px;font-weight:800;color:{GOLD};text-shadow:0 0 20px {GOLD};'>"
            f"자산 가치 점프 구간! 상급지 이동을 권고합니다.</div>"
            f"<div style='margin-top:20px;'>"
            f"<span style='font-size:14px;color:#886600;'>갈아타기 가치 (이동 시 이득)</span><br>"
            f"<span class='alpha-delta'>{d['delta']:+d}pt &nbsp; ({d['delta_pct']:+.1f}%)</span></div>"
            f"<div style='margin-top:16px;font-size:13px;color:#664400;line-height:1.8;'>"
            f"조건 1: 목표 점수 {tgt_data['s_alpha']}pt ≥ {ALPHA_TRIGGER_MIN}pt ✅<br>"
            f"조건 2: 이동 시 이득 {d['delta']:+d}pt ≥ {ALPHA_TRIGGER_DELTA}pt ✅<br>"
            f"{cur_data['danji_name']} → {tgt_data['danji_name']} 이동 시 예상 자산 가치 상승 레버리지 확보"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='card' style='text-align:center;padding:20px;border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"초격차 갈아타기 성립 조건 미달 &nbsp;|&nbsp; 조건: 목표 ≥ {ALPHA_TRIGGER_MIN}pt & 이동 이득 ≥ {ALPHA_TRIGGER_DELTA}pt"
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
    st.markdown(
        """
<div style='background:linear-gradient(135deg,#0D1B2A 0%,#112233 100%);
            border:1px solid #1E3A5F;border-radius:12px;padding:28px 32px;
            max-width:640px;margin:40px auto;'>
  <div style='font-size:18px;font-weight:700;color:#E0F0FF;letter-spacing:0.5px;margin-bottom:20px;'>
    🧭 Cortex AI 지능형 부동산 비서 — 시작 가이드
  </div>
  <div style='display:flex;flex-direction:column;gap:14px;'>
    <div style='display:flex;align-items:flex-start;gap:14px;'>
      <div style='font-size:22px;line-height:1;'>🏠</div>
      <div>
        <div style='color:#7EC8E3;font-size:13px;font-weight:600;margin-bottom:2px;'>1단계 — 자금 계획의 시작</div>
        <div style='color:#B0C8D8;font-size:13px;line-height:1.6;'>
          좌측 메뉴에서 <strong style='color:#E0F0FF;'>현재 거주 단지</strong>와
          <strong style='color:#E0F0FF;'>보유 현금(억 단위)</strong>을 입력하세요.
        </div>
      </div>
    </div>
    <div style='display:flex;align-items:flex-start;gap:14px;'>
      <div style='font-size:22px;line-height:1;'>🎯</div>
      <div>
        <div style='color:#7EC8E3;font-size:13px;font-weight:600;margin-bottom:2px;'>2단계 — 목표 설정</div>
        <div style='color:#B0C8D8;font-size:13px;line-height:1.6;'>
          상급지 이동을 희망하는 <strong style='color:#E0F0FF;'>목표 단지</strong>를 선택하세요.
        </div>
      </div>
    </div>
    <div style='display:flex;align-items:flex-start;gap:14px;'>
      <div style='font-size:22px;line-height:1;'>✨</div>
      <div>
        <div style='color:#7EC8E3;font-size:13px;font-weight:600;margin-bottom:2px;'>3단계 — 라이프스타일 맞춤화</div>
        <div style='color:#B0C8D8;font-size:13px;line-height:1.6;'>
          본인의 주거 가치 우선순위
          (<strong style='color:#E0F0FF;'>학군·역세권·슬세권·쾌적성</strong>)를 체크하세요.
        </div>
      </div>
    </div>
    <div style='display:flex;align-items:flex-start;gap:14px;'>
      <div style='font-size:22px;line-height:1;'>📊</div>
      <div>
        <div style='color:#7EC8E3;font-size:13px;font-weight:600;margin-bottom:2px;'>4단계 — AI 리포트 확인</div>
        <div style='color:#B0C8D8;font-size:13px;line-height:1.6;'>
          Cortex AI가 분석한 <strong style='color:#E0F0FF;'>재무 안정도</strong>와
          <strong style='color:#E0F0FF;'>맞춤 가치 리포트</strong>를 확인하세요.
        </div>
      </div>
    </div>
  </div>
  <div style='margin-top:20px;padding-top:16px;border-top:1px solid #1E3A5F;
              font-size:11px;color:#4A6A8A;text-align:center;line-height:1.6;'>
    모든 분석은 Snowflake Cortex AI의 실시간 추론을 통해 생성됩니다.<br>
    Model C+ · Plan Freeze 2026-04-01 · Alpha-Trigger ≥ 80pt
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )
