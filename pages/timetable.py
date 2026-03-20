import streamlit as st
import pandas as pd
from datetime import datetime
from utils.helpers import (
    load_timetable, get_current_period, get_next_period,
    get_current_day, PERIODS, period_status,
    STATUS_LABELS, STATUS_COLORS
)

def show():
    st.markdown("""
    <div class="main-header">
        <h1>📅 시간표 조회</h1>
        <p>반별 전체 시간표를 한눈에 확인하고, 현재·다음 교시를 실시간으로 파악하세요</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_timetable()
    now = datetime.now()
    cur_day    = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    # ── 필터 ─────────────────────────────────────────────────────────────────
    classes = sorted(df["반"].unique().tolist())
    days    = ["월", "화", "수", "목", "금"]

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        sel_class = st.selectbox("🏫 반 선택", classes)
    with col2:
        default_day = cur_day if cur_day in days else "월"
        sel_day = st.selectbox("📆 요일 선택", days, index=days.index(default_day))
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_all = st.checkbox("전체 요일", value=False)

    st.markdown("---")

    # ── 전체 요일 뷰 ──────────────────────────────────────────────────────────
    if show_all:
        st.markdown(f"### 📋 {sel_class} 주간 시간표")

        # 피벗 테이블 생성
        sub = df[df["반"] == sel_class].copy()
        sub["내용"] = sub["과목"] + "\n" + sub["교사명"] + "\n" + sub["교실위치"]
        pivot = sub.pivot_table(index="교시", columns="요일",
                                values="내용", aggfunc="first")
        # 요일 순서 맞춤
        ordered_days = [d for d in days if d in pivot.columns]
        pivot = pivot.reindex(columns=ordered_days)
        pivot.index = [f"{i}교시" for i in pivot.index]

        # 스타일
        def style_cell(val):
            if not isinstance(val, str):
                return "background:#1A2030; color:#555;"
            return "background:#161B22; color:#E6EDF3; white-space:pre-line; font-size:0.85rem;"

        st.dataframe(
            pivot.fillna("—").style.applymap(style_cell),
            use_container_width=True,
            height=320,
        )
        return

    # ── 단일 요일 상세 뷰 ────────────────────────────────────────────────────
    sub = df[(df["반"] == sel_class) & (df["요일"] == sel_day)].sort_values("교시")

    if sub.empty:
        st.warning("해당 반/요일 데이터가 없습니다.")
        return

    st.markdown(f"### {sel_class} · {sel_day}요일 시간표")

    # 범례
    col_l = st.columns(4)
    badges = [
        ("🔴 수업 중", "badge-current"),
        ("🟢 다음 교시", "badge-next"),
        ("⚫ 완료", "badge-done"),
        ("⚪ 예정", "badge-upcoming"),
    ]
    for col, (label, cls) in zip(col_l, badges):
        with col:
            st.markdown(f'<span class="status-badge {cls}">{label}</span>',
                        unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    for _, row in sub.iterrows():
        period = int(row["교시"])
        s, e   = PERIODS.get(period, (None, None))
        time_str = f"{s.strftime('%H:%M')} ~ {e.strftime('%H:%M')}" if s else ""

        status = "upcoming"
        card_cls = ""
        badge_cls = "badge-upcoming"
        badge_label = "⚪ 예정"

        if sel_day == cur_day:
            status = period_status(period, now)
            if status == "current":
                card_cls, badge_cls, badge_label = "card-current", "badge-current", "🔴 수업 중"
            elif status == "next":
                card_cls, badge_cls, badge_label = "card-next", "badge-next", "🟢 다음 교시"
            elif status == "done":
                badge_cls, badge_label = "badge-done", "⚫ 완료"

        # 층별 색상
        floor_colors = {1:"#58A6FF", 2:"#BC8CFF", 3:"#FF7B72", 4:"#FFA657", 5:"#3FB950"}
        floor_color = floor_colors.get(int(row["층"]), "#8B949E")

        st.markdown(f"""
        <div class="card {card_cls}">
            <div style="display:flex; align-items:center; gap:16px;">
                <!-- 교시 번호 -->
                <div style="min-width:56px; text-align:center; 
                            background:#0D1117; border-radius:10px; padding:10px 0;">
                    <div style="font-size:1.4rem; font-weight:900; color:#4ECDC4;">{period}</div>
                    <div style="font-size:0.65rem; color:#8B949E;">교시</div>
                </div>
                <!-- 내용 -->
                <div style="flex:1;">
                    <div style="font-size:0.78rem; color:#8B949E; margin-bottom:4px;">{time_str}</div>
                    <div style="font-size:1.15rem; font-weight:700; color:#E6EDF3;">
                        {row['과목']}
                        <span style="font-size:0.85rem; font-weight:400; color:#8B949E; margin-left:6px;">
                            {row['교사명']} 선생님
                        </span>
                    </div>
                </div>
                <!-- 위치 + 뱃지 -->
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:1rem; font-weight:700; color:{floor_color};">
                        📍 {row['교실위치']}
                    </div>
                    <div style="font-size:0.78rem; color:#8B949E; margin:2px 0 6px;">{row['층']}층</div>
                    <span class="status-badge {badge_cls}">{badge_label}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── 요약 통계 ─────────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📊 오늘 이동 요약")
    floors_visited = sub["층"].unique()
    subjects = sub["과목"].unique()

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 수업 수", f"{len(sub)}교시")
    with c2:
        st.metric("이동하는 층", f"{len(floors_visited)}개 층",
                  delta=f"{', '.join(map(str, sorted(floors_visited)))}층")
    with c3:
        st.metric("과목 수", f"{len(subjects)}과목")
