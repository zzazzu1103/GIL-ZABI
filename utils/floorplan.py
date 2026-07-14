"""
utils/floorplan.py ― 순수 SVG 벡터 학교 평면도 (1~5층)
──────────────────────────────────────────────────────────
사진 없이 벽·복도·교실을 직접 그립니다.
- FLOOR_ROOMS   : 층별 방 목록 (id / name / 좌표 / 종류)
- FLOOR_CORRIDORS: 층별 복도 영역
- ROOM_FLOOR    : 교실 id → 실제 층
- render_map()  : Streamlit 컴포넌트로 지도 렌더링

id 는 timetable.csv 의 교실위치, teachers.csv 의 교무실위치 값과 일치합니다.
"""

import json
import streamlit as st

# ── 방 종류별 기본 채움색 ────────────────────────────────────────
TYPE_FILL = {
    "class":    "#FFFFFF",   # 일반 교실
    "office":   "#F6EFDC",   # 교무실
    "special":  "#F2EDE2",   # 특별실
    "facility": "#E9E3D5",   # 화장실·계단·ELV 등
    "outdoor":  "#E3EDDC",   # 학교숲·하늘공원
}

WALL_COLOR     = "#4A4435"
CORRIDOR_FILL  = "#EFE9DC"
CORRIDOR_LINE  = "#CFC5AE"

# 강조 스타일
HIGHLIGHT = {
    "current": {"fill": "rgba(217,119,6,0.35)",  "stroke": "#D97706", "sw": 4, "emoji": "🔴"},
    "next":    {"fill": "rgba(5,150,105,0.30)",  "stroke": "#059669", "sw": 4, "emoji": "🟢"},
    "teacher": {"fill": "rgba(37,99,235,0.30)",  "stroke": "#2563EB", "sw": 4, "emoji": "📍"},
}


def _r(rid, name, x, y, w, h, t="special", fs=None):
    return {"id": rid, "name": name, "x": x, "y": y, "w": w, "h": h,
            "type": t, "fs": fs or (10 if w < 80 or h < 60 else 13)}


# ── 2~5층 공통 뼈대 (아래쪽 날개) ────────────────────────────────
_END_Y, _END_H = 590, 70     # 양끝 계단/화장실 블록
_ROW_Y, _ROW_H = 710, 150    # 교실 줄


def _left_end(f):
    return [
        _r(f"계단L{f}",   "계단",          60, _END_Y,  55, _END_H, "facility"),
        _r(f"세치실L{f}", "세치실",       115, _END_Y,  55, _END_H, "facility"),
        _r(f"화장실남L{f}", "화장실\n(남)", 170, _END_Y,  73, _END_H, "facility"),
        _r(f"화장실여L{f}", "화장실\n(여)", 243, _END_Y,  77, _END_H, "facility"),
    ]


def _right_end(f):
    return [
        _r(f"화장실여R{f}", "화장실\n(여)", 1160, _END_Y, 73, _END_H, "facility"),
        _r(f"화장실남R{f}", "화장실\n(남)", 1233, _END_Y, 73, _END_H, "facility"),
        _r(f"세치실R{f}", "세치실",        1306, _END_Y, 55, _END_H, "facility"),
        _r(f"계단R{f}",   "계단",          1361, _END_Y, 59, _END_H, "facility"),
    ]


def _nanum(f, side, x):
    return _r(f"생각나눔터{side}{f}", "생각\n나눔터", x, _ROW_Y + 5, 35, _ROW_H - 10, "facility", fs=9)


def _class4(specs):
    """왼쪽 교실 4칸: [(id, name), ...] → x 60~510"""
    xs = [(60, 113), (173, 113), (286, 112), (398, 112)]
    return [_r(rid, name, x, _ROW_Y, w, _ROW_H, "class")
            for (rid, name), (x, w) in zip(specs, xs)]


