import streamlit as st
from datetime import datetime, timezone, timedelta
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

    # ── 헤더 ─────────────────────────────────────────────────────
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 길잡이 <span>GIL-ZABI</span></h1>
        <p>시간표를 지도 위에 펼치다 — 내 수업의 위치를 한눈에</p>
    </div>
    """, unsafe_allow_html=True)

    # ── 실시간 상태 ───────────────────────────────────────────────
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

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 빠른 시간표 조회 ──────────────────────────────────────────
    st.markdown("### ⚡ 빠른 시간표 조회")

    df = load_timetable()
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

    for _, row in sub.iterrows():
        period = int(row["교시"])
        s, e   = PERIODS.get(period, (None, None))
        time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

        card_class = ""
        badge_html = ""
        if sel_day == cur_day:
            if period == cur_period:
                card_class = "card-current"
                badge_html = '<span class="status-badge badge-current">🟡 수업 중</span>'
            elif period == nxt_period:
                card_class = "card-next"
                badge_html = '<span class="status-badge badge-next">🟢 다음 교시</span>'

        # 층별 색상 (아이보리 테마)
        floor_colors = {1:"#7D6B2E", 2:"#5C7A3E", 3:"#2E6B7D", 4:"#6B2E7D", 5:"#7D3A2E"}
        floor_color = floor_colors.get(int(row["층"]), "#9E9070")

        st.markdown(
            f'<div class="card {card_class}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<div>'
            f'<span style="color:#9E9070;font-size:0.78rem;">{period}교시 · {time_str}</span><br>'
            f'<span style="font-size:1.05rem;font-weight:700;color:#3D3929;">{row["과목"]}</span>'
            f'<span style="color:#9E9070;font-size:0.85rem;margin-left:8px;">{row["교사명"]} 선생님</span>'
            f'</div>'
            f'<div style="text-align:right;">'
            f'<div style="font-size:1rem;font-weight:700;color:{floor_color};">📍 {row["교실위치"]}</div>'
            f'<div style="color:#9E9070;font-size:0.78rem;">{row["층"]}층</div>'
            f'{badge_html}'
            f'</div></div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 이용 안내 ─────────────────────────────────────────────────
    st.markdown("### 📌 이용 안내")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">📅</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">시간표 조회</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">반별·요일별 전체 시간표와 현재 교시를 한눈에 확인하세요</div>'
            '</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">🗺️</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">학교 지도</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">1~5층 평면도에서 교실 위치를 확인하세요</div>'
            '</div>', unsafe_allow_html=True)
    with col3:
        st.markdown(
            '<div class="card" style="text-align:center;">'
            '<div style="font-size:1.8rem;">🔍</div>'
            '<div style="font-weight:700;margin:8px 0 4px;color:#3D3929;">선생님 찾기</div>'
            '<div style="color:#9E9070;font-size:0.82rem;">선생님 이름으로 검색하면 현재 위치를 알 수 있어요</div>'
            '</div>', unsafe_allow_html=True)
