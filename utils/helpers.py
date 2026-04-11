import pandas as pd
import streamlit as st
from datetime import datetime, time, timezone, timedelta
import os

KST = timezone(timedelta(hours=9))

PERIODS = {
    1: (time(9, 10),  time(10, 00)),
    2: (time(10, 10),  time(11, 00)),
    3: (time(11, 10), time(12, 00)),
    4: (time(12, 10), time(13, 00)),
    5: (time(14, 00), time(14, 50)),
    6: (time(15, 00), time(15, 50)),
    7: (time(16, 10), time(16, 50)),
}

DAY_MAP = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금"}
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

STATUS_LABELS = {
    "current":  "🟡 수업 중",
    "next":     "🟢 다음 교시",
    "done":     "⚫ 완료",
    "upcoming": "⚪ 예정",
}

STATUS_COLORS = {
    "current":  "#D97706",
    "next":     "#059669",
    "done":     "#9E9070",
    "upcoming": "#D4C9A8",
}

TANGU_CODES = {"탐구A", "탐구B", "탐구C", "탐구D", "탐구E1", "탐구E2"}


def sort_classes(class_list: list) -> list:
    """
    반 목록을 숫자 기준으로 정렬.
    '1-1', '1-2', ..., '1-12', '2-1', ... 순서로.
    """
    def _key(c):
        try:
            parts = c.split("-")
            return (int(parts[0]), int(parts[1]))
        except Exception:
            return (999, 999)
    return sorted(class_list, key=_key)


@st.cache_data(ttl=60)
def load_timetable():
    df = pd.read_csv(os.path.join(DATA_DIR, "timetable.csv"))
    df["교시"] = df["교시"].astype(int)
    df["층"]   = df["층"].astype(int)
    return df

@st.cache_data(ttl=60)
def load_teachers():
    return pd.read_csv(os.path.join(DATA_DIR, "teachers.csv"))

@st.cache_data(ttl=60)
def load_rooms():
    df = pd.read_csv(os.path.join(DATA_DIR, "rooms.csv"))
    for col in ["층", "x", "y", "width", "height"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype(int)
    return df


def get_current_period(now=None):
    t = (now or datetime.now(KST)).time()
    for period, (start, end) in PERIODS.items():
        if start <= t <= end:
            return period
    return None

def get_next_period(now=None):
    t = (now or datetime.now(KST)).time()
    current = get_current_period(now)
    if current:
        nxt = current + 1
        return nxt if nxt in PERIODS else None
    for period, (start, _) in PERIODS.items():
        if t < start:
            return period
    return None

def get_current_day(now=None):
    wd = (now or datetime.now(KST)).weekday()
    return DAY_MAP.get(wd)

def period_status(period, now=None):
    t = (now or datetime.now(KST)).time()
    start, end = PERIODS[period]
    cur = get_current_period(now)
    nxt = get_next_period(now)
    if cur == period:  return "current"
    if nxt == period:  return "next"
    if t > end:        return "done"
    return "upcoming"


def apply_tangu_map(row: pd.Series, tangu_map: dict) -> pd.Series:
    """탐구 과목 행에 학생 개인 설정(교사명, 교실위치)을 적용."""
    if row["과목"] not in TANGU_CODES:
        return row
    mapping = tangu_map.get(row["과목"])
    if not mapping:
        return row
    row = row.copy()
    row["교사명"]   = mapping.get("교사명", row["교사명"])
    row["교실위치"] = mapping.get("교실위치", row["교실위치"])
    try:
        room_str = str(row["교실위치"])
        if len(room_str) >= 3 and room_str.isdigit():
            row["층"] = int(room_str[0])
    except Exception:
        pass
    return row


def get_personalized_timetable(df: pd.DataFrame, class_name: str, day: str) -> pd.DataFrame:
    """반/요일 시간표를 가져오되 탐구 매핑을 적용해 반환."""
    sub = df[(df["반"] == class_name) & (df["요일"] == day)].copy().sort_values("교시")
    tangu_map = st.session_state.get("tangu_map", {})
    if tangu_map:
        sub = sub.apply(lambda row: apply_tangu_map(row, tangu_map), axis=1)
    return sub


def get_teacher_location(timetable_df, teachers_df, teacher_name, day, period):
    row = timetable_df[
        (timetable_df["교사명"] == teacher_name) &
        (timetable_df["요일"]   == day) &
        (timetable_df["교시"]   == period)
    ]
    if not row.empty:
        r = row.iloc[0]
        return {"상태": "수업중", "교실": r["교실위치"], "층": r["층"], "과목": r["과목"], "반": r["반"]}
    t_info = teachers_df[teachers_df["교사명"] == teacher_name]
    if not t_info.empty:
        ti = t_info.iloc[0]
        return {"상태": "교무실", "교실": ti["교무실위치"], "층": ti["층"], "과목": ti["담당과목"], "반": "-"}
    return {"상태": "정보없음", "교실": "-", "층": 0, "과목": "-", "반": "-"}
