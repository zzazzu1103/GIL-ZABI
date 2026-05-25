"""
pages/map_view.py  ―  사진 배경 + SVG 클릭 오버레이 방식
──────────────────────────────────────────────────────────
준비:
  프로젝트 루트에 assets/ 폴더를 만들고
  2층.jpg, 1층.jpg, 3층.jpg, 4층.jpg, 5층.jpg 를 넣어두세요.
  파일명은 FLOOR_IMAGE 딕셔너리에서 자유롭게 바꿀 수 있어요.
"""

import streamlit as st
import base64
import os
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

from utils.helpers import (
    load_timetable, get_current_period,
    get_next_period, get_current_day, PERIODS,
)

# ── 층별 이미지 파일 경로 ────────────────────────────────────────
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

FLOOR_IMAGE = {
    1: "1층.jpg",
    2: "2층.jpg",
    3: "3층.jpg",
    4: "4층.jpg",
    5: "5층.jpg",
}

# ── 이미지 원본 크기 (층별로 다를 경우 각각 지정) ─────────────────
# 현재 2층 기준: 1536 × 1024
FLOOR_IMAGE_SIZE = {
    1: (1536, 1024),
    2: (1536, 1024),
    3: (1536, 1024),
    4: (1536, 1024),
    5: (1536, 1024),
}

# ── 2층 교실 클릭 영역 정의 ─────────────────────────────────────
# (x, y, w, h) 는 원본 이미지(1536×1024) 기준 픽셀 좌표
# id 는 timetable.csv 의 교실위치 컬럼 값과 일치시키세요
FLOOR_ROOMS = {
    2: [
        # ── 위쪽 복도 (1-8 ~ 1-11) ─────────────────────────────
        {"id": "108", "name": "1-8반",       "x": 957,  "y": 168, "w": 101, "h": 130},
        {"id": "109", "name": "1-9반",       "x": 1058, "y": 168, "w": 101, "h": 130},
        {"id": "110", "name": "1-10반",      "x": 1159, "y": 168, "w": 101, "h": 130},
        {"id": "111", "name": "1-11반",      "x": 1260, "y": 168, "w": 116, "h": 130},
        # ── 사물함 영역 ────────────────────────────────────────
        {"id": "사물함",  "name": "사물함",  "x": 693,  "y": 168, "w": 175, "h": 100},
        # ── 화장실 (위) ────────────────────────────────────────
        {"id": "화장실(남)2층위", "name": "화장실(남)", "x": 868, "y": 168, "w":  47, "h": 130},
        {"id": "화장실(여)2층위", "name": "화장실(여)", "x": 915, "y": 168, "w":  42, "h": 130},
        # ── 사이언스 북클럽 ────────────────────────────────────
        {"id": "사이언스북클럽", "name": "사이언스\n북클럽", "x": 693, "y": 298, "w": 175, "h": 175},
        # ── Wee클래스 / 예술체육부 ─────────────────────────────
        {"id": "Wee클래스",   "name": "Wee클래스",  "x": 556, "y": 195, "w": 110, "h":  80},
        {"id": "예술체육부",  "name": "예술체육부", "x": 556, "y": 130, "w": 110, "h":  65},
        # ── 통합교육지원실 ────────────────────────────────────
        {"id": "통합교육지원실", "name": "통합교육\n지원실", "x": 556, "y": 395, "w": 110, "h": 100},
        # ── 아래쪽 복도 (1-5 ~ 1-7) ───────────────────────────
        {"id": "105", "name": "1-5반",       "x": 945,  "y": 615, "w": 102, "h": 140},
        {"id": "106", "name": "1-6반",       "x": 1047, "y": 615, "w": 102, "h": 140},
        {"id": "107", "name": "1-7반",       "x": 1149, "y": 615, "w": 110, "h": 140},
        # ── 교과교실3 ─────────────────────────────────────────
        {"id": "교과교실3",  "name": "교과교실3",  "x": 845,  "y": 615, "w": 100, "h": 140},
        # ── 진로활동실 ────────────────────────────────────────
        {"id": "진로활동실", "name": "진로활동실", "x": 734,  "y": 615, "w": 111, "h": 140},
        # ── 생각나눔터 (2곳) ──────────────────────────────────
        {"id": "생각나눔터1", "name": "생각\n나눔터", "x": 619, "y": 615, "w":  56, "h": 140},
        {"id": "생각나눔터2", "name": "생각\n나눔터", "x": 703, "y": 615, "w":  31, "h": 140},
        # ── 1학년 교무실 ──────────────────────────────────────
        {"id": "1학년교무실", "name": "1학년\n교무실", "x": 617, "y": 615, "w": 115, "h": 140},
        # ── 방송실 ───────────────────────────────────────────
        {"id": "방송실",    "name": "방송실",    "x": 543, "y": 615, "w":  73, "h": 140},
        # ── 대외협력부 ───────────────────────────────────────
        {"id": "대외협력부", "name": "대외협력부", "x": 448, "y": 615, "w":  95, "h": 140},
        # ── 본교무실 ─────────────────────────────────────────
        {"id": "본교무실",  "name": "본교무실",  "x": 291, "y": 615, "w": 157, "h": 140},
        # ── 학생안전부 ───────────────────────────────────────
        {"id": "학생안전부", "name": "학생안전부", "x": 214, "y": 615, "w":  77, "h": 140},
        # ── 체육관 ───────────────────────────────────────────
        {"id": "체육관",    "name": "체육관",    "x":  48,  "y": 128, "w": 490, "h": 390},
        # ── 화장실 (아래) ────────────────────────────────────
        {"id": "화장실(여)2층아래", "name": "화장실(여)", "x": 1001, "y": 493, "w":  53, "h":  75},
        {"id": "화장실(남)2층아래", "name": "화장실(남)", "x": 1054, "y": 493, "w":  53, "h":  75},
        # ── ELV ─────────────────────────────────────────────
        {"id": "ELV2층", "name": "ELV",   "x": 718,  "y": 490, "w":  60, "h":  75},
    ],
    # 다른 층은 사진 추가 후 여기에 계속 채우세요
    1: [], 3: [], 4: [], 5: [],
}