def _class5(specs):
    """오른쪽 5칸(특별실 1 + 교실 4): x 816~1421"""
    out = []
    for i, (rid, name, t) in enumerate(specs):
        out.append(_r(rid, name, 816 + i * 121, _ROW_Y, 121, _ROW_H, t))
    return out


# ── 층별 방 정의 ────────────────────────────────────────────────
FLOOR_ROOMS = {
    # ═══ 1층 ═══
    1: [
        _r("조리실", "조리실", 230, 225, 215, 275, "special", fs=18),
        _r("식당",   "식당",   445, 225, 215, 275, "special", fs=18),
        _r("계단L1",  "계단",        380, 585, 40, 65, "facility"),
        _r("화장실남L1", "화장실\n(남)", 445, 585, 57, 65, "facility"),
        _r("화장실여L1", "화장실\n(여)", 502, 585, 56, 65, "facility"),
        _r("도서관", "도서관\n(지혜의 숲)", 380, 700, 280, 95, "special", fs=15),
        _r("드림스테이지", "드림\n스테이지", 815, 260, 125, 285, "special"),
        _r("ELV1", "ELV", 815, 560, 60, 60, "facility"),
        _r("예술교과실", "예술\n교과실", 965, 260, 175, 105, "special", fs=13),
        _r("시청각실", "시청각실", 1165, 225, 230, 140, "special", fs=16),
        _r("학교숲", "학교숲", 965, 385, 430, 180, "outdoor", fs=18),
        _r("화장실여R1", "화장실\n(여)", 1140, 580, 57, 65, "facility"),
        _r("화장실남R1", "화장실\n(남)", 1197, 580, 57, 65, "facility"),
        _r("계단R1", "계단", 1290, 580, 55, 65, "facility"),
        _r("교육행정실", "교육\n행정실", 920, 710, 110, 80, "office", fs=12),
        _r("교장실", "교장실", 1050, 710, 110, 80, "office", fs=12),
        _r("보건실", "보건실", 1210, 710, 110, 80, "office", fs=12),
    ],

    # ═══ 2층 ═══ (복도 뼈대는 3~5층과 동일)
    2: [
        _r("체육관", "체육관", 60, 120, 450, 360, "special", fs=20),
        _r("예술체육부", "예술체육부", 510, 120, 120, 66, "office", fs=11),
        _r("Wee클래스", "Wee클래스", 510, 186, 120, 80, "office", fs=11),
        _r("계단C2", "계단", 510, 320, 120, 75, "facility"),
        _r("통합교육지원실", "통합교육\n지원실", 510, 425, 120, 105, "special", fs=12),
        _r("사물함2", "사물함", 675, 150, 120, 145, "facility", fs=12),
        _r("사이언스북클럽", "사이언스\n북클럽", 675, 345, 120, 210, "special", fs=12),
        _r("ELV2", "ELV", 675, 610, 120, 48, "facility"),
        _r("계단T2", "계단", 820, 225, 60, 70, "facility"),
        _r("화장실남T2", "화장실\n(남)", 905, 225, 48, 70, "facility"),
        _r("화장실여T2", "화장실\n(여)", 965, 225, 48, 70, "facility"),
        _r("108", "1-8", 1020, 160, 108, 135, "class"),
        _r("109", "1-9", 1128, 160, 108, 135, "class"),
        _r("110", "1-10", 1236, 160, 108, 135, "class"),
        _r("111", "1-11", 1344, 160, 108, 135, "class"),
        *_left_end(2), *_right_end(2),
        _r("학생안전부", "학생\n안전부", 60, _ROW_Y, 80, _ROW_H, "office", fs=11),
        _r("본교무실", "본교무실", 140, _ROW_Y, 210, _ROW_H, "office", fs=15),
        _r("대외협력부", "대외\n협력부", 350, _ROW_Y, 80, _ROW_H, "office", fs=11),
        _r("방송실", "방송실", 430, _ROW_Y, 80, _ROW_H, "special", fs=11),
        _nanum(2, "L", 512),
        _r("1학년교무실", "1학년\n교무실", 565, _ROW_Y, 180, _ROW_H + 20, "office", fs=15),
        _nanum(2, "R", 763),
        *_class5([
            ("진로활동실", "진로\n활동실", "special"),
            ("교과교실3", "교과교실3", "special"),
            ("105", "1-5", "class"),
            ("106", "1-6", "class"),
            ("107", "1-7", "class"),
        ]),
    ],

    # ═══ 3층 ═══
    3: [
        _r("교과교실_3F", "교과교실", 510, 100, 120, 62, "special", fs=12),
        _r("과학정보부", "과학정보부", 510, 162, 120, 60, "office", fs=12),
        _r("홈베이스3", "", 510, 222, 120, 108, "special"),
        _r("사물함3", "사물함", 510, 330, 120, 82, "facility", fs=12),
        _r("저현마루", "저현마루", 510, 412, 120, 218, "special", fs=13),
        _r("창의융합zone", "창의융합\nzone", 675, 150, 120, 145, "special", fs=13),
        _r("화학실험실", "화학\n실험실", 675, 345, 120, 160, "special", fs=13),
        _r("준비실C3", "준비실", 675, 505, 120, 50, "facility"),
        _r("계단C3", "계단", 675, 555, 120, 55, "facility"),
        _r("ELV3", "ELV", 675, 610, 120, 48, "facility"),
        _r("계단T3", "계단", 820, 225, 60, 70, "facility"),
        _r("화장실남T3", "화장실\n(남)", 905, 225, 48, 70, "facility"),
        _r("화장실여T3", "화장실\n(여)", 965, 225, 48, 70, "facility"),
        _r("준비실T3a", "준비실", 1020, 160, 55, 135, "facility"),
        _r("생물실험실", "생물 실험실", 1075, 160, 165, 135, "special", fs=14),
        _r("준비실T3b", "준비실", 1240, 160, 55, 135, "facility"),
        _r("물리지학실험실", "물리·지학\n실험실", 1295, 160, 155, 135, "special", fs=14),
        *_left_end(3), *_right_end(3),
        *_class4([("101", "1-1"), ("102", "1-2"), ("103", "1-3"), ("104", "1-4")]),
        _nanum(3, "L", 512),
        _r("창의융합실", "창의융합실", 565, _ROW_Y, 180, _ROW_H + 20, "special", fs=15),
        _nanum(3, "R", 763),
        *_class5([
            ("사회교과실", "사회\n교과실", "special"),
            ("209", "2-9", "class"),
            ("210", "2-10", "class"),
            ("211", "2-11", "class"),
            ("212", "2-12", "class"),
        ]),
    ],

    # ═══ 4층 ═══
    4: [
        _r("창의인문부", "창의인문부", 510, 100, 120, 62, "office", fs=12),
        _r("교과교실_4F", "교과교실", 510, 162, 120, 68, "special", fs=12),
        _r("학생회자치실", "학생회\n자치실", 510, 230, 120, 100, "special", fs=12),
        _r("창의융합컴퓨터실", "창의융합\n컴퓨터실", 510, 330, 120, 135, "special", fs=12),
        _r("미술실2", "미술실(2)", 510, 465, 120, 165, "special", fs=13),
        _r("사물함4", "사물함", 675, 150, 120, 145, "facility", fs=12),
        _r("미술실1", "미술실(1)", 675, 345, 120, 160, "special", fs=13),
        _r("준비실C4", "준비실", 675, 505, 120, 50, "facility"),
        _r("계단C4", "계단", 675, 555, 120, 55, "facility"),
        _r("ELV4", "ELV", 675, 610, 120, 48, "facility"),
        _r("계단T4", "계단", 820, 225, 60, 70, "facility"),
        _r("화장실남T4", "화장실\n(남)", 905, 225, 48, 70, "facility"),
        _r("화장실여T4", "화장실\n(여)", 965, 225, 48, 70, "facility"),
        _r("309", "3-9", 1020, 160, 108, 135, "class"),
        _r("310", "3-10", 1128, 160, 108, 135, "class"),
        _r("311", "3-11", 1236, 160, 108, 135, "class"),
        _r("312", "3-12", 1344, 160, 108, 135, "class"),
        *_left_end(4), *_right_end(4),
        *_class4([("201", "2-1"), ("202", "2-2"), ("203", "2-3"), ("204", "2-4")]),
        _nanum(4, "L", 512),
        _r("2학년교무실", "2학년\n교무실", 565, _ROW_Y, 180, _ROW_H + 20, "office", fs=15),
        _nanum(4, "R", 763),
        *_class5([
            ("외국어교과실", "외국어\n교과실", "special"),
            ("205", "2-5", "class"),
            ("206", "2-6", "class"),
            ("207", "2-7", "class"),
            ("208", "2-8", "class"),
        ]),
    ],

    # ═══ 5층 ═══
    5: [
        _r("하늘공원", "하늘공원", 510, 100, 910, 180, "outdoor", fs=20),
        _r("교직원휴게실", "교직원\n휴게실", 510, 310, 120, 105, "office", fs=12),
        _r("사물함5", "사물함", 510, 460, 120, 150, "facility", fs=12),
        _r("음악실", "음악실", 675, 280, 120, 180, "special", fs=13),
        _r("준비실C5", "준비실", 675, 460, 120, 55, "facility"),
        _r("계단C5", "계단", 675, 515, 120, 60, "facility"),
        _r("ELV5", "ELV", 675, 575, 120, 60, "facility"),
        *_left_end(5), *_right_end(5),
        *_class4([("301", "3-1"), ("302", "3-2"), ("303", "3-3"), ("304", "3-4")]),
        _nanum(5, "L", 512),
        _r("3학년교무실", "3학년\n교무실", 565, _ROW_Y, 180, _ROW_H + 20, "office", fs=15),
        _nanum(5, "R", 763),
        *_class5([
            ("진학상담실", "진학\n상담실", "office"),
            ("305", "3-5", "class"),
            ("306", "3-6", "class"),
            ("307", "3-7", "class"),
            ("308", "3-8", "class"),
        ]),
    ],
}

