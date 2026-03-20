import streamlit as st
from datetime import datetime
from utils.helpers import (
    get_current_period, get_next_period, get_current_day,
    PERIODS, load_timetable, load_teachers, STATUS_LABELS
)

def show():
    now = datetime.now()
    cur_day   = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    # ── 헤더 ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 길잡이 GIL-ZABI</h1>
        <p>시간표를 지도 위에 펼치다 — 내 수업의 위치를 한눈에</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 실시간 상태 카드 ──────────────────────────────────────────────────────
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
            st.metric("📖 현재 교시", "쉬는 시간 / 점심")
    with col4:
        if nxt_period:
            s, e = PERIODS[nxt_period]
            st.metric("⏭️ 다음 교시", f"{nxt_period}교시",
                      delta=f"{s.strftime('%H:%M')} 시작")
        else:
            st.metric("⏭️ 다음 교시", "수업 종료")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 빠른 조회 ──────────────────────────────────────────────────────────────
    st.markdown("### ⚡ 빠른 시간표 조회")

    df = load_timetable()
    teachers_df = load_teachers()

    classes = sorted(df["반"].unique().tolist())
    col_a, col_b = st.columns([2, 1])
    with col_a:
        sel_class = st.selectbox("내 반 선택", classes, key="home_class")
    with col_b:
        days = ["월", "화", "수", "목", "금"]
        default_day = cur_day if cur_day in days else "월"
        sel_day = st.selectbox("요일", days,
                               index=days.index(default_day), key="home_day")

    sub = df[(df["반"] == sel_class) & (df["요일"] == sel_day)].sort_values("교시")

    if sub.empty:
        st.info("해당 반/요일 시간표 데이터가 없습니다.")
        return

    # 교시 카드 렌더링
    for _, row in sub.iterrows():
        period = int(row["교시"])
        s, e = PERIODS.get(period, (None, None))
        time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

        # 현재 / 다음 교시 하이라이트
        card_class = ""
        badge = ""
        if sel_day == cur_day:
            if period == cur_period:
                card_class = "card-current"
                badge = '<span class="status-badge badge-current">🔴 수업 중</span>'
            elif period == nxt_period:
                card_class = "card-next"
                badge = '<span class="status-badge badge-next">🟢 다음 교시</span>'

        st.markdown(f"""
        <div class="card {card_class}">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <span style="color:#8B949E; font-size:0.8rem;">{period}교시 · {time_str}</span><br>
                    <span style="font-size:1.1rem; font-weight:700; color:#E6EDF3;">
                        {row['과목']}
                    </span>
                    <span style="color:#8B949E; font-size:0.9rem; margin-left:8px;">
                        {row['교사명']} 선생님
                    </span>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:1rem; font-weight:600; color:#4ECDC4;">
                        📍 {row['교실위치']}
                    </div>
                    <div style="color:#8B949E; font-size:0.8rem;">{row['층']}층</div>
                    {badge}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 공지 / 안내 ────────────────────────────────────────────────────────────
    st.markdown("### 📌 이용 안내")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div style="font-size:2rem;">📅</div>
            <div style="font-weight:700; margin:8px 0 4px;">시간표 조회</div>
            <div style="color:#8B949E; font-size:0.85rem;">반별·요일별 전체 시간표와 현재 교시를 한눈에 확인하세요</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div style="font-size:2rem;">🗺️</div>
            <div style="font-weight:700; margin:8px 0 4px;">학교 지도</div>
            <div style="color:#8B949E; font-size:0.85rem;">1~5층 평면도에서 교실 위치를 클릭해 정보를 확인하세요</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div style="font-size:2rem;">🔍</div>
            <div style="font-weight:700; margin:8px 0 4px;">선생님 찾기</div>
            <div style="color:#8B949E; font-size:0.85rem;">선생님 이름으로 검색하면 현재 위치를 알 수 있어요</div>
        </div>
        """, unsafe_allow_html=True)
