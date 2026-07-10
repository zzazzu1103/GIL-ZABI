import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
from utils.auth import get_role
from utils.helpers import (
    load_timetable, get_current_period, get_next_period,
    get_current_day, PERIODS, period_status,
    STATUS_LABELS, STATUS_COLORS, sort_classes,
    get_personalized_timetable,
)


def _render_day_cards(sub: pd.DataFrame, sel_day: str, cur_day, cur_period, nxt_period, now):
    """교시별 카드 렌더링 (홈/시간표 공용)"""
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

        floor_colors = {1:"#2E6B7D", 2:"#6B2E7D", 3:"#FF7B72", 4:"#C2852A", 5:"#059669"}
        floor_color = floor_colors.get(int(row["층"]), "#9E9070")

        st.markdown(f"""
        <div class="card {card_cls}">
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="min-width:56px; text-align:center;
                            background:#FAF7F2; border-radius:10px; padding:10px 0;">
                    <div style="font-size:1.4rem; font-weight:900; color:#7D6B2E;">{period}</div>
                    <div style="font-size:0.65rem; color:#9E9070;">교시</div>
                </div>
                <div style="flex:1;">
                    <div style="font-size:0.78rem; color:#9E9070; margin-bottom:4px;">{time_str}</div>
                    <div style="font-size:1.15rem; font-weight:700; color:#3D3929;">
                        {row['과목']}
                        <span style="font-size:0.85rem; font-weight:400; color:#9E9070; margin-left:6px;">
                            {row['교사명']} 선생님
                        </span>
                    </div>
                </div>
                <div style="text-align:right; min-width:120px;">
                    <div style="font-size:1rem; font-weight:700; color:{floor_color};">
                        📍 {row['교실위치']}
                    </div>
                    <div style="font-size:0.78rem; color:#9E9070; margin:2px 0 6px;">{row['층']}층</div>
                    <span class="status-badge {badge_cls}">{badge_label}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def show_for_class(preset_class: str = None, preset_day: str = None):
    """홈화면에서 호출하는 함수 — 헤더 없이 시간표만 렌더링"""
    df = load_timetable()
    now = datetime.now(KST)
    cur_day    = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    classes = sort_classes(df["반"].unique().tolist())
    days    = ["월", "화", "수", "목", "금"]
    role    = get_role()

    # 기본 반 결정: preset > 세션 내 반 > 첫번째 반
    default_class = preset_class or st.session_state.get("my_class", classes[0])
    default_day   = preset_day or (cur_day if cur_day in days else "월")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if role == "student" and "my_class" in st.session_state:
            st.markdown(
                f'<div class="card" style="padding:10px 14px;">'
                f'<span style="color:#9E9070;font-size:0.78rem;">내 반</span><br>'
                f'<span style="font-weight:700;color:#3D3929;">{default_class}</span>'
                f'</div>', unsafe_allow_html=True)
            sel_class = default_class
        else:
            idx = classes.index(default_class) if default_class in classes else 0
            sel_class = st.selectbox("🏫 반 선택", classes, index=idx, key="home_timetable_class")
    with col2:
        sel_day = st.selectbox("📆 요일", days, index=days.index(default_day), key="home_timetable_day")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_all = st.checkbox("전체 요일", value=False, key="home_timetable_all")

    if show_all:
        _render_pivot(df, sel_class, days)
        return

    sub = get_personalized_timetable(df, sel_class, sel_day)
    if sub.empty:
        st.info("해당 반/요일 시간표 데이터가 없습니다.")
        return

    _render_day_cards(sub, sel_day, cur_day, cur_period, nxt_period, now)

    # 요약
    st.markdown("---")
    floors_visited = sub["층"].unique()
    subjects = sub["과목"].unique()
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("총 수업 수", f"{len(sub)}교시")
    with c2: st.metric("이동하는 층", f"{len(floors_visited)}개 층",
                       delta=f"{', '.join(map(str, sorted(floors_visited)))}층")
    with c3: st.metric("과목 수", f"{len(subjects)}과목")


def _render_pivot(df, sel_class, days):
    """전체 요일 피벗 테이블"""
    st.markdown(f"### 📋 {sel_class} 주간 시간표")
    sub = df[df["반"] == sel_class].copy()
    # ★ 핵심 수정: 교실위치를 str로 변환 후 합치기
    sub["내용"] = sub["과목"] + "\n" + sub["교사명"] + "\n" + sub["교실위치"].astype(str)
    pivot = sub.pivot_table(index="교시", columns="요일", values="내용", aggfunc="first")
    ordered_days = [d for d in days if d in pivot.columns]
    pivot = pivot.reindex(columns=ordered_days)
    pivot.index = [f"{i}교시" for i in pivot.index]

    def style_cell(val):
        if not isinstance(val, str):
            return "background:#F5F0E8; color:#555;"
        return "background:#fff; color:#3D3929; white-space:pre-line; font-size:0.85rem;"

    styler = pivot.fillna("—").style
    # pandas 2.1+ 에서 Styler.applymap 이 map 으로 바뀜 (3.0에서 applymap 제거)
    style_fn = styler.map if hasattr(styler, "map") else styler.applymap
    st.dataframe(
        style_fn(style_cell),
        use_container_width=True,
        height=320,
    )


def show():
    st.markdown("""
    <div class="main-header">
        <h1>📅 시간표 조회</h1>
        <p>반별 전체 시간표를 한눈에 확인하고, 현재·다음 교시를 실시간으로 파악하세요</p>
    </div>
    """, unsafe_allow_html=True)

    df = load_timetable()
    now = datetime.now(KST)
    cur_day    = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    classes = sort_classes(df["반"].unique().tolist())
    days    = ["월", "화", "수", "목", "금"]
    role    = get_role()
    my_class = st.session_state.get("my_class", classes[0])

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if role == "student" and "my_class" in st.session_state:
            st.markdown(
                f'<div class="card" style="padding:10px 14px;">'
                f'<span style="color:#9E9070;font-size:0.78rem;">내 반</span><br>'
                f'<span style="font-weight:700;color:#3D3929;">{my_class}</span>'
                f'</div>', unsafe_allow_html=True)
            sel_class = my_class
        else:
            sel_class = st.selectbox("🏫 반 선택", classes)
    with col2:
        default_day = cur_day if cur_day in days else "월"
        sel_day = st.selectbox("📆 요일 선택", days, index=days.index(default_day))
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_all = st.checkbox("전체 요일", value=False)

    st.markdown("---")

    if show_all:
        _render_pivot(df, sel_class, days)
        return

    sub = get_personalized_timetable(df, sel_class, sel_day)

    if sub.empty:
        st.warning("해당 반/요일 데이터가 없습니다.")
        return

    st.markdown(f"### {sel_class} · {sel_day}요일 시간표")

    col_l = st.columns(4)
    badges = [
        ("🔴 수업 중", "badge-current"),
        ("🟢 다음 교시", "badge-next"),
        ("⚫ 완료", "badge-done"),
        ("⚪ 예정", "badge-upcoming"),
    ]
    for col, (label, cls) in zip(col_l, badges):
        with col:
            st.markdown(f'<span class="status-badge {cls}">{label}</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    _render_day_cards(sub, sel_day, cur_day, cur_period, nxt_period, now)

    st.markdown("---")
    st.markdown("#### 📊 오늘 이동 요약")
    floors_visited = sub["층"].unique()
    subjects = sub["과목"].unique()
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("총 수업 수", f"{len(sub)}교시")
    with c2: st.metric("이동하는 층", f"{len(floors_visited)}개 층",
                       delta=f"{', '.join(map(str, sorted(floors_visited)))}층")
    with c3: st.metric("과목 수", f"{len(subjects)}과목")
