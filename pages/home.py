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

    # ── 이용 안내 ───────────────────────────────────────────────────
    st.markdown("### 📌 이용 안내")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">🗺️</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">학교 지도</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">1~5층 평면도에서 교실 위치를 확인하세요</div>'
            '</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">🔍</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">선생님 찾기</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">선생님 이름으로 검색하면 현재 위치를 알 수 있어요</div>'
            '</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">👤</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">개인 설정</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">내 반과 탐구 과목을 설정해 맞춤 시간표를 확인하세요</div>'
            '</div>', unsafe_allow_html=True)
