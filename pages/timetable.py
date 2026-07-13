import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
from utils.auth import get_role
from utils.helpers import (
    load_timetable, get_current_period, get_next_period,
    get_current_day, PERIODS, period_status,
    STATUS_LABELS, STATUS_COLORS, sort_classes,
    get_personalized_timetable, is_unselected_elective,
    is_elective, elective_subject_name, load_teacher_timetable,
    subject_color, day_label,
)
from utils.floorplan import room_display_name, ROOM_NAME, ROOM_FLOOR
from utils.room_overrides import save_room_override


def _room_options():
    """지도에 실제로 존재하는 교실 id 목록 (층 → 이름 순 정렬).

    교실 위치 수정은 이 목록에서만 고를 수 있게 해서, 지도의 id 와
    어긋나는 값을 저장해 지도에 아무것도 표시되지 않는 상황을 막는다.
    """
    ids = sorted(ROOM_NAME, key=lambda rid: (ROOM_FLOOR.get(rid, 0), ROOM_NAME[rid]))
    return [(rid, f"{ROOM_NAME[rid]} · {rid} ({ROOM_FLOOR.get(rid, '?')}층)") for rid in ids]


def _subject_display(subject, teacher) -> str:
    """선택과목이면 실제 과목명을 함께 표시 (예: '탐구D · 물리Ⅱ')."""
    if is_elective(subject):
        real = elective_subject_name(subject, teacher)
        if real:
            return f"{subject} · {real}"
    return str(subject)


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

        # 선택과목인데 아직 선생님을 고르지 않았으면 교사/위치를 표시하지 않음
        if is_unselected_elective(row["과목"]):
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
                                선택과목
                            </span>
                        </div>
                    </div>
                    <div style="text-align:right; min-width:150px;">
                        <div style="font-size:0.85rem; font-weight:700; color:#B45309;">
                            ❓ 선생님 미선택
                        </div>
                        <div style="font-size:0.75rem; color:#9E9070; margin:2px 0 6px;">
                            개인 설정에서 선택하면<br>교실·층이 표시돼요
                        </div>
                        <span class="status-badge {badge_cls}">{badge_label}</span>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            continue

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
                        <span style="{f'background:{subject_color(row["과목"])}; padding:2px 10px; border-radius:6px;' if subject_color(row['과목']) else ''}">
                            {_subject_display(row['과목'], row['교사명'])}
                        </span>
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


