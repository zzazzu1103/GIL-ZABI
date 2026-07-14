import streamlit as st
from datetime import datetime, timezone, timedelta
from utils.auth import get_current_user, get_role
from utils.helpers import (
    get_current_period, get_next_period, get_current_day,
    PERIODS, load_timetable_sheets, STATUS_LABELS
)

KST = timezone(timedelta(hours=9))


def show():
    now        = datetime.now(KST)
    cur_day    = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    # ── 헤더 ───────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 길잡이 <span>GIL-ZABI</span></h1>
        <p>시간표를 지도 위에 펼치다 — 내 수업의 위치를 한눈에</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 실시간 상태 ─────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    day_display = cur_day if cur_day else "주말"
    with col1:
        st.metric("📅 오늘", f"{now.strftime('%m/%d')} ({day_display})")
    with col2:
        st.metric("🕐 현재 시각", now.strftime("%H:%M"))
    with col3:
        if cur_period:
            s, e = PERIODS[cur_period]
            st.metric("📖 현재 교시", f"{cur_period}교시",
                      delta=f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}")
        else:
            st.metric("📖 현재 교시", "쉬는 시간")
    with col4:
        if nxt_period:
            s, e = PERIODS[nxt_period]
            st.metric("⏭️ 다음 교시", f"{nxt_period}교시",
                      delta=f"{s.strftime('%H:%M')} 시작")
        else:
            st.metric("⏭️ 다음 교시", "수업 종료")

    # ── 시간표 (timetable.py 본문 통합) ─────────────────────────────
    st.markdown('<hr style="margin:14px 0 20px;">', unsafe_allow_html=True)
    st.markdown("### 📅 시간표")

    from pages.timetable import show_body
    show_body()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 이용 안내 (카드를 클릭하면 해당 페이지로 이동) ─────────────────
    st.markdown("### 📌 이용 안내")
    from utils.auth import ROLE_PAGES
    available = ROLE_PAGES[get_role()]
    col1, col2, col3 = st.columns(3)
    cards = [
        (col1, "🗺️", "학교 지도", "1~5층 평면도에서 교실 위치를 확인하세요", "🗺️ 학교 지도", "map"),
        (col2, "🔍", "선생님 찾기", "선생님 이름으로 검색하면 현재 위치를 알 수 있어요", "🔍 선생님 찾기", "teacher"),
        (col3, "👤", "개인 설정", "내 반과 탐구 과목을 설정해 맞춤 시간표를 확인하세요", "👤 개인 설정", "profile"),
    ]

    # 카드 전체를 덮는 투명 버튼으로 클릭 영역을 확장해, 별도의 "이동" 버튼 없이
    # 카드를 누르면 바로 이동되도록 만든다.
    st.markdown("""
    <style>
    div[class*="st-key-home_card_"] { position: relative; transition: border-color 0.2s; }
    div[class*="st-key-home_card_"]:hover { border-color: #B8A05A !important; }
    div[class*="st-key-home_card_"] div[class*="st-key-home_nav_"] {
        position: absolute; inset: 0; z-index: 1;
    }
    div[class*="st-key-home_card_"] div[class*="st-key-home_nav_"] button {
        width: 100%; height: 100%; opacity: 0; cursor: pointer;
        background: transparent !important; border: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    for col, icon, title, desc, target, cid in cards:
        with col:
            with st.container(border=True, key=f"home_card_{cid}"):
                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:1.8rem;">{icon}</div>'
                    f'<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">{title}</div>'
                    f'<div style="color:#9E9070;font-size:0.82rem;">{desc}</div>'
                    f'</div>', unsafe_allow_html=True)
                if target in available:
                    if st.button(title, key=f"home_nav_{cid}", use_container_width=True):
                        st.session_state["nav_target"] = target
                        st.rerun()
