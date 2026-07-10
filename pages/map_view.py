"""
pages/map_view.py ― 순수 SVG 벡터 평면도 (1~5층)
──────────────────────────────────────────────────────────
utils/floorplan.py 에 정의된 벽·복도·교실 데이터를 그대로 그립니다.
내 반을 선택하면 현재 진행 중인 수업(🔴)과 다음 교시(🟢) 교실이 강조됩니다.
"""

import streamlit as st
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

from utils.helpers import (
    load_timetable, get_current_period, get_next_period,
    get_current_day, get_personalized_timetable, PERIODS, sort_classes,
    is_unselected_elective,
)
from utils.floorplan import render_map, find_room_floor, room_display_name


def _class_highlight_entries(df, sel_class, cur_day, cur_period, nxt_period):
    """선택한 반의 현재/다음 교시 정보를 [(status, period, row)] 로 반환."""
    entries = []
    if not cur_day or sel_class == "선택 안 함":
        return entries
    sub = get_personalized_timetable(df, sel_class, cur_day)
    if sub.empty:
        return entries
    for period, status in ((cur_period, "current"), (nxt_period, "next")):
        if period is None:
            continue
        row = sub[sub["교시"] == period]
        if row.empty:
            continue
        r = row.iloc[0]
        rid = str(r["교실위치"])
        unselected = is_unselected_elective(r["과목"])
        entries.append({
            "status": status, "period": period,
            "rid": None if unselected else rid,
            "subject": r["과목"],
            "teacher": None if unselected else r["교사명"],
            "floor": None if unselected else find_room_floor(rid, int(r["층"])),
            "unselected": unselected,
        })
    return entries


def show():
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 학교 지도</h1>
        <p>1~5층 평면도에서 교실을 클릭해 위치를 확인하세요</p>
    </div>
    """, unsafe_allow_html=True)

    timetable_df = load_timetable()
    now          = datetime.now(KST)
    cur_day      = get_current_day(now)
    cur_period   = get_current_period(now)
    nxt_period   = get_next_period(now)

    # ── 필터 (반 → 층 순서: 반을 고르면 해당 수업 층으로 자동 이동) ──
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        classes = sort_classes(timetable_df["반"].unique().tolist())
        my_class = st.session_state.get("my_class")
        options = ["선택 안 함"] + classes
        default_idx = options.index(my_class) if my_class in options else 0
        sel_class = st.selectbox("🏫 내 반 (강조 표시용)", options, index=default_idx)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_hl = st.checkbox("현재/다음 교시 교실 강조", value=True)

    entries = _class_highlight_entries(timetable_df, sel_class, cur_day,
                                       cur_period, nxt_period) if show_hl else []

    # 반이 바뀌면 현재(없으면 다음) 수업이 있는 층으로 자동 전환
    if st.session_state.get("_map_last_class") != sel_class:
        st.session_state["_map_last_class"] = sel_class
        located = [e for e in entries if e["floor"] is not None]
        if located:
            st.session_state["map_floor_sel"] = located[0]["floor"]

    with col2:
        st.session_state.setdefault("map_floor_sel", 2)
        sel_floor = st.selectbox("🏢 층 선택", [1, 2, 3, 4, 5],
                                 format_func=lambda x: f"{x}층",
                                 key="map_floor_sel")

    # 같은 교실이 현재+다음 둘 다면 '현재'가 우선하도록 next → current 순으로 기록
    highlight_map = {}
    for e in sorted(entries, key=lambda e: e["status"] != "next"):
        if e["rid"] is not None and e["floor"] == sel_floor:
            highlight_map[e["rid"]] = e["status"]

    # ── 지도 렌더링 ────────────────────────────────────────────────
    st.markdown(f"#### {sel_floor}층 평면도")
    render_map(sel_floor, highlight_map)

    # ── 현재/다음 수업 정보 패널 ──────────────────────────────────
    if sel_class != "선택 안 함":
        if not cur_day:
            st.info("오늘은 수업이 없는 날이에요.")
        elif entries:
            st.markdown("#### 📍 내 수업 위치")
            if cur_period is None:
                st.caption("☕ 지금은 쉬는 시간이에요 — 다음 교시 위치를 확인하세요.")
            for e in entries:
                s, t = PERIODS.get(e["period"], (None, None))
                time_str = f"{s.strftime('%H:%M')}~{t.strftime('%H:%M')}" if s else ""
                is_cur = e["status"] == "current"
                card_cls, badge_cls = ("card-current", "badge-current") if is_cur else ("card-next", "badge-next")
                badge_label = "🔴 수업 중" if is_cur else "🟢 다음 교시"

                if e["unselected"]:
                    st.markdown(f"""
                    <div class="card {card_cls}">
                      <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div>
                          <span class="status-badge {badge_cls}">{badge_label}</span>
                          <div style="margin-top:8px;font-size:1.1rem;font-weight:700;">
                            {e['period']}교시 · {e['subject']} <span style="font-size:0.8rem;color:#9E9070;">선택과목</span>
                          </div>
                          <div style="color:#9E9070;font-size:0.85rem;">{time_str}</div>
                        </div>
                        <div style="text-align:right;">
                          <div style="font-size:0.95rem;font-weight:700;color:#B45309;">❓ 선생님 미선택</div>
                          <div style="color:#9E9070;font-size:0.75rem;">개인 설정에서 선택하면<br>위치가 표시돼요</div>
                        </div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    continue
                floor_note = "" if e["floor"] == sel_floor else \
                    f'<span style="color:#B45309;font-size:0.75rem;"> · 지도에서 {e["floor"]}층을 선택하세요</span>'

                st.markdown(f"""
                <div class="card {card_cls}">
                  <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                      <span class="status-badge {badge_cls}">{badge_label}</span>
                      <div style="margin-top:8px;font-size:1.1rem;font-weight:700;">
                        {e['period']}교시 · {e['subject']}
                      </div>
                      <div style="color:#9E9070;font-size:0.85rem;">
                        {e['teacher']} 선생님 · {time_str}
                      </div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:1.3rem;font-weight:900;color:#7D6B2E;">
                        📍 {room_display_name(e['rid'])}
                      </div>
                      <div style="color:#9E9070;font-size:0.78rem;">{e['floor']}층{floor_note}</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("지금 시간에는 표시할 수업이 없어요.")

    # ── 범례 ──────────────────────────────────────────────────────
    st.markdown("---")
    col_l = st.columns(4)
    legends = [
        ("#FFFFFF", "일반 교실"),
        ("#D97706", "🔴 현재 수업"),
        ("#059669", "🟢 다음 교시"),
        ("#EFE9DC", "복도"),
    ]
    for col, (color, label) in zip(col_l, legends):
        with col:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;font-size:0.8rem;">'
                f'<div style="width:12px;height:12px;border-radius:2px;border:1px solid #B4A886;'
                f'background:{color};flex-shrink:0;"></div>'
                f'<span style="color:#9E9070;">{label}</span></div>',
                unsafe_allow_html=True,
            )
