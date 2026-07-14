import streamlit as st
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
from utils.helpers import (
    load_timetable, load_teachers, get_current_period,
    get_next_period, get_current_day, PERIODS, get_teacher_location,
    load_teacher_timetable, teacher_subjects,
)
from utils.floorplan import render_map, find_room_floor, room_display_name, is_outdoor_room

def show():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 선생님 찾기</h1>
        <p>선생님 이름을 검색하면 현재 어디 계신지 바로 알 수 있어요</p>
    </div>
    """, unsafe_allow_html=True)

    timetable_df = load_timetable()
    teachers_df  = load_teachers()
    try:
        schedule_df = load_teacher_timetable()   # 선택과목 포함 교사별 전체 시간표
    except FileNotFoundError:
        schedule_df = None
    now          = datetime.now(KST)
    cur_day      = get_current_day(now)
    cur_period   = get_current_period(now)
    nxt_period   = get_next_period(now)

    teacher_names = sorted(teachers_df["교사명"].tolist())

    # ── 검색 UI ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 선생님 이름 또는 과목 검색", placeholder="예: 김영희, 수학...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_dropdown = st.checkbox("목록에서 선택", value=False)

    picked = st.session_state.get("ts_selected")

    def _teacher_subject(name: str) -> str:
        row = teachers_df[teachers_df["교사명"] == name]
        fallback = str(row.iloc[0]["담당과목"]) if not row.empty else ""
        return teacher_subjects(name) or fallback

    if use_dropdown:
        selected_teacher = st.selectbox("선생님 선택", teacher_names)
    else:
        # 검색어 기반 필터 — 이름 또는 담당 과목에 검색어가 포함되면 매칭
        if query:
            matches = [
                n for n in teacher_names
                if query in n or query in _teacher_subject(n)
            ]
            if not matches:
                st.warning(f"'{query}'와 일치하는 선생님이 없습니다.")
                return
            selected_teacher = st.selectbox("검색 결과", matches)
        elif picked and picked in teacher_names:
            # 전체 목록에서 클릭해서 선택한 경우
            selected_teacher = picked
            if st.button("← 전체 목록으로 돌아가기", key="ts_back"):
                st.session_state.pop("ts_selected", None)
                st.rerun()
        else:
            st.markdown("""
            <div class="card" style="text-align:center; padding:40px;">
                <div style="font-size:3rem; margin-bottom:12px;">🔍</div>
                <div style="font-size:1.1rem; font-weight:600; color:#9E9070;">
                    선생님 이름을 검색하거나 아래 목록에서 선택하세요
                </div>
                <div style="font-size:0.85rem; color:#D4C9A8; margin-top:6px;">
                    성함 일부만 입력해도 검색됩니다
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 전체 선생님 목록 — 클릭하면 바로 선택
            st.markdown("### 👩‍🏫 전체 선생님 목록")
            sorted_teachers = teachers_df.sort_values("교사명")
            cols = st.columns(3)
            for i, (_, t) in enumerate(sorted_teachers.iterrows()):
                with cols[i % 3]:
                    subj = teacher_subjects(t['교사명']) or t['담당과목']
                    if st.button(
                        f"**{t['교사명']}**  \n:small[:gray[{subj}]]",
                        key=f"tsbtn_{t['교사명']}",
                        help=str(t["교무실"]),
                        use_container_width=True,
                    ):
                        st.session_state["ts_selected"] = t["교사명"]
                        st.rerun()
            return

    # ── 선택된 선생님 상세 정보 ────────────────────────────────────────────────
    teacher_info = teachers_df[teachers_df["교사명"] == selected_teacher]
    if teacher_info.empty:
        st.error("선생님 정보를 찾을 수 없습니다.")
        return

    ti = teacher_info.iloc[0]

    st.markdown("---")
    st.markdown(f"## 👩‍🏫 {selected_teacher} 선생님")

    # 기본 정보 카드
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="card">
            <div style="color:#9E9070; font-size:0.8rem; margin-bottom:8px;">기본 정보</div>
            <div style="font-size:1rem; font-weight:600;">담당 과목</div>
            <div style="font-size:1.4rem; font-weight:900; color:#7D6B2E; margin:4px 0 12px;">{teacher_subjects(selected_teacher) or ti['담당과목']}</div>
            <div style="font-size:1rem; font-weight:600;">교무실</div>
            <div style="font-size:1rem; color:#3D3929; margin-top:4px;">
                📍 {ti['교무실위치']} ({ti['층']}층)
            </div>
        </div>
        """, unsafe_allow_html=True)
    # 현재 위치 계산: 수업 중이면 그 교실, 쉬는 시간·공강이면 교무실
    loc = get_teacher_location(timetable_df, teachers_df,
                               selected_teacher, cur_day, cur_period)
    is_teaching = loc["상태"] == "수업중"
    loc_rid   = str(loc["교실"])
    is_outdoor = is_outdoor_room(loc_rid)
    loc_floor = find_room_floor(loc_rid)
    if loc_floor is None:
        loc_floor = int(loc["층"]) if str(loc["층"]).isdigit() and 1 <= int(loc["층"]) <= 5 else 2
    loc_floor_label = "🌳 야외" if is_outdoor else f"{loc_floor}층"

    if not cur_day:
        when_str, note = "주말", "오늘은 수업이 없어요 · 교무실 기준 위치예요"
    elif cur_period is None:
        when_str, note = "쉬는 시간", "지금은 쉬는 시간이에요 · 교무실에 계세요"
    else:
        s, e = PERIODS.get(cur_period, (None, None))
        when_str = f"{cur_period}교시 · {s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else f"{cur_period}교시"
        note = "" if is_teaching else "이번 교시에는 수업이 없어요 · 교무실에 계세요"

    with c2:
        status_color = "#D97706" if is_teaching else "#059669"
        status_icon  = "🔴" if is_teaching else "🟢"
        badge_cls    = "badge-current" if is_teaching else "badge-next"
        status_label = "수업 중" if is_teaching else "교무실"

        extra = ""
        if is_teaching:
            extra += f"<div style='color:#3D3929; margin-top:6px;'>{loc['과목']} · {loc['반']}</div>"
        if note:
            extra += f"<div style='color:#9E9070; font-size:0.8rem; margin-top:6px;'>{note}</div>"

        st.markdown(
            f'<div class="card {"card-current" if is_teaching else "card-next"}">'
            f'<div style="color:#9E9070; font-size:0.8rem; margin-bottom:8px;">지금 ({when_str})</div>'
            f'<span class="status-badge {badge_cls}">{status_icon} {status_label}</span>'
            f'<div style="font-size:1.4rem; font-weight:900; color:{status_color}; margin:10px 0 4px;">'
            f'📍 {room_display_name(loc_rid)}</div>'
            f'<div style="color:#9E9070; font-size:0.85rem;">{loc_floor_label}</div>'
            f'{extra}</div>',
            unsafe_allow_html=True,
        )

    # ── 지도에서 위치 보기 ─────────────────────────────────────────────────────
    st.caption(
        f"📍 {selected_teacher} 선생님은 지금 "
        + (f"**{room_display_name(loc_rid)}**에서 수업 중이에요."
           if is_teaching else f"**{room_display_name(loc_rid)}**에 계세요.")
    )
    if is_outdoor:
        st.info(f"🌳 **{room_display_name(loc_rid)}**은(는) 야외 장소라 건물 지도에는 표시되지 않아요.")
    else:
        st.markdown(f"### 🗺️ 지도에서 위치 보기 — {loc_floor}층")
        render_map(loc_floor, {loc_rid: "teacher"})

    # ── 오늘 하루 일정 ─────────────────────────────────────────────────────────
    if cur_day:
        st.markdown(f"### 📅 {cur_day}요일 수업 일정")

        src = schedule_df if schedule_df is not None else timetable_df
        day_schedule = src[
            (src["교사명"] == selected_teacher) &
            (src["요일"] == cur_day)
        ].sort_values("교시")

        if day_schedule.empty:
            st.info(f"{cur_day}요일에는 수업이 없습니다. 교무실에 계십니다.")
        else:
            for _, row in day_schedule.iterrows():
                period = int(row["교시"])
                s, e = PERIODS.get(period, (None, None))
                time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

                is_current = (period == cur_period)
                is_next    = (period == nxt_period)

                card_cls   = "card-current" if is_current else ("card-next" if is_next else "")
                badge_html = ""
                if is_current:
                    badge_html = '<span class="status-badge badge-current">🔴 수업 중</span>'
                elif is_next:
                    badge_html = '<span class="status-badge badge-next">🟢 다음 교시</span>'

                room_label = room_display_name(str(row["교실위치"]))
                floor_label = "🌳 야외" if is_outdoor_room(row["교실위치"]) else f"{row['층']}층"
                # 배지가 없을 때(badge_html="") 이 줄이 빈 줄로 남으면 마크다운
                # 파서가 HTML 블록을 중간에 끊고 그 뒤 들여쓰기를 코드블록으로
                # 오인해 "</div>" 가 그대로 텍스트로 보이는 문제가 있어
                # 줄바꿈 없는 한 줄짜리 문자열로 조립한다.
                st.markdown(
                    f'<div class="card {card_cls}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<div>'
                    f'<div style="color:#9E9070;font-size:0.78rem;">{period}교시 · {time_str}</div>'
                    f'<div style="font-size:1.05rem;font-weight:700;margin-top:4px;">'
                    f'{row["과목"]} — {room_label}</div>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<div style="font-size:1rem;font-weight:700;color:#7D6B2E;">📍 {row["교실위치"]}</div>'
                    f'<div style="color:#9E9070;font-size:0.78rem;">{floor_label}</div>'
                    f'{badge_html}'
                    f'</div>'
                    f'</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── 주간 전체 일정 ─────────────────────────────────────────────────────────
    with st.expander("📋 주간 전체 시간표 보기"):
        days = ["월","화","수","목","금"]
        src = schedule_df if schedule_df is not None else timetable_df
        week_data = src[src["교사명"] == selected_teacher]

        if week_data.empty:
            st.info("등록된 수업 데이터가 없습니다.")
        else:
            for day in days:
                day_df = week_data[week_data["요일"] == day].sort_values("교시")
                if not day_df.empty:
                    st.markdown(f"**{day}요일**")
                    for _, r in day_df.iterrows():
                        floor_txt = "야외" if is_outdoor_room(r["교실위치"]) else f"{r['층']}층"
                        st.markdown(
                            f"　{int(r['교시'])}교시 · {r['과목']} · "
                            f"{room_display_name(str(r['교실위치']))} · "
                            f"📍{r['교실위치']}({floor_txt})"
                        )