# ── 층별 복도 정의 (x, y, w, h [, label]) ────────────────────────
FLOOR_CORRIDORS = {
    1: [
        (660, 225, 45, 475),               # 급식동 세로 복도
        (380, 650, 325, 50, "복도"),        # 도서관 앞 복도
        (765, 225, 50, 485),               # 본관 세로 복도
        (765, 660, 630, 50, "복도"),        # 본관 가로 복도
    ],
    2: [
        (630, 100, 45, 560),               # 세로 복도 (3~5층과 동일 위치)
        (675, 295, 775, 50, "복도"),        # 1-8~1-11 앞 복도
        (60, 660, 1360, 50, "복도"),        # 아래쪽 가로 복도
    ],
    3: [
        (630, 100, 45, 560),               # 세로 복도
        (675, 295, 775, 50, "복도"),        # 실험실 앞 복도
        (60, 660, 1360, 50, "복도"),        # 아래쪽 가로 복도
    ],
    4: [
        (630, 100, 45, 560),
        (675, 295, 775, 50, "복도"),
        (60, 660, 1360, 50, "복도"),
    ],
    5: [
        (630, 280, 45, 380),
        (60, 660, 1360, 50, "복도"),
    ],
}

# ── 교실 id → 층 / 표시 이름 ─────────────────────────────────────
ROOM_FLOOR = {rm["id"]: f for f, rooms in FLOOR_ROOMS.items() for rm in rooms}
ROOM_NAME  = {rm["id"]: rm["name"].replace("\n", " ")
              for rooms in FLOOR_ROOMS.values() for rm in rooms if rm["name"]}