# ── 강조 색상 ────────────────────────────────────────────────────
HIGHLIGHT = {
    "current": {"fill": "rgba(217,119,6,0.30)",  "stroke": "#D97706", "sw": 3},
    "next":    {"fill": "rgba(5,150,105,0.25)",  "stroke": "#059669", "sw": 3},
    "normal":  {"fill": "rgba(125,107,46,0.08)", "stroke": "#7D6B2E", "sw": 1.5},
}


def _img_to_base64(floor: int) -> str | None:
    fname = FLOOR_IMAGE.get(floor)
    if not fname:
        return None
    path = os.path.join(ASSETS_DIR, fname)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = fname.rsplit(".", 1)[-1].lower()
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
    return f"data:{mime};base64,{data}"


def _build_overlay_html(
    floor: int,
    b64_img: str | None,
    highlight_map: dict,      # {room_id: "current"|"next"}
) -> str:
    """
    사진을 배경으로, 그 위에 SVG 클릭 오버레이를 올린 HTML 반환.
    이미지가 없으면 회색 placeholder 배경을 사용.
    """
    rooms = FLOOR_ROOMS.get(floor, [])
    iw, ih = FLOOR_IMAGE_SIZE.get(floor, (1536, 1024))

    # 뷰포트 너비 기준으로 비율 유지 (max 960px)
    bg_style = (
        f'background-image:url("{b64_img}"); background-size:contain;'
        f'background-repeat:no-repeat; background-position:top left;'
        if b64_img else
        'background:#E8E0D4;'
    )

    rects = []
    for rm in rooms:
        rid   = rm["id"]
        style = HIGHLIGHT.get(highlight_map.get(rid, "normal"), HIGHLIGHT["normal"])

        # 이름 줄바꿈 처리
        lines = rm["name"].split("\n")
        cy = rm["y"] + rm["h"] / 2 - (len(lines) - 1) * 9
        text_els = "".join(
            f'<tspan x="{rm["x"] + rm["w"]/2}" dy="{0 if i==0 else 18}">{l}</tspan>'
            for i, l in enumerate(lines)
        )

        # 강조 배지
        badge = ""
        if rid in highlight_map:
            emoji = "🔴" if highlight_map[rid] == "current" else "🟢"
            badge = (
                f'<text x="{rm["x"]+rm["w"]-10}" y="{rm["y"]+16}"'
                f' font-size="14" text-anchor="middle">{emoji}</text>'
            )

        rects.append(f"""
  <g class="room" data-id="{rid}" data-name="{rm['name'].replace(chr(10),' ')}"
     style="cursor:pointer;"
     onclick="selectRoom('{rid}', '{rm['name'].replace(chr(10),' ')}')">
    <rect x="{rm['x']}" y="{rm['y']}" width="{rm['w']}" height="{rm['h']}"
          rx="6"
          fill="{style['fill']}"
          stroke="{style['stroke']}"
          stroke-width="{style['sw']}"
          stroke-dasharray="{'none' if rid in highlight_map else '5,3'}"/>
    <text x="{rm['x'] + rm['w']/2}" y="{cy}"
          text-anchor="middle"
          font-size="13"
          font-weight="700"
          font-family="'Noto Sans KR',sans-serif"
          fill="{'#3D3929' if rid not in highlight_map else '#1a1a1a'}"
          pointer-events="none">
      {text_els}
    </text>
    {badge}
  </g>""")

    rooms_json = "[" + ",".join(
        f'{{"id":"{r["id"]}","name":"{r["name"].replace(chr(10)," ")}"}}'
        for r in rooms
    ) + "]"

    return f"""
<div id="map-wrap" style="position:relative; width:100%; max-width:960px;
     margin:0 auto; border-radius:12px; overflow:hidden;
     border:1px solid #E0D8CC; box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- 배경 이미지 -->
  <div style="width:100%; padding-top:{ih/iw*100:.3f}%;
       {bg_style}
       position:relative;">
  </div>

  <!-- SVG 오버레이 (absolute, 이미지와 완전히 겹침) -->
  <svg viewBox="0 0 {iw} {ih}"
       xmlns="http://www.w3.org/2000/svg"
       style="position:absolute;top:0;left:0;width:100%;height:100%;">
    {''.join(rects)}
  </svg>
</div>

<!-- 선택된 교실 정보 박스 -->
<div id="room-info" style="
     display:none; margin-top:12px; padding:14px 20px;
     background:#fff; border:1px solid #E0D8CC; border-left:4px solid #7D6B2E;
     border-radius:10px; font-family:'Noto Sans KR',sans-serif;">
  <div id="room-info-text" style="font-size:1rem; font-weight:700; color:#3D3929;"></div>
</div>

<script>
const _highlight = {highlight_map};
const _rooms     = {rooms_json};

function selectRoom(id, name) {{
  // 이전 선택 초기화
  document.querySelectorAll('.room rect').forEach(r => {{
    r.setAttribute('stroke-dasharray', '5,3');
    r.setAttribute('stroke-width', '1.5');
  }});

  // 선택된 방 강조
  const el = document.querySelector(`[data-id="${{id}}"] rect`);
  if (el) {{
    el.setAttribute('stroke-dasharray', 'none');
    el.setAttribute('stroke-width', '3');
    el.setAttribute('stroke', '#7D6B2E');
  }}

  // 정보 박스
  const box  = document.getElementById('room-info');
  const text = document.getElementById('room-info-text');
  box.style.display = 'block';

  const hl = _highlight[id];
  const badge = hl === 'current' ? ' 🔴 수업 중' : hl === 'next' ? ' 🟢 다음 교시' : '';
  text.innerHTML = `📍 ${{name}}${{badge}}`;
}}
</script>
"""


