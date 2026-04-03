import pandas as pd
import streamlit as st
from datetime import datetime, time, timezone, timedelta
import os

KST = timezone(timedelta(hours=9))

PERIODS = {
    1: (time(8, 30),  time(9, 20)),
    2: (time(9, 30),  time(10, 20)),
    3: (time(10, 30), time(11, 20)),
    4: (time(11, 30), time(12, 20)),
    5: (time(13, 10), time(14, 0)),
    6: (time(14, 10), time(15, 0)),
    7: (time(15, 10), time(16, 0)),
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