# ── 야외 수업 장소 ────────────────────────────────────────────────
# 건물 지도(층별 평면도)에는 없지만 수업 위치로는 선택 가능한 공간.
# 층 개념이 없어 ROOM_FLOOR 에는 넣지 않고, 실제 층 데이터는 0으로 표기한다.
OUTDOOR_ROOMS = {
    "운동장":     "운동장",
    "철없는쉼터": "철없는 쉼터",
    "농구배구장": "농구·배구장",
}
ROOM_NAME.update(OUTDOOR_ROOMS)


def is_outdoor_room(rid) -> bool:
    return str(rid) in OUTDOOR_ROOMS


def find_room_floor(rid, default=None):
    return ROOM_FLOOR.get(str(rid), default)


def room_display_name(rid):
    return ROOM_NAME.get(str(rid), str(rid))


# ── SVG 빌드 ────────────────────────────────────────────────────
def _floor_viewbox(floor):
    xs, ys = [], []
    for rm in FLOOR_ROOMS[floor]:
        xs += [rm["x"], rm["x"] + rm["w"]]
        ys += [rm["y"], rm["y"] + rm["h"]]
    for c in FLOOR_CORRIDORS.get(floor, []):
        xs += [c[0], c[0] + c[2]]
        ys += [c[1], c[1] + c[3]]
    pad = 25
    x0, y0 = min(xs) - pad, min(ys) - pad
    return x0, y0, max(xs) - x0 + pad, max(ys) - y0 + pad


