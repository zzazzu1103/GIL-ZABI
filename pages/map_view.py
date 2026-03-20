import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timezone, timedelta
KST = timezone(timedelta(hours=9))
import json, sys, os
from utils.helpers import (
    load_rooms, load_timetable, get_current_period,
    get_next_period, get_current_day
)

# ── 층별 교실 레이아웃 정의 ─────────────────────────────────────────────────
FLOOR_LAYOUTS = {
    1: [
        {"id":"1-101",  "name":"1-1반",   "x":40,  "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"1-102",  "name":"1-2반",   "x":170, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"1-103",  "name":"1-3반",   "x":300, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"체육관", "name":"체육관",  "x":430, "y":80,  "w":160, "h":120,"type":"special"},
        {"id":"1-교무실","name":"1학년부\n교무실","x":40,"y":200,"w":160,"h":65,"type":"office"},
        {"id":"화장실1","name":"화장실",  "x":620, "y":100, "w":60,  "h":60, "type":"restroom"},
        {"id":"현관",   "name":"현관",    "x":250, "y":300, "w":160, "h":60, "type":"entrance"},
    ],
    2: [
        {"id":"2-201",  "name":"2-1반",   "x":40,  "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"2-202",  "name":"2-2반",   "x":170, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"2-203",  "name":"2-3반",   "x":300, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"미술실", "name":"미술실",  "x":430, "y":80,  "w":140, "h":120,"type":"special"},
        {"id":"2-교무실","name":"수학\n교무실","x":40,"y":200,"w":160,"h":65,"type":"office"},
        {"id":"화장실2","name":"화장실",  "x":620, "y":100, "w":60,  "h":60, "type":"restroom"},
        {"id":"계단2",  "name":"계단",    "x":590, "y":180, "w":80,  "h":60, "type":"stair"},
    ],
    3: [
        {"id":"3-301",  "name":"3-1반",   "x":40,  "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"3-302",  "name":"3-2반",   "x":170, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"3-303",  "name":"3-3반",   "x":300, "y":100, "w":110, "h":75, "type":"classroom"},
        {"id":"음악실", "name":"음악실",  "x":430, "y":80,  "w":140, "h":120,"type":"special"},
        {"id":"3-교무실","name":"영어·예술\n교무실","x":40,"y":200,"w":160,"h":65,"type":"office"},
        {"id":"화장실3","name":"화장실",  "x":620, "y":100, "w":60,  "h":60, "type":"restroom"},
        {"id":"계단3",  "name":"계단",    "x":590, "y":180, "w":80,  "h":60, "type":"stair"},
    ],
    4: [
        {"id":"4-401",  "name":"과학실 A\n(물리)",  "x":40,  "y":80,  "w":130, "h":90, "type":"lab"},
        {"id":"4-402",  "name":"과학실 B\n(화학)",  "x":190, "y":80,  "w":130, "h":90, "type":"lab"},
        {"id":"4-403",  "name":"과학실 C\n(생명)",  "x":340, "y":80,  "w":130, "h":90, "type":"lab"},
        {"id":"4-교무실","name":"과학\n교무실","x":490,"y":80,"w":120,"h":90,"type":"office"},
        {"id":"준비실", "name":"준비실",  "x":40,  "y":195, "w":200, "h":60, "type":"storage"},
        {"id":"화장실4","name":"화장실",  "x":620, "y":100, "w":60,  "h":60, "type":"restroom"},
    ],
    5: [
        {"id":"도서관", "name":"도서관",  "x":40,  "y":80,  "w":280, "h":140,"type":"special"},
        {"id":"상담실", "name":"진로\n상담실","x":340,"y":80,  "w":120, "h":120,"type":"special"},
        {"id":"5-교무실","name":"교장·\n교감실","x":480,"y":80, "w":130,"h":120,"type":"office"},
        {"id":"회의실", "name":"회의실",  "x":40,  "y":240, "w":160, "h":70,  "type":"office"},
        {"id":"화장실5","name":"화장실",  "x":620, "y":100, "w":60,  "h":60, "type":"restroom"},
    ],
}

TYPE_COLORS = {
    "classroom": {"fill":"#1A2535","stroke":"#4ECDC4","text":"#E6EDF3"},
    "special":   {"fill":"#1A2030","stroke":"#FF6B35","text":"#E6EDF3"},
    "lab":       {"fill":"#1A2530","stroke":"#BC8CFF","text":"#E6EDF3"},
    "office":    {"fill":"#1A2020","stroke":"#3FB950","text":"#E6EDF3"},
    "restroom":  {"fill":"#141920","stroke":"#58A6FF","text":"#8B949E"},
    "stair":     {"fill":"#141920","stroke":"#8B949E","text":"#8B949E"},
    "storage":   {"fill":"#141920","stroke":"#FFA657","text":"#8B949E"},
    "entrance":  {"fill":"#1A2530","stroke":"#FFDDA6","text":"#E6EDF3"},
}

HIGHLIGHT_COLORS = {
    "current": "#FF6B35",
    "next":    "#4ECDC4",
}


def build_svg(floor: int, highlight_rooms: dict, room_info_map: dict) -> str:
    """SVG 평면도 생성. highlight_rooms = {교실코드: 'current'|'next'}"""
    rooms = FLOOR_LAYOUTS.get(floor, [])
    W, H = 720, 400

    parts = [f"""<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"
        style="width:100%;height:auto;background:#0D1117;border-radius:12px;border:1px solid #30363D;">
    <defs>
        <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
            <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
    </defs>
    <!-- 복도 -->
    <rect x="0" y="60" width="{W}" height="20" fill="#0F1923" opacity="0.8"/>
    <text x="10" y="75" font-size="11" fill="#8B949E" font-family="sans-serif">{floor}층 복도</text>
    <!-- 외벽 -->
    <rect x="5" y="5" width="{W-10}" height="{H-10}"
          fill="none" stroke="#30363D" stroke-width="2" rx="8"/>
    """]

    for rm in rooms:
        rid   = rm["id"]
        rtype = rm.get("type","classroom")
        colors = TYPE_COLORS.get(rtype, TYPE_COLORS["classroom"])

        fill   = colors["fill"]
        stroke = colors["stroke"]
        sw     = 1.5
        glow_filter = ""

        if rid in highlight_rooms:
            kind   = highlight_rooms[rid]
            stroke = HIGHLIGHT_COLORS[kind]
            sw     = 3
            fill   = f"{'rgba(255,107,53,0.18)' if kind=='current' else 'rgba(78,205,196,0.18)'}"
            glow_filter = 'filter="url(#glow)"'

        name_lines = rm["name"].replace("\n","&#10;")
        lines = rm["name"].split("\n")
        text_y_base = rm["y"] + rm["h"] // 2 - (len(lines) - 1) * 7
        text_parts = "".join(
            f'<tspan x="{rm["x"]+rm["w"]//2}" dy="{0 if i==0 else 14}">{l}</tspan>'
            for i, l in enumerate(lines)
        )

        # 상태 아이콘
        icon = ""
        if rid in highlight_rooms:
            emoji = "🔴" if highlight_rooms[rid] == "current" else "🟢"
            icon = f'<text x="{rm["x"]+rm["w"]-16}" y="{rm["y"]+16}" font-size="12" text-anchor="middle">{emoji}</text>'

        parts.append(f"""
    <g class="room" id="room-{rid}" style="cursor:pointer;" {glow_filter}>
        <rect x="{rm['x']}" y="{rm['y']}" width="{rm['w']}" height="{rm['h']}"
              rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>
        <text x="{rm['x']+rm['w']//2}" y="{text_y_base}"
              text-anchor="middle" font-size="11" fill="{colors['text']}"
              font-family="'Noto Sans KR',sans-serif" font-weight="600">
            {text_parts}
        </text>
        {icon}
    </g>""")

    # 층 표시
    parts.append(f"""
    <text x="{W-20}" y="{H-10}" text-anchor="end"
          font-size="11" fill="#8B949E" font-family="sans-serif">{floor}F</text>
    </svg>""")

    return "".join(parts)


def show():
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 학교 지도</h1>
        <p>1~5층 평면도를 탐색하고 각 교실 정보를 확인하세요</p>
    </div>
    """, unsafe_allow_html=True)

    rooms_df    = load_rooms()
    timetable_df = load_timetable()
    now          = datetime.now(KST)
    cur_day      = get_current_day(now)
    cur_period   = get_current_period(now)
    nxt_period   = get_next_period(now)

    # ── 필터 ─────────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        sel_floor = st.selectbox("🏢 층 선택", [1,2,3,4,5], format_func=lambda x: f"{x}층")
    with col2:
        classes = sorted(timetable_df["반"].unique().tolist())
        sel_class = st.selectbox("🏫 내 반 (강조 표시용)", ["선택 안 함"] + classes)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_highlight = st.checkbox("현재/다음 교시 교실 강조", value=True)

    # ── 강조할 교실 계산 ──────────────────────────────────────────────────────
    highlight = {}
    if show_highlight and sel_class != "선택 안 함" and cur_day:
        for period, label in [(cur_period,"current"),(nxt_period,"next")]:
            if period is None:
                continue
            row = timetable_df[
                (timetable_df["반"] == sel_class) &
                (timetable_df["요일"] == cur_day) &
                (timetable_df["교시"] == period)
            ]
            if not row.empty:
                room_id = row.iloc[0]["교실위치"]
                highlight[room_id] = label

    # ── SVG 지도 렌더링 ───────────────────────────────────────────────────────
    room_info_map = {r["id"]: r for r in FLOOR_LAYOUTS.get(sel_floor, [])}
    svg_code = build_svg(sel_floor, highlight, room_info_map)

    st.markdown(f"#### {sel_floor}층 평면도")
    st.markdown(svg_code, unsafe_allow_html=True)

    # ── 범례 ─────────────────────────────────────────────────────────────────
    cols = st.columns(6)
    legends = [
        ("#4ECDC4","일반 교실"),
        ("#FF6B35","특별실"),
        ("#BC8CFF","과학실"),
        ("#3FB950","교무실"),
        ("#FF6B35","🔴 수업 중"),
        ("#4ECDC4","🟢 다음 교시"),
    ]
    for col, (color, label) in zip(cols, legends):
        with col:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;font-size:0.8rem;">'
                f'<div style="width:12px;height:12px;border-radius:2px;'
                f'background:{color};flex-shrink:0;"></div>'
                f'<span style="color:#8B949E;">{label}</span></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── 강조 교실 정보 패널 ────────────────────────────────────────────────────
    if highlight:
        st.markdown("#### 📍 현재 위치 정보")
        for room_id, status in highlight.items():
            period = cur_period if status == "current" else nxt_period
            s, e = (None, None)
            from utils.helpers import PERIODS
            if period:
                s, e = PERIODS.get(period, (None, None))
            time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

            row = timetable_df[
                (timetable_df["반"] == sel_class) &
                (timetable_df["요일"] == cur_day) &
                (timetable_df["교시"] == period)
            ]
            subject = row.iloc[0]["과목"] if not row.empty else "-"
            teacher = row.iloc[0]["교사명"] if not row.empty else "-"

            card_cls = "card-current" if status == "current" else "card-next"
            badge_label = "🔴 수업 중" if status == "current" else "🟢 다음 교시"
            badge_cls   = "badge-current" if status == "current" else "badge-next"

            st.markdown(f"""
            <div class="card {card_cls}">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span class="status-badge {badge_cls}">{badge_label}</span>
                        <div style="margin-top:8px;font-size:1.1rem;font-weight:700;">
                            {period}교시 · {subject}
                        </div>
                        <div style="color:#8B949E;font-size:0.85rem;">{teacher} 선생님 · {time_str}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.4rem;font-weight:900;color:#4ECDC4;">📍 {room_id}</div>
                        <div style="color:#8B949E;font-size:0.8rem;">{sel_floor}층</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ── 이 층 교실 목록 ────────────────────────────────────────────────────────
    st.markdown(f"#### {sel_floor}층 공간 목록")
    floor_rooms = FLOOR_LAYOUTS.get(sel_floor, [])
    type_labels = {
        "classroom":"일반 교실","special":"특별실","lab":"과학실",
        "office":"교무실","restroom":"화장실","stair":"계단",
        "storage":"창고/준비실","entrance":"현관",
    }
    type_colors = {
        "classroom":"#4ECDC4","special":"#FF6B35","lab":"#BC8CFF",
        "office":"#3FB950","restroom":"#58A6FF","stair":"#8B949E",
        "storage":"#FFA657","entrance":"#FFDDA6",
    }

    cols = st.columns(3)
    for i, rm in enumerate(floor_rooms):
        rtype = rm.get("type","classroom")
        color = type_colors.get(rtype,"#8B949E")
        label = type_labels.get(rtype,"기타")
        with cols[i % 3]:
            st.markdown(f"""
            <div class="card" style="padding:14px;">
                <div style="font-size:0.7rem;color:{color};font-weight:700;
                            letter-spacing:0.05em;">{label.upper()}</div>
                <div style="font-size:1rem;font-weight:700;margin:4px 0 2px;">
                    {rm['name'].replace(chr(10),' ')}
                </div>
                <div style="font-size:0.78rem;color:#8B949E;">{rm['id']}</div>
            </div>
            """, unsafe_allow_html=True)
