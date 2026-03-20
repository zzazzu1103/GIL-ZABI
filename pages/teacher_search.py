import streamlit as st
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
from utils.helpers import (
    load_timetable, load_teachers, get_current_period,
    get_next_period, get_current_day, PERIODS, get_teacher_location
)

def show():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 선생님 찾기</h1>
        <p>선생님 이름을 검색하면 현재 어디 계신지 바로 알 수 있어요</p>
    </div>
    """, unsafe_allow_html=True)

    timetable_df = load_timetable()
    teachers_df  = load_teachers()
    now          = datetime.now(KST)
    cur_day      = get_current_day(now)
    cur_period   = get_current_period(now)
    nxt_period   = get_next_period(now)

    teacher_names = sorted(teachers_df["교사명"].tolist())

    # ── 검색 UI ──────────────────────────────────────────────────────────────
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 선생님 이름 검색", placeholder="예: 김영희, 이철수...")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        use_dropdown = st.checkbox("목록에서 선택", value=False)

    if use_dropdown:
        selected_teacher = st.selectbox("선생님 선택", teacher_names)
    else:
        # 검색어 기반 필터
        if query:
            matches = [n for n in teacher_names if query in n]
            if not matches:
                st.warning(f"'{query}'와 일치하는 선생님이 없습니다.")
                return
            selected_teacher = st.selectbox("검색 결과", matches)
        else:
            st.markdown("""
            <div class="card" style="text-align:center; padding:40px;">
                <div style="font-size:3rem; margin-bottom:12px;">🔍</div>
                <div style="font-size:1.1rem; font-weight:600; color:#8B949E;">
                    선생님 이름을 입력하세요
                </div>
                <div style="font-size:0.85rem; color:#4A5568; margin-top:6px;">
                    성함 일부만 입력해도 검색됩니다
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 전체 선생님 목록
            st.markdown("### 👩‍🏫 전체 선생님 목록")
            cols = st.columns(2)
            for i, (_, t) in enumerate(teachers_df.iterrows()):
                with cols[i % 2]:
                    st.markdown(f"""
                    <div class="card" style="padding:14px;">
                        <div style="font-size:1rem; font-weight:700;">{t['교사명']} 선생님</div>
                        <div style="color:#8B949E; font-size:0.85rem; margin-top:4px;">
                            {t['담당과목']} · {t['교무실']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
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
            <div style="color:#8B949E; font-size:0.8rem; margin-bottom:8px;">기본 정보</div>
            <div style="font-size:1rem; font-weight:600;">담당 과목</div>
            <div style="font-size:1.4rem; font-weight:900; color:#4ECDC4; margin:4px 0 12px;">{ti['담당과목']}</div>
            <div style="font-size:1rem; font-weight:600;">교무실</div>
            <div style="font-size:1rem; color:#E6EDF3; margin-top:4px;">
                📍 {ti['교무실위치']} ({ti['층']}층)
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        # 현재 위치
        if cur_day and cur_period:
            loc = get_teacher_location(timetable_df, teachers_df,
                                       selected_teacher, cur_day, cur_period)
            s, e = PERIODS.get(cur_period, (None, None))
            time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

            status_color = "#FF6B35" if loc["상태"] == "수업중" else "#3FB950"
            status_icon  = "🔴" if loc["상태"] == "수업중" else "🟢"
            badge_cls    = "badge-current" if loc["상태"] == "수업중" else "badge-next"

            st.markdown(f"""
            <div class="card card-current">
                <div style="color:#8B949E; font-size:0.8rem; margin-bottom:8px;">
                    지금 ({cur_period}교시 · {time_str})
                </div>
                <span class="status-badge {badge_cls}">
                    {status_icon} {loc['상태']}
                </span>
                <div style="font-size:1.4rem; font-weight:900; color:{status_color}; margin:10px 0 4px;">
                    📍 {loc['교실']}
                </div>
                <div style="color:#8B949E; font-size:0.85rem;">{loc['층']}층</div>
                {"<div style='color:#E6EDF3; margin-top:6px;'>"+loc['과목']+" · "+loc['반']+"</div>" if loc['상태']=='수업중' else ""}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card">
                <div style="color:#8B949E; font-size:0.85rem;">
                    현재 수업 시간이 아닙니다.<br>교무실에서 찾으세요.
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── 오늘 하루 일정 ─────────────────────────────────────────────────────────
    if cur_day:
        st.markdown(f"### 📅 {cur_day}요일 수업 일정")

        day_schedule = timetable_df[
            (timetable_df["교사명"] == selected_teacher) &
            (timetable_df["요일"] == cur_day)
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

                st.markdown(f"""
                <div class="card {card_cls}">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div style="color:#8B949E;font-size:0.78rem;">{period}교시 · {time_str}</div>
                            <div style="font-size:1.05rem;font-weight:700;margin-top:4px;">
                                {row['과목']} — {row['반']}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:1rem;font-weight:700;color:#4ECDC4;">
                                📍 {row['교실위치']}
                            </div>
                            <div style="color:#8B949E;font-size:0.78rem;">{row['층']}층</div>
                            {badge_html}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ── 주간 전체 일정 ─────────────────────────────────────────────────────────
    with st.expander("📋 주간 전체 시간표 보기"):
        days = ["월","화","수","목","금"]
        week_data = timetable_df[timetable_df["교사명"] == selected_teacher]

        if week_data.empty:
            st.info("등록된 수업 데이터가 없습니다.")
        else:
            for day in days:
                day_df = week_data[week_data["요일"] == day].sort_values("교시")
                if not day_df.empty:
                    st.markdown(f"**{day}요일**")
                    for _, r in day_df.iterrows():
                        st.markdown(
                            f"　{int(r['교시'])}교시 · {r['과목']} · {r['반']} · 📍{r['교실위치']}({r['층']}층)"
                        )