def build_map_html(floor: int, highlight_map: dict | None = None) -> tuple[str, int]:
    """(html, 권장 컴포넌트 높이) 반환. highlight_map: {room_id: current|next|teacher}"""
    highlight_map = highlight_map or {}
    rooms = FLOOR_ROOMS.get(floor, [])
    vx, vy, vw, vh = _floor_viewbox(floor)

    parts = []

    # 복도 (벽보다 먼저 = 아래층에 깔림)
    for c in FLOOR_CORRIDORS.get(floor, []):
        x, y, w, h = c[:4]
        label = c[4] if len(c) > 4 else None
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{CORRIDOR_FILL}" stroke="{CORRIDOR_LINE}" stroke-width="1"/>'
        )
        if label:
            parts.append(
                f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" '
                f'font-size="12" fill="#B4A886" letter-spacing="6" '
                f'pointer-events="none">{label}</text>'
            )

    # 방 (벽 = 진한 테두리)
    for rm in rooms:
        rid = rm["id"]
        hl = highlight_map.get(rid)
        if hl in HIGHLIGHT:
            style = HIGHLIGHT[hl]
            fill, stroke, sw = style["fill"], style["stroke"], style["sw"]
        else:
            fill, stroke, sw = TYPE_FILL.get(rm["type"], "#fff"), WALL_COLOR, 2

        clickable = bool(rm["name"])
        name_flat = rm["name"].replace("\n", " ")
        onclick = (f''' onclick="selectRoom('{rid}', '{name_flat}')" style="cursor:pointer;"'''
                   if clickable else "")

        # 이름 (줄바꿈 지원)
        text_el = ""
        if rm["name"]:
            lines = rm["name"].split("\n")
            lh = rm["fs"] + 4
            cy = rm["y"] + rm["h"] / 2 + rm["fs"] / 3 - (len(lines) - 1) * lh / 2
            tspans = "".join(
                f'<tspan x="{rm["x"] + rm["w"] / 2}" dy="{0 if i == 0 else lh}">{l}</tspan>'
                for i, l in enumerate(lines)
            )
            text_el = (
                f'<text x="{rm["x"] + rm["w"] / 2}" y="{cy}" text-anchor="middle" '
                f'font-size="{rm["fs"]}" font-weight="700" '
                f'fill="{"#3D3929" if not hl else "#1a1a1a"}" '
                f'pointer-events="none">{tspans}</text>'
            )

        # 강조 배지 + 펄스 링
        badge = ""
        if hl in HIGHLIGHT:
            bx, by = rm["x"] + rm["w"] - 14, rm["y"] + 16
            badge = (
                f'<circle cx="{bx}" cy="{by - 5}" r="8" fill="none" '
                f'stroke="{HIGHLIGHT[hl]["stroke"]}" stroke-width="2">'
                f'<animate attributeName="r" values="6;15" dur="1.4s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0.9;0" dur="1.4s" repeatCount="indefinite"/>'
                f'</circle>'
                f'<text x="{bx}" y="{by}" font-size="13" text-anchor="middle" '
                f'pointer-events="none">{HIGHLIGHT[hl]["emoji"]}</text>'
            )

        parts.append(
            f'<g class="room" data-id="{rid}"{onclick}>'
            f'<rect x="{rm["x"]}" y="{rm["y"]}" width="{rm["w"]}" height="{rm["h"]}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="miter"/>'
            f'{text_el}{badge}</g>'
        )

    hl_json    = json.dumps(highlight_map, ensure_ascii=False)
    map_height = int(1000 * vh / vw)

    html = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
body {{ margin:0; font-family:'Noto Sans KR',sans-serif; }}
.room rect {{ transition: filter .15s; }}
.room:hover rect {{ filter: brightness(0.93); }}
.map-hint {{ display:none; }}
/* 모바일: 지도를 축소하지 않고 원본 크기 그대로 좌우 스크롤로 본다 */
@media (max-width: 640px) {{
  .map-scroll {{ overflow-x:auto !important; -webkit-overflow-scrolling:touch; }}
  .map-scroll svg {{ width:1000px !important; }}
  .map-hint {{ display:block; margin-top:6px; font-size:0.72rem;
               color:#9E9070; text-align:center; }}
}}
</style>
<div style="width:100%; max-width:1000px; margin:0 auto;">
  <div class="map-scroll" style="border:1px solid #E0D8CC; border-radius:12px; overflow:hidden;
       background:#F7F4EE; box-shadow:0 2px 12px rgba(0,0,0,0.08);">
    <svg viewBox="{vx} {vy} {vw} {vh}" xmlns="http://www.w3.org/2000/svg"
         style="display:block; width:100%; height:auto;">
      {''.join(parts)}
    </svg>
  </div>
  <div class="map-hint">↔️ 지도를 좌우로 밀어서 전체를 볼 수 있어요</div>
  <div id="room-info" style="display:none; margin-top:10px; padding:12px 18px;
       background:#fff; border:1px solid #E0D8CC; border-left:4px solid #7D6B2E;
       border-radius:10px;">
    <div id="room-info-text" style="font-size:0.95rem; font-weight:700; color:#3D3929;"></div>
  </div>
</div>
<script>
const _highlight = {hl_json};
function selectRoom(id, name) {{
  document.querySelectorAll('.room rect').forEach(r => {{
    if (!(r.parentNode.dataset.id in _highlight)) {{
      r.setAttribute('stroke', '{WALL_COLOR}');
      r.setAttribute('stroke-width', '2');
    }}
  }});
  const el = document.querySelector(`[data-id="${{id}}"] rect`);
  if (el && !(id in _highlight)) {{
    el.setAttribute('stroke', '#7D6B2E');
    el.setAttribute('stroke-width', '4');
  }}
  const badges = {{'current': ' · 🔴 수업 중', 'next': ' · 🟢 다음 교시', 'teacher': ' · 👩‍🏫 선생님 위치'}};
  document.getElementById('room-info').style.display = 'block';
  document.getElementById('room-info-text').textContent =
    '📍 ' + name + (badges[_highlight[id]] || '');
}}
</script>
"""
    return html, map_height + 90


def render_map(floor: int, highlight_map: dict | None = None):
    """Streamlit 컴포넌트로 평면도 렌더링."""
    html, height = build_map_html(floor, highlight_map)
    # st.components.v1.html 은 2026-06 이후 제거 예정 → st.iframe 우선 사용
    if hasattr(st, "iframe"):
        st.iframe(html, height=height)
    else:
        st.components.v1.html(html, height=height, scrolling=False)
