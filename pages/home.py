import streamlit as st
from datetime import datetime, timezone, timedelta
from utils.auth import get_current_user, get_role
from utils.helpers import (
    get_current_period, get_next_period, get_current_day,
    PERIODS, load_timetable, STATUS_LABELS
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

    # ── 이용 안내 (클릭하면 해당 페이지로 이동) ──────────────────────
    st.markdown("### 📌 이용 안내")
    from utils.auth import ROLE_PAGES
    available = ROLE_PAGES[get_role()]
    col1, col2, col3 = st.columns(3)
    cards = [
        (col1, "🗺️", "학교 지도", "1~5층 평면도에서 교실 위치를 확인하세요", "🗺️ 학교 지도"),
        (col2, "🔍", "선생님 찾기", "선생님 이름으로 검색하면 현재 위치를 알 수 있어요", "🔍 선생님 찾기"),
        (col3, "👤", "개인 설정", "내 반과 탐구 과목을 설정해 맞춤 시간표를 확인하세요", "👤 개인 설정"),
    ]
    for col, icon, title, desc, target in cards:
        with col:
            with st.container(border=True):
                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<div style="font-size:1.8rem;">{icon}</div>'
                    f'<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">{title}</div>'
                    f'<div style="color:#9E9070;font-size:0.82rem;">{desc}</div>'
                    f'</div>', unsafe_allow_html=True)
                if target in available:
                    if st.button("이동", key=f"home_nav_{title}", use_container_width=True):
                        st.session_state["nav_target"] = target
                        st.rerun()