def _render_teacher_day_cards(teacher: str, sub: pd.DataFrame, sel_day: str,
                              cur_day, cur_period, nxt_period, now):
    """교사 본인 시간표 카드 (반/교실 표시). 수업이 없는 교시는 '공강'으로
    표시하고(숨기지 않음), 수업이 있는 교시는 교실 위치를 바로 수정할 수 있다."""
    by_period = {int(r["교시"]): r for _, r in sub.iterrows()}

    for period in sorted(PERIODS):
        s, e = PERIODS.get(period, (None, None))
        time_str = f"{s.strftime('%H:%M')} ~ {e.strftime('%H:%M')}" if s else ""
        row = by_period.get(period)

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

        if row is None:
            st.markdown(
                f'<div class="card {card_cls}">'
                f'<div style="display:flex; align-items:center; gap:16px;">'
                f'<div style="min-width:56px; text-align:center; background:#FAF7F2; '
                f'border-radius:10px; padding:10px 0;">'
                f'<div style="font-size:1.4rem; font-weight:900; color:#7D6B2E;">{period}</div>'
                f'<div style="font-size:0.65rem; color:#9E9070;">교시</div></div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:0.78rem; color:#9E9070; margin-bottom:4px;">{time_str}</div>'
                f'<div style="font-size:1.05rem; font-weight:700; color:#C9BFA9;">☕ 공강</div>'
                f'</div>'
                f'<div style="text-align:right; min-width:120px;">'
                f'<span class="status-badge {badge_cls}">{badge_label}</span>'
                f'</div></div></div>',
                unsafe_allow_html=True,
            )
            continue

        floor_colors = {1: "#2E6B7D", 2: "#6B2E7D", 3: "#FF7B72", 4: "#C2852A", 5: "#059669"}
        floor_color = floor_colors.get(int(row["층"]), "#9E9070")
        room_label = room_display_name(str(row["교실위치"]))

        # 빈 줄이 HTML 블록 파싱을 깨는 문제(마크다운 렌더러가 들여쓰기된
        # 뒷부분을 코드블록으로 오인)를 피하려고 한 줄짜리 문자열로 조립한다.
        st.markdown(
            f'<div class="card {card_cls}">'
            f'<div style="display:flex; align-items:center; gap:16px;">'
            f'<div style="min-width:56px; text-align:center; background:#FAF7F2; '
            f'border-radius:10px; padding:10px 0;">'
            f'<div style="font-size:1.4rem; font-weight:900; color:#7D6B2E;">{period}</div>'
            f'<div style="font-size:0.65rem; color:#9E9070;">교시</div></div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:0.78rem; color:#9E9070; margin-bottom:4px;">{time_str}</div>'
            f'<div style="font-size:1.15rem; font-weight:700; color:#3D3929;">'
            f'{row["과목"]}'
            f'<span style="font-size:0.85rem; font-weight:400; color:#9E9070; margin-left:6px;">'
            f'{room_label}</span></div></div>'
            f'<div style="text-align:right; min-width:120px;">'
            f'<div style="font-size:1rem; font-weight:700; color:{floor_color};">📍 {row["교실위치"]}</div>'
            f'<div style="font-size:0.78rem; color:#9E9070; margin:2px 0 6px;">{row["층"]}층</div>'
            f'<span class="status-badge {badge_cls}">{badge_label}</span>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        with st.popover("✏️ 교실 위치 수정"):
            st.caption(f"{period}교시 · {row['과목']} 교실을 지도에 있는 장소 중에서 바로 바꿀 수 있어요.")
            options = _room_options()
            option_ids = [rid for rid, _ in options]
            cur_room = str(row["교실위치"])
            default_idx = option_ids.index(cur_room) if cur_room in option_ids else 0
            chosen_label = st.selectbox(
                "교실 선택", [label for _, label in options],
                index=default_idx, key=f"room_edit_{sel_day}_{period}",
            )
            new_room = option_ids[[label for _, label in options].index(chosen_label)]
            if st.button("저장", key=f"room_save_{sel_day}_{period}"):
                save_room_override(teacher, sel_day, period, new_room)
                load_timetable.clear()
                load_teacher_timetable.clear()
                st.success("✅ 교실 위치를 수정했어요. (지도·시간표에 바로 반영돼요)")


def _render_teacher_pivot(ttt, teacher, days):
    """교사 본인 주간 시간표 피벗 (전체 요일)."""
    st.markdown(f"### 📋 {teacher} 선생님 주간 시간표")
    sub = ttt[ttt["교사명"] == teacher]
    if sub.empty:
        st.info("등록된 수업 데이터가 없습니다.")
        return

    grid = {}
    for _, row in sub.iterrows():
        room_label = room_display_name(str(row["교실위치"]))
        content = f'{row["과목"]}\n{room_label}'
        grid.setdefault(int(row["교시"]), {})[row["요일"]] = (content, row["과목"])
    periods = sorted(grid)
    ordered_days = [d for d in days if any(d in g for g in grid.values())]

    rows_html = []
    for p in periods:
        cells = []
        for d in ordered_days:
            val = grid[p].get(d)
            if val:
                lines = val[0].split("\n")
                content = (
                    f'<b style="font-size:0.92rem;">{lines[0]}</b>'
                    + "".join(f'<br><span style="font-size:0.76rem;color:#8C8064;">{l}</span>'
                              for l in lines[1:])
                )
                color = subject_color(val[1]) or "#fff"
                cells.append(f'<td style="{_TD} background:{color};">{content}</td>')
            else:
                cells.append(f'<td style="{_TD} background:#F5F0E8; border-color:#EDE7DA; color:#C9BFA9;">—</td>')
        rows_html.append(f'<tr><th style="{_TH_ROW}">{p}교시</th>{"".join(cells)}</tr>')

    head = "".join(f'<th style="{_TH}">{day_label(d)}</th>' for d in ordered_days)
    st.markdown(
        f'<div style="overflow-x:auto;">'
        f'<table style="{_TABLE}">'
        f'<thead><tr><th style="{_TH}"></th>{head}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _render_pivot(df, sel_class, days):
    """전체 요일 피벗 테이블 (탐구 매핑 적용, 미선택 선택과목은 교사·교실 숨김)"""
    st.markdown(f"### 📋 {sel_class} 주간 시간표")
    sub = pd.concat(
        [get_personalized_timetable(df, sel_class, d) for d in days],
        ignore_index=True,
    ) if len(df) else df.copy()

    def _cell(row):
        if is_unselected_elective(row["과목"]):
            return f"{row['과목']}\n(선생님 미선택)"
        return f"{_subject_display(row['과목'], row['교사명'])}\n{row['교사명']}\n{row['교실위치']}"

    # 배포 서버(py3.14)에서 st.dataframe 의 네이티브 직렬화가 프로세스를
    # 죽이는 문제가 있어 순수 HTML 표로 렌더링한다.
    grid = {}   # {교시: {요일: (내용, 과목)}}
    for _, row in sub.iterrows():
        grid.setdefault(int(row["교시"]), {})[row["요일"]] = (_cell(row), row["과목"])
    periods = sorted(grid)
    ordered_days = [d for d in days if any(d in g for g in grid.values())]

    rows_html = []
    for p in periods:
        cells = []
        for d in ordered_days:
            val = grid[p].get(d)
            if val:
                lines = val[0].split("\n")
                content = (
                    f'<b style="font-size:0.92rem;">{lines[0]}</b>'
                    + "".join(f'<br><span style="font-size:0.76rem;color:#8C8064;">{l}</span>'
                              for l in lines[1:])
                )
                color = subject_color(val[1]) or "#fff"
                cells.append(f'<td style="{_TD} background:{color};">{content}</td>')
            else:
                cells.append(f'<td style="{_TD} background:#F5F0E8; border-color:#EDE7DA; color:#C9BFA9;">—</td>')
        rows_html.append(
            f'<tr><th style="{_TH_ROW}">{p}교시</th>{"".join(cells)}</tr>'
        )

    head = "".join(f'<th style="{_TH}">{day_label(d)}</th>' for d in ordered_days)
    st.markdown(
        f'<div style="overflow-x:auto;">'
        f'<table style="{_TABLE}">'
        f'<thead><tr><th style="{_TH}"></th>{head}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


# 둥근 카드형 표 스타일 (교시 카드와 톤 통일)
_TABLE  = "width:100%; border-collapse:separate; border-spacing:6px; background:transparent;"
_TH     = "padding:6px 4px; color:#9E9070; font-weight:700; font-size:0.82rem; border:none; background:transparent;"
_TH_ROW = ("padding:10px 6px; background:#F5F0E8; color:#7D6B2E; font-weight:900; font-size:0.85rem;"
           "border:1px solid #E0D8CC; border-radius:10px; min-width:52px;")
_TD     = ("padding:10px 8px; border:1px solid #E0D8CC; border-radius:10px; font-size:0.85rem;"
           "color:#3D3929; text-align:center; vertical-align:middle;")


def _render_grade_grid(df, grade, sel_day):
    """학년 전체 시간표: 한 요일의 반×교시 그리드 (s2h9 스타일)."""
    st.markdown(f"### 🏫 {grade}학년 전체 시간표 — {day_label(sel_day)}요일")
    sub = df[(df["반"].str.startswith(f"{grade}-")) & (df["요일"] == sel_day)]
    if sub.empty:
        st.info("해당 학년/요일 데이터가 없습니다.")
        return
    class_cols = sort_classes(sub["반"].unique().tolist())
    grid = {}   # {교시: {반: (과목, 교사)}}
    for _, row in sub.iterrows():
        grid.setdefault(int(row["교시"]), {})[row["반"]] = (row["과목"], row["교사명"])

    rows_html = []
    for p in sorted(grid):
        cells = []
        for c in class_cols:
            val = grid[p].get(c)
            if val:
                color = subject_color(val[0]) or "#fff"
                cells.append(
                    f'<td style="{_TD} background:{color};">'
                    f'<b>{val[0]}</b><br>'
                    f'<span style="font-size:0.75rem;color:#6B6350;">{val[1]}</span></td>'
                )
            else:
                cells.append(f'<td style="{_TD} background:#F5F0E8; color:#C9BFA9;">—</td>')
        rows_html.append(f'<tr><th style="{_TH_ROW}">{p}교시</th>{"".join(cells)}</tr>')

    head = "".join(f'<th style="{_TH}">{c.split("-")[1]}반</th>' for c in class_cols)
    st.markdown(
        f'<div style="overflow-x:auto;">'
        f'<table style="{_TABLE}">'
        f'<thead><tr><th style="{_TH}">교시</th>{head}</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody></table></div>',
        unsafe_allow_html=True,
    )
    st.caption("선택과목(탐구·교과)은 반 교실 기준 대표 선생님이 표시돼요.")


def show():
    """단독 페이지용 (현재는 홈에 통합되어 홈에서 show_body 를 사용)"""
    st.markdown("""
    <div class="main-header">
        <h1>📅 시간표 조회</h1>
        <p>반별 전체 시간표를 한눈에 확인하고, 현재·다음 교시를 실시간으로 파악하세요</p>
    </div>
    """, unsafe_allow_html=True)
    show_body()


def show_body():
    """시간표 본문 — 홈 페이지에서 호출"""
    df = load_timetable()
    now = datetime.now(KST)
    cur_day    = get_current_day(now)
    cur_period = get_current_period(now)
    nxt_period = get_next_period(now)

    classes = sort_classes(df["반"].unique().tolist())
    days    = ["월", "화", "수", "목", "금"]
    role    = get_role()
    my_class = st.session_state.get("my_class", classes[0])
    my_teacher_name = st.session_state.get("my_teacher_name", "")

    grades = sorted({int(c.split("-")[0]) for c in classes if "-" in c})

    # ── 교사: 본인 시간표 보기 ───────────────────────────────────────
    if role in ("teacher", "admin") and my_teacher_name:
        show_my_schedule = st.checkbox(
            f"👩‍🏫 내 시간표 보기 ({my_teacher_name} 선생님)", value=False,
            key="show_my_teacher_schedule",
        )
        if show_my_schedule:
            ttt = load_teacher_timetable()
            col_a, col_b = st.columns([2, 1])
            with col_a:
                default_day = cur_day if cur_day in days else "월"
                sel_day = st.selectbox("📆 요일 선택", days, index=days.index(default_day),
                                       format_func=day_label, key="teacher_sched_day")
            with col_b:
                st.markdown("<br>", unsafe_allow_html=True)
                show_all_t = st.checkbox("전체 요일", value=False, key="teacher_sched_all")

            if show_all_t:
                _render_teacher_pivot(ttt, my_teacher_name, days)
                return

            sub = ttt[(ttt["교사명"] == my_teacher_name) & (ttt["요일"] == sel_day)].sort_values("교시")
            st.markdown(f"### {my_teacher_name} 선생님 · {day_label(sel_day)}요일 시간표")
            _render_teacher_day_cards(my_teacher_name, sub, sel_day, cur_day, cur_period, nxt_period, now)
            return

    col1, col2, col3, col4 = st.columns([1.2, 1.2, 2, 1.4])
    if role == "student" and "my_class" in st.session_state:
        with col1:
            st.markdown(
                f'<div class="card" style="padding:10px 14px;">'
                f'<span style="color:#9E9070;font-size:0.78rem;">내 반</span><br>'
                f'<span style="font-weight:700;color:#3D3929;">{my_class}</span>'
                f'</div>', unsafe_allow_html=True)
        sel_class = my_class
        sel_grade = int(my_class.split("-")[0]) if "-" in my_class else grades[0]
    else:
        # 개인 설정에 저장된 내 반을 기본값으로, 학년/반 분리 선택
        my_grade = int(my_class.split("-")[0]) if my_class and "-" in my_class else grades[0]
        with col1:
            sel_grade = st.selectbox("🎓 학년", grades, index=grades.index(my_grade) if my_grade in grades else 0,
                                     format_func=lambda g: f"{g}학년")
        grade_classes = [c for c in classes if c.startswith(f"{sel_grade}-")]
        with col2:
            default_idx = grade_classes.index(my_class) if my_class in grade_classes else 0
            sel_class = st.selectbox("🏫 반", grade_classes, index=default_idx,
                                     format_func=lambda c: f"{c.split('-')[1]}반")
    with col3:
        default_day = cur_day if cur_day in days else "월"
        sel_day = st.selectbox("📆 요일 선택", days, index=days.index(default_day),
                               format_func=day_label)
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        show_all   = st.checkbox("전체 요일", value=False)
        show_grade = st.checkbox("학년 전체 시간표", value=False)

    if show_grade:
        _render_grade_grid(df, sel_grade, sel_day)
        return

    if show_all:
        _render_pivot(df, sel_class, days)
        return

    sub = get_personalized_timetable(df, sel_class, sel_day)

    if sub.empty:
        st.warning("해당 반/요일 데이터가 없습니다.")
        return

    st.markdown(f"### {sel_class} · {day_label(sel_day)}요일 시간표")

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
