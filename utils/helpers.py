import pandas as pd
import streamlit as st
from datetime import datetime, time
import os

# ── 교시 시간 정의 ─────────────────────────────────────────────
PERIODS = {
    1: (time(8, 30),  time(9, 20)),
    2: (time(9, 30),  time(10, 20)),
    3: (time(10, 30), time(11, 20)),
    4: (time(11, 30), time(12, 20)),
    5: (time(13, 10), time(14, 0)),
    6: (time(14, 10), time(15, 0)),
    7: (time(15, 10), time(16, 0)),
}

DAY_MAP = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
DAY_MAP_KR = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


# ── 데이터 로드 (캐시) ─────────────────────────────────────────
@st.cache_data(ttl=60)
def load_timetable():
    path = os.path.join(DATA_DIR, "timetable.csv")
    df = pd.read_csv(path)
    df["교시"] = df["교시"].astype(int)
    df["층"] = df["층"].astype(int)
    return df

@st.cache_data(ttl=60)
def load_teachers():
    path = os.path.join(DATA_DIR, "teachers.csv")
    return pd.read_csv(path)

@st.cache_data(ttl=60)
def load_rooms():
    path = os.path.join(DATA_DIR, "rooms.csv")
    df = pd.read_csv(path)
    df["층"] = df["층"].astype(int)
    df["x"] = df["x"].astype(int)
    df["y"] = df["y"].astype(int)
    df["width"] = df["width"].astype(int)
    df["height"] = df["height"].astype(int)
    return df


# ── 현재 교시 계산 ─────────────────────────────────────────────
def get_current_period(now: datetime | None = None) -> int | None:
    """현재 시각이 몇 교시인지 반환. 쉬는 시간이면 None."""
    t = (now or datetime.now()).time()
    for period, (start, end) in PERIODS.items():
        if start <= t <= end:
            return period
    return None

def get_next_period(now: datetime | None = None) -> int | None:
    """다음 교시 번호 반환. 마지막 교시 이후면 None."""
    t = (now or datetime.now()).time()
    current = get_current_period(now)
    if current:
        nxt = current + 1
        return nxt if nxt in PERIODS else None
    for period, (start, _) in PERIODS.items():
        if t < start:
            return period
    return None

def get_current_day(now: datetime | None = None) -> str | None:
    """오늘 요일(한글) 반환. 주말이면 None."""
    wd = (now or datetime.now()).weekday()
    return DAY_MAP.get(wd) if wd < 5 else None

def period_status(period: int, now: datetime | None = None) -> str:
    """교시별 상태: 'current' | 'next' | 'done' | 'upcoming'"""
    t = (now or datetime.now()).time()
    start, end = PERIODS[period]
    current = get_current_period(now)
    nxt = get_next_period(now)
    if current == period:
        return "current"
    if nxt == period:
        return "next"
    if t > end:
        return "done"
    return "upcoming"


# ── 시간표 조회 헬퍼 ───────────────────────────────────────────
def get_student_timetable(df: pd.DataFrame, class_name: str, day: str) -> pd.DataFrame:
    """특정 반·요일의 시간표 반환."""
    return (
        df[(df["반"] == class_name) & (df["요일"] == day)]
        .sort_values("교시")
        .reset_index(drop=True)
    )

def get_teacher_location(
    timetable_df: pd.DataFrame,
    teachers_df: pd.DataFrame,
    teacher_name: str,
    day: str,
    period: int,
) -> dict:
    """선생님의 현재 위치 정보 반환."""
    row = timetable_df[
        (timetable_df["교사명"] == teacher_name)
        & (timetable_df["요일"] == day)
        & (timetable_df["교시"] == period)
    ]
    if not row.empty:
        r = row.iloc[0]
        return {
            "상태": "수업중",
            "교실": r["교실위치"],
            "층": r["층"],
            "과목": r["과목"],
            "반": r["반"],
        }
    # 수업 없으면 → 교무실
    t_info = teachers_df[teachers_df["교사명"] == teacher_name]
    if not t_info.empty:
        ti = t_info.iloc[0]
        return {
            "상태": "교무실",
            "교실": ti["교무실위치"],
            "층": ti["층"],
            "과목": ti["담당과목"],
            "반": "-",
        }
    return {"상태": "정보없음", "교실": "-", "층": 0, "과목": "-", "반": "-"}


# ── 색상 상수 ──────────────────────────────────────────────────
STATUS_COLORS = {
    "current":  "#FF6B35",   # 주황 — 수업 중
    "next":     "#4ECDC4",   # 청록 — 다음 교시
    "done":     "#95A5A6",   # 회색 — 완료
    "upcoming": "#2C3E50",   # 다크 — 예정
}
STATUS_LABELS = {
    "current":  "🔴 수업 중",
    "next":     "🟢 다음 교시",
    "done":     "⚫ 완료",
    "upcoming": "⚪ 예정",
}
