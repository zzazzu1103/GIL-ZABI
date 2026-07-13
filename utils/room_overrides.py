"""
utils/room_overrides.py
─────────────────────────
선생님이 본인 시간표("내 시간표")에서 즉석으로 바꾼 교실 위치를 저장한다.
원본 data/timetable.csv, data/teacher_timetable.csv 는 그대로 두고,
로드 시점에 (교사명, 요일, 교시) 기준 오버라이드를 겹쳐 적용한다.

저장 위치: Google Sheets (utils/gsheets.py 공용 스프레드시트의 room_overrides
탭) → 실패 시 data/room_overrides.json 폴백 (다른 개인 설정과 동일 패턴).
"""

import json
import os
from datetime import datetime, timezone, timedelta

import streamlit as st

from utils import gsheets
from utils.floorplan import find_room_floor, is_outdoor_room

KST = timezone(timedelta(hours=9))

SHEET_NAME = "room_overrides"
_HEADER = ["key", "교사명", "요일", "교시", "교실위치", "updated_at"]

OVERRIDES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "room_overrides.json"
)


def _key(teacher, day, period) -> str:
    return f"{teacher}|{day}|{int(period)}"


def _get_worksheet(readonly=True):
    return gsheets.open_worksheet(SHEET_NAME, _HEADER, readonly=readonly)


def _load_json_all() -> dict:
    if not os.path.exists(OVERRIDES_PATH):
        return {}
    try:
        with open(OVERRIDES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json_all(data: dict):
    os.makedirs(os.path.dirname(OVERRIDES_PATH), exist_ok=True)
    with open(OVERRIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@st.cache_data(ttl=60)
def load_room_overrides() -> dict:
    """{"교사명|요일|교시": 교실위치} 형태의 dict 반환."""
    ws = _get_worksheet(readonly=True)
    if ws:
        try:
            rows = ws.get_all_records()
            return {
                str(r["key"]): str(r["교실위치"])
                for r in rows if r.get("key") and r.get("교실위치")
            }
        except Exception:
            pass
    return _load_json_all()


def save_room_override(teacher: str, day: str, period: int, room: str):
    """(교사명, 요일, 교시) 의 교실 오버라이드를 저장하고 캐시를 갱신한다."""
    key = _key(teacher, day, period)
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    row_data = [key, teacher, day, str(int(period)), room, now_str]

    ws = _get_worksheet(readonly=False)
    if ws:
        try:
            row_num = gsheets.find_row(ws, key, col=1)
            if row_num:
                ws.update(f"A{row_num}:F{row_num}", [row_data])
            else:
                ws.append_row(row_data, value_input_option="USER_ENTERED")
            load_room_overrides.clear()
            return
        except Exception:
            pass

    # 폴백: JSON
    data = _load_json_all()
    data[key] = room
    _save_json_all(data)
    load_room_overrides.clear()


def apply_room_overrides(df, teacher_col="교사명", day_col="요일",
                          period_col="교시", room_col="교실위치", floor_col="층"):
    """timetable 형태 DataFrame 에 교실 오버라이드를 겹쳐 적용한 새 DataFrame 반환.

    교사·요일·교시가 같으면 물리적으로 같은 수업이므로(선택과목처럼 여러
    반이 같은 시간에 같은 선생님을 참조하는 행도 포함) 전부 동일하게 반영된다.
    """
    overrides = load_room_overrides()
    if not overrides or df.empty:
        return df
    df = df.copy()
    keys = (
        df[teacher_col].astype(str) + "|" + df[day_col].astype(str) + "|"
        + df[period_col].astype(int).astype(str)
    )
    mask = keys.isin(overrides)
    if not mask.any():
        return df
    new_rooms = keys[mask].map(overrides)
    df.loc[mask, room_col] = new_rooms
    # 실내 지도에 있는 방이면 그 층, 야외 장소면 0(층 없음), 그 외 알 수 없는
    # 값이면 기존 층을 그대로 둔다.
    new_floors = new_rooms.map(
        lambda r: 0 if is_outdoor_room(r) else find_room_floor(r)
    )
    has_floor = new_floors.notna()
    if has_floor.any():
        idx = new_floors[has_floor].index
        df.loc[idx, floor_col] = new_floors[has_floor].astype(int)
    return df