def show():
    st.markdown("""
    <div class="main-header">
        <h1>🗺️ 학교 지도</h1>
        <p>실제 평면도 위에서 교실을 클릭해 위치를 확인하세요</p>
    </div>
    """, unsafe_allow_html=True)

    timetable_df = load_timetable()
    now          = datetime.now(KST)
    cur_day      = get_current_day(now)
    cur_period   = get_current_period(now)
    nxt_period   = get_next_period(now)

    # ── 필터 ──────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1, 2, 2])
    with col1:
        sel_floor = st.selectbox("🏢 층 선택", [1, 2, 3, 4, 5],
                                  index=1,   # 2층을 기본값으로
                                  format_func=lambda x: f"{x}층")
    with col2:
        classes = sorted(timetable_df["반"].unique().tolist())
        sel_class = st.selectbox("🏫 내 반 (강조 표시용)", ["선택 안 함"] + classes)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        show_hl = st.checkbox("현재/다음 교시 교실 강조", value=True)

    # ── 강조 계산 ──────────────────────────────────────────────────
    highlight_map: dict[str, str] = {}
    if show_hl and sel_class != "선택 안 함" and cur_day:
        for period, label in [(cur_period, "current"), (nxt_period, "next")]:
            if period is None:
                continue
            row = timetable_df[
                (timetable_df["반"]   == sel_class) &
                (timetable_df["요일"] == cur_day) &
                (timetable_df["교시"] == period)
            ]
            if not row.empty:
                rid = str(row.iloc[0]["교실위치"])
                highlight_map[rid] = label

    # ── 이미지 로드 ────────────────────────────────────────────────
    b64 = _img_to_base64(sel_floor)
    if b64 is None:
        if sel_floor == 2:
            st.warning(
                "📂 `assets/2층.jpg` 파일이 없습니다.\n\n"
                "프로젝트 루트에 `assets/` 폴더를 만들고 평면도 사진을 넣어주세요."
            )
        else:
            st.info(f"📂 `assets/{FLOOR_IMAGE.get(sel_floor, '')}` 파일을 추가하면 지도가 표시돼요.")

    # ── 지도 렌더링 ────────────────────────────────────────────────
    st.markdown(f"#### {sel_floor}층 평면도")
    html = _build_overlay_html(sel_floor, b64, highlight_map)
    st.components.v1.html(html, height=600, scrolling=False)

    # ── 현재 위치 정보 패널 ────────────────────────────────────────
    if highlight_map and sel_class != "선택 안 함":
        st.markdown("#### 📍 현재 위치 정보")
        for rid, status in highlight_map.items():
            period = cur_period if status == "current" else nxt_period
            s, e   = PERIODS.get(period, (None, None))
            time_str = f"{s.strftime('%H:%M')}~{e.strftime('%H:%M')}" if s else ""

            row = timetable_df[
                (timetable_df["반"]   == sel_class) &
                (timetable_df["요일"] == cur_day) &
                (timetable_df["교시"] == period)
            ]
            subject = row.iloc[0]["과목"]   if not row.empty else "-"
            teacher = row.iloc[0]["교사명"] if not row.empty else "-"
            floor   = row.iloc[0]["층"]     if not row.empty else sel_floor

            card_cls   = "card-current" if status == "current" else "card-next"
            badge_cls  = "badge-current" if status == "current" else "badge-next"
            badge_label= "🔴 수업 중" if status == "current" else "🟢 다음 교시"

            st.markdown(f"""
            <div class="card {card_cls}">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                  <span class="status-badge {badge_cls}">{badge_label}</span>
                  <div style="margin-top:8px;font-size:1.1rem;font-weight:700;">
                    {period}교시 · {subject}
                  </div>
                  <div style="color:#9E9070;font-size:0.85rem;">
                    {teacher} 선생님 · {time_str}
                  </div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:1.4rem;font-weight:900;color:#7D6B2E;">
                    📍 {rid}
                  </div>
                  <div style="color:#9E9070;font-size:0.78rem;">{floor}층</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── 범례 ──────────────────────────────────────────────────────
    st.markdown("---")
    col_l = st.columns(4)
    legends = [
        ("#7D6B2E", "교실 / 공간"),
        ("#D97706", "🔴 수업 중"),
        ("#059669", "🟢 다음 교시"),
        ("#9E9070", "클릭하면 이름 표시"),
    ]
    for col, (color, label) in zip(col_l, legends):
        with col:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;font-size:0.8rem;">'
                f'<div style="width:12px;height:12px;border-radius:2px;'
                f'background:{color};flex-shrink:0;"></div>'
                f'<span style="color:#9E9070;">{label}</span></div>',
                unsafe_allow_html=True,
            )