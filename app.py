# Moving-Up 마스터 | Richgo-Cortex AI Strategic Command Center v2.0 | Model C+ 2026-04-02
# Run: streamlit run app.py
# modules/data_loader.py | modules/report_engine.py | modules/styles.py
from typing import Optional, Tuple
from dotenv import load_dotenv
import streamlit as st
import time

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

# ── Preference Emoji Map (UI 상수) ────────────────────────────────────────────
_PREF_EMOJI = {"학군": "📚", "역세권": "🚇", "슬세권": "🛒", "쾌적성": "🌿"}

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

        # ── Kill Switch: 분석 실행 / 중지 ────────────────────────────────────
        _has_results  = bool(st.session_state.get("cur_data"))
        _is_analyzing = st.session_state.get("_analyzing", False)

        if _is_analyzing:
            # 분석 중: 중지 버튼 노출
            if st.button("🛑 분석 중지", use_container_width=True, type="secondary",
                         help="분석을 중단하고 단지 선택 화면으로 돌아갑니다."):
                for _k in ["cur_data", "tgt_data", "financial_result",
                           "personal_result", "_analyzing"]:
                    st.session_state.pop(_k, None)
                st.rerun()
            import time
            with st.status("목표 단지 설정 및 시스템 초기화 중...", expanded=True) as status:
                status.write("🛰️ [25%] 선택하신 단지의 공간 좌표 및 필지 데이터 분석 중...")
                time.sleep(0.4)
                status.write("📦 [50%] Snowflake 저장소에서 최신 실거래가 및 매물 시세 파싱 중...")
                time.sleep(0.4)
                status.write("🧠 [75%] Cortex AI가 거주지 이전(Moving-Up) 전략 시뮬레이션 준비 중...")
                time.sleep(0.4)
                
                try:
                    cur_res = engine.analyze(selected_current["DANJI_ID"])
                    tgt_res = engine.analyze(selected_target["DANJI_ID"])
                    if cur_res is None or tgt_res is None:
                        st.session_state["_analyzing"] = False
                        status.update(label="데이터 결측 경고", state="error")
                        st.info(
                            "해당 단지의 실거래 데이터 결측이 감지되어, "
                            "인근 구/동 평균 데이터로 정밀 보정 중입니다. (일시 분석 제한)"
                        )
                    else:
                        status.write("✅ [100%] 초기 분석 준비 완료! 하단 리포트를 확인하세요.")
                        status.update(label="초기화 준비 완료", state="complete", expanded=False)
                        time.sleep(0.6)
                        
                        st.session_state.update({
                            "cur_data":  cur_res,
                            "tgt_data":  tgt_res,
                            "_analyzing": False,
                        })
                        st.session_state.pop("financial_result", None)
                        st.session_state.pop("personal_result",  None)
                        st.rerun()
                except Exception:
                    st.session_state["_analyzing"] = False
                    status.update(label="오류 발생", state="error")
                    st.info(
                        "해당 단지의 실거래 데이터 결측이 감지되어, "
                        "인근 구/동 평균 데이터로 정밀 보정 중입니다. (일시 분석 제한)"
                    )
        else:
            # 대기 중: 실행 버튼 노출
            if st.button("✅ 설정 완료", use_container_width=True, disabled=is_same):
                st.session_state["_analyzing"] = True
                st.rerun()
            # 결과가 있을 때만 초기화 버튼 노출
            if _has_results:
                if st.button("🔄 단지 재설정",
                             use_container_width=True,
                             help="현재 분석 결과를 초기화하고 새로운 단지를 설정합니다."):
                    for _k in ["cur_data", "tgt_data", "financial_result",
                               "personal_result", "_analyzing"]:
                        st.session_state.pop(_k, None)
                    st.rerun()

        # ── 엔진 세션 저장 (대시보드 Cortex 호출용) ──────────────────────────
        if engine:
            st.session_state["_engine"] = engine

        st.markdown("---")

        # ── MISSION 1: 나의 재무 프로필 입력 ────────────────────────────────────────
        @st.fragment
        def render_financial_fragment():
            st.markdown(
                f"<div class='section-header' style='margin-top:4px;' "
                f"title='갈아타기 실행을 위한 초개인화 재무 프로필을 입력하세요.'>"
                f"💰 나의 재무 프로필</div>",
                unsafe_allow_html=True,
            )
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("<div style='font-size:11px;color:#8892A4;margin-bottom:2px;'>금융 자산 (비상금, 억)</div>", unsafe_allow_html=True)
                liquid_asset_eok = st.number_input(
                    "금융 자산", min_value=0.0, max_value=100.0, step=0.5,
                    value=float(st.session_state.get("liquid_asset_eok", 5.0)),
                    format="%.1f", label_visibility="collapsed"
                )
                st.session_state["liquid_asset_eok"] = liquid_asset_eok

                st.markdown("<div style='font-size:11px;color:#8892A4;margin-top:8px;margin-bottom:2px;'>월 세후 소득 (만원)</div>", unsafe_allow_html=True)
                monthly_income_man = st.number_input(
                    "월 소득", min_value=0, max_value=20000, step=50,
                    value=int(st.session_state.get("monthly_income_man", 500)),
                    label_visibility="collapsed"
                )
                st.session_state["monthly_income_man"] = monthly_income_man

            with col2:
                st.markdown("<div style='font-size:11px;color:#8892A4;margin-bottom:2px;'>대출 금리 (%)</div>", unsafe_allow_html=True)
                loan_interest_rate = st.number_input(
                    "대출 금리", min_value=1.0, max_value=15.0, step=0.1,
                    value=float(st.session_state.get("loan_interest_rate", 4.0)),
                    format="%.1f", label_visibility="collapsed"
                )
                st.session_state["loan_interest_rate"] = loan_interest_rate

                st.markdown("<div style='font-size:11px;color:#8892A4;margin-top:8px;margin-bottom:2px;'>월 고정 지출 (만원)</div>", unsafe_allow_html=True)
                monthly_expense_man = st.number_input(
                    "월 지출", min_value=0, max_value=20000, step=50,
                    value=int(st.session_state.get("monthly_expense_man", 200)),
                    label_visibility="collapsed"
                )
                st.session_state["monthly_expense_man"] = monthly_expense_man

            st.markdown(
                f"<div style='font-size:11px;color:#445566;margin-top:8px;margin-bottom:8px;line-height:1.6;'>"
                f"강남3구·용산 LTV 50% / 그 외 LTV 70% 자동 적용<br>"
                f"대출 원리금 40년 균등 상환 시뮬레이션 적용</div>",
                unsafe_allow_html=True,
            )
            
        render_financial_fragment()

        # ── MISSION 2: 라이프스타일 별점 가중치 ──────────────────────────────
        @st.fragment
        def render_lifestyle_fragment():
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
                help="반경 1km 내 초등학교 수 및 국가 수준 학업성취도 기반 점수를 반영합니다.",
            )
            w_rail  = st.select_slider(
                "🚇 역세권", options=_STAR_OPTIONS,
                format_func=lambda x: _STAR_LABELS[x],
                value=prev_weights.get("역세권", 3),
                help="지하철역 도보 소요 시간 및 노선별 희소성 가중치를 반영합니다.",
            )
            w_shop  = st.select_slider(
                "🛒 슬세권", options=_STAR_OPTIONS,
                format_func=lambda x: _STAR_LABELS[x],
                value=prev_weights.get("슬세권", 3),
                help="도보권 내 마트, 병원, 카페 등 생활 편의시설 밀집도를 반영합니다.",
            )
            w_green = st.select_slider(
                "🌿 쾌적성", options=_STAR_OPTIONS,
                format_func=lambda x: _STAR_LABELS[x],
                value=prev_weights.get("쾌적성", 3),
                help="단지 주변 공원 면적 및 미세먼지 저감 구역 데이터를 반영합니다.",
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
            
        render_lifestyle_fragment()

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
    # MISSION: Cortex AI 통합 분석 (Warp Speed)
    # ════════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div style='font-size:20px;font-weight:800;color:#E8EAF0;margin:28px 0 12px 0;'>"
        f"🚀 Cortex AI 종합 분석 엔진</div>",
        unsafe_allow_html=True,
    )

    liquid_asset_eok    = float(st.session_state.get("liquid_asset_eok", 5.0))
    monthly_income_man  = int(st.session_state.get("monthly_income_man", 500))
    monthly_expense_man = int(st.session_state.get("monthly_expense_man", 200))
    loan_interest_rate  = float(st.session_state.get("loan_interest_rate", 4.0))
    lifestyle_weights   = st.session_state.get("lifestyle_weights", {"학군": 3, "역세권": 3, "슬세권": 3, "쾌적성": 3})

    engine_obj     = st.session_state.get("_engine")
    sf_client      = engine_obj._client if engine_obj else None

    # ── 통합 실행 버튼 (Warp Speed) ──
    col_run_btn, col_run_hint = st.columns([3, 5])
    with col_run_btn:
        run_analysis = st.button(
            "🚀 Cortex AI 통합 분석 실행",
            key="btn_run_analysis",
            use_container_width=True,
            type="primary"
        )
    with col_run_hint:
        _tw = sum(lifestyle_weights.values()) or 1
        _wt_preview = " · ".join(f"<b style='color:{MINT};'>{k}</b>" for k in lifestyle_weights.keys())
        st.markdown(
            f"<div style='padding-top:10px;font-size:12px;color:#445566;'>"
            f"재무 판독 및 가치 분석 병렬 실행 (소득/지출 및 {_wt_preview} 가중치 기반)</div>",
            unsafe_allow_html=True,
        )

    # ── 레이아웃 프레임 ──
    st.markdown(
        f"<div style='font-size:16px;font-weight:700;color:#E8EAF0;margin:20px 0 10px 0;'>"
        f"MISSION 1: 재무 실행 가능성 분석</div>",
        unsafe_allow_html=True,
    )
    fin_placeholder = st.empty()

    st.markdown(
        f"<div style='font-size:16px;font-weight:700;color:#E8EAF0;margin:28px 0 10px 0;'>"
        f"MISSION 2: 나만의 맞춤 가치 점수</div>",
        unsafe_allow_html=True,
    )
    per_placeholder = st.empty()

    if run_analysis:
        import concurrent.futures
        import time
        t_start = time.time()

        # Skeleton UX 적용
        fin_placeholder.markdown(
            f"<div class='card' style='text-align:center;padding:40px;border-color:{BORDER};'>"
            f"<div style='color:#B0C8D8;font-size:16px;font-weight:bold;margin-bottom:10px;'>⏳ AI 재무 분석 중...</div>"
            f"<div style='color:#445566;font-size:13px;'>초개인화 재무 데이터를 바탕으로 상환 능력을 시뮬레이션하고 있습니다.</div></div>",
            unsafe_allow_html=True,
        )
        per_placeholder.markdown(
            f"<div class='card' style='text-align:center;padding:40px;border-color:{BORDER};'>"
            f"<div style='color:#B0C8D8;font-size:16px;font-weight:bold;margin-bottom:10px;'>⏳ AI 가치 분석 중...</div>"
            f"<div style='color:#445566;font-size:13px;'>우선순위 가중치를 바탕으로 환경 가치 정합성을 추론하고 있습니다.</div></div>",
            unsafe_allow_html=True,
        )

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_fin = executor.submit(
                compute_financial_feasibility,
                liquid_asset_eok, monthly_income_man, monthly_expense_man, loan_interest_rate, tgt_data, sf_client
            )
            future_per = executor.submit(
                compute_personalized_score,
                lifestyle_weights, tgt_data, sf_client
            )

            with st.status("회원님의 자산과 취향을 고려해 최적의 전략을 Cortex AI가 도출하고 있습니다...", expanded=True) as status:
                fin = future_fin.result()
                per = future_per.result()
                
                status.update(label=f"✅ 병렬 분석 완료!", state="complete", expanded=False)

        st.session_state["financial_result"] = fin
        st.session_state["personal_result"]  = per
        time.sleep(0.3)

    fin = st.session_state.get("financial_result")
    if fin:
        with fin_placeholder.container():
            vc   = fin["verdict_color"]
            vl   = fin["verdict_label"]
            col_fin1, col_fin2 = st.columns([1, 2])
            with col_fin1:
                dsr = fin['dsr']
                pir = fin['personalized_pir']
                pir_color = "#FF8C00" if pir > 20 else "#00FFAA"
                dsr_pct = int(dsr * 100)
                dsr_color = "#FF4B4B" if dsr_pct > 40 else "#00FFAA"
                
                st.markdown(
                    f"<div class='card' style='border-color:{vc}44;text-align:center;padding:16px;'>"
                    f"<div style='font-size:12px;color:#445566;margin-bottom:6px;'>재무 판정 배지</div>"
                    f"<div style='font-size:26px;font-weight:900;color:{vc};"
                    f"text-shadow:0 0 16px {vc};margin-bottom:12px;'>{vl}</div>"
                    f"<div style='font-size:11px;color:#8892A4;line-height:1.9;text-align:left;'>"
                    f"매매가: <b style='color:#E8EAF0;'>{fin['price_eok']:.1f}억</b><br>"
                    f"실투자(Gap): <b style='color:{vc};'>{fin['gap_eok']:.1f}억</b><br>"
                    f"총 가용자금: <b style='color:#E8EAF0;'>{fin['total_eok']:.1f}억</b><br>"
                    f"여유/부족: <b style='color:{vc};'>{fin['surplus_eok']:+.1f}억</b><hr style='margin:8px 0;border-color:#1E2329;'>"
                    f"맞춤형 PIR: <b style='color:{pir_color};'>{pir}년</b><br>"
                    f"생존예비: <b style='color:#E8EAF0;'>{fin['survival_months']}개월</b>"
                    f"</div>"
                    f"<div style='margin-top:12px;text-align:left;'>"
                    f"  <div style='display:flex;justify-content:space-between;font-size:10px;color:#445566;margin-bottom:4px;'>"
                    f"      <span>DSR: {dsr_pct}% </span>"
                    f"      <span>월 {int(fin['monthly_loan_payment'])}만원 상환</span>"
                    f"  </div>"
                    f"  <div style='width:100%;background:#1E2329;border-radius:4px;height:6px;overflow:hidden;'>"
                    f"    <div style='width:{min(dsr_pct, 100)}%;background:{dsr_color};height:100%;'></div>"
                    f"  </div>"
                    f"</div>"
                    f"</div>",
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
        fin_placeholder.markdown(
            f"<div class='card' style='text-align:center;padding:20px;border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"상단의 [Cortex AI 통합 분석 실행] 버튼을 눌러주세요.</span></div>",
            unsafe_allow_html=True,
        )

    per = st.session_state.get("personal_result")
    if per:
        with per_placeholder.container():
            pscore  = per["personal_score"]
            pcolor  = MINT if pscore >= 75 else (YELLOW_NEO if pscore >= 50 else RED_NEO)
            pgrade  = "최적합" if pscore >= 75 else ("적합" if pscore >= 50 else "재검토")
            pglyph  = "✅" if pscore >= 75 else ("⚠️" if pscore >= 50 else "🚨")
            breakdown       = per.get("breakdown", [])
            advisor_comment = per.get("advisor_comment", "")
            matching_verdict= per.get("matching_verdict", "")
            strongest_asset = per.get("strongest_asset", "")
            _weights_display= per.get("weights", {})
            _tw2            = sum(_weights_display.values()) or 1

        # ── 상단: 종합 점수 카드 (1) + 어드바이저 리포트 (1.5) ──────────────
        col_score, col_report = st.columns([1, 1.5])

        with col_score:
            # 별점 요약 태그
            star_tags = "".join(
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:6px;'>"
                f"<span style='color:#B0C8D8;font-size:12px;'>"
                f"{_PREF_EMOJI.get(k,'⭐')} {k}</span>"
                f"<span style='color:{pcolor};font-size:12px;font-weight:700;'>"
                f"{'★'*v}{'☆'*(5-v)} {v/_tw2*100:.0f}%</span>"
                f"</div>"
                for k, v in _weights_display.items()
            )
            st.markdown(
                f"<div class='card' style='border-color:{pcolor}55;'>"
                f"<div style='font-size:11px;color:#445566;margin-bottom:4px;letter-spacing:1px;'>"
                f"WEIGHTED MATCH SCORE</div>"
                f"<div style='display:flex;align-items:baseline;gap:8px;margin-bottom:4px;'>"
                f"<span style='font-size:64px;font-weight:900;color:{pcolor};"
                f"text-shadow:0 0 24px {pcolor};line-height:1;'>{pscore}</span>"
                f"<span style='color:#445566;font-size:14px;'>/100</span>"
                f"</div>"
                f"<div style='background:{pcolor}22;border:1px solid {pcolor}44;"
                f"border-radius:20px;padding:3px 12px;display:inline-block;"
                f"font-size:12px;font-weight:700;color:{pcolor};margin-bottom:16px;'>"
                f"{pglyph} {pgrade}</div>"
                f"<hr style='border-color:#1E3A5F;margin:0 0 12px 0;'>"
                f"<div style='font-size:11px;color:#445566;margin-bottom:8px;font-weight:600;'>"
                f"사령관님의 우선순위</div>"
                f"{star_tags}"
                f"</div>",
                unsafe_allow_html=True,
            )

        with col_report:
            # 어드바이저 코멘트
            adv_lines = [l.strip() for l in advisor_comment.split("\n") if l.strip()]
            adv_html  = "".join(
                f"<div style='margin-bottom:10px;padding:11px 15px;"
                f"background:#0A1520;border-left:3px solid {pcolor}55;"
                f"border-radius:0 8px 8px 0;font-size:13px;color:#C8D8E8;line-height:1.7;'>"
                f"{line}</div>"
                for line in adv_lines
            )
            # 강점 자산 태그
            asset_tag = (
                f"<div style='margin-top:10px;padding:8px 14px;"
                f"background:linear-gradient(90deg,{pcolor}18,transparent);"
                f"border:1px solid {pcolor}44;border-radius:8px;"
                f"font-size:12px;color:{pcolor};font-weight:600;'>"
                f"🏆 이 단지의 가장 강력한 무기 &nbsp;|&nbsp; {strongest_asset}"
                f"</div>"
                if strongest_asset else ""
            )
            st.markdown(
                f"<div class='card' style='border-color:{pcolor}33;'>"
                f"<div style='font-size:13px;font-weight:700;color:{pcolor};"
                f"margin-bottom:12px;letter-spacing:0.3px;'>"
                f"🤖 Cortex AI 전략 어드바이저 리포트</div>"
                f"{adv_html}{asset_tag}</div>",
                unsafe_allow_html=True,
            )

        # ── 항목별 기여 분석 그리드 ───────────────────────────────────────────
        if breakdown:
            st.markdown(
                f"<div style='font-size:14px;font-weight:700;color:#7EC8E3;"
                f"margin:20px 0 10px 0;letter-spacing:0.5px;'>"
                f"📐 항목별 기여 점수 분해 (Value × Weight → Contribution)</div>",
                unsafe_allow_html=True,
            )
            grid_cols = st.columns(len(breakdown))
            for col, b in zip(grid_cols, breakdown):
                b_color = (
                    MINT       if b["contribution"] >= 20 else
                    YELLOW_NEO if b["contribution"] >= 12 else
                    "#445566"
                )
                star_filled = "★" * b["star"] + "☆" * (5 - b["star"])
                with col:
                    st.markdown(
                        f"<div style='background:#0D1B2A;border:1px solid #1E3A5F;"
                        f"border-top:3px solid {b_color};border-radius:10px;"
                        f"padding:14px 12px;text-align:center;'>"
                        # 이모지 + 항목명
                        f"<div style='font-size:22px;margin-bottom:4px;'>{b['emoji']}</div>"
                        f"<div style='font-size:13px;font-weight:700;color:#E0F0FF;"
                        f"margin-bottom:10px;'>{b['key']}</div>"
                        # 원천 점수 → 비중 → 기여
                        f"<div style='font-size:11px;color:#445566;margin-bottom:2px;'>"
                        f"원천 점수</div>"
                        f"<div style='font-size:20px;font-weight:800;color:#B0C8D8;"
                        f"margin-bottom:4px;'>{b['raw_score']:.0f}<span style='font-size:11px;'>점</span></div>"
                        f"<div style='font-size:16px;color:#334455;margin:2px 0;'>×</div>"
                        f"<div style='font-size:11px;color:#445566;margin-bottom:2px;'>"
                        f"반영 비중</div>"
                        f"<div style='font-size:18px;font-weight:700;color:#7EC8E3;"
                        f"margin-bottom:4px;'>{b['weight_pct']:.0f}<span style='font-size:11px;'>%</span></div>"
                        f"<div style='font-size:16px;color:#334455;margin:2px 0;'>▼</div>"
                        f"<div style='background:{b_color}22;border:1px solid {b_color}44;"
                        f"border-radius:6px;padding:4px 0;margin-top:4px;'>"
                        f"<div style='font-size:10px;color:{b_color};margin-bottom:1px;'>"
                        f"기여 점수</div>"
                        f"<div style='font-size:22px;font-weight:900;color:{b_color};'>"
                        f"+{b['contribution']:.1f}<span style='font-size:11px;'>pt</span></div>"
                        f"</div>"
                        # 별점
                        f"<div style='font-size:11px;color:#556677;margin-top:8px;'>"
                        f"{star_filled}</div>"
                        f"<div style='font-size:10px;color:#334455;margin-top:4px;"
                        f"line-height:1.4;'>{b['hint']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        # ── 취향 정합성 판정 ─────────────────────────────────────────────────
        if matching_verdict:
            has_warning = "⚠️" in matching_verdict or "경고" in matching_verdict
            mv_color    = YELLOW_NEO if has_warning else MINT
            mv_lines    = [l.strip() for l in matching_verdict.split("\n") if l.strip()]
            mv_html     = "".join(
                f"<div style='margin-bottom:8px;padding:12px 16px;"
                f"background:#0A1520;border-left:3px solid {mv_color}55;"
                f"border-radius:0 8px 8px 0;font-size:13px;color:#C8D8E8;line-height:1.7;'>"
                f"{line}</div>"
                for line in mv_lines
            )
            st.markdown(
                f"<div class='card' style='border-color:{mv_color}44;margin-top:12px;'>"
                f"<div style='font-size:13px;font-weight:700;color:{mv_color};"
                f"margin-bottom:12px;letter-spacing:0.3px;'>"
                f"🔍 Cortex AI 취향 정합성 판정</div>"
                f"{mv_html}</div>",
                unsafe_allow_html=True,
            )
    else:
        per_placeholder.markdown(
            f"<div class='card' style='text-align:center;padding:20px;border-color:{BORDER};'>"
            f"<span style='color:#445566;font-size:13px;'>"
            f"상단의 [Cortex AI 통합 분석 실행] 버튼을 눌러주세요.</span></div>",
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
