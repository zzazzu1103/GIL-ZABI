import pandas as pd
import streamlit as st
from datetime import datetime, time, timezone, timedelta
import os

KST = timezone(timedelta(hours=9))

PERIODS = {
    1: (time(9, 10),  time(10, 00)),
    2: (time(10, 10),  time(11, 00)),
    3: (time(11, 10), time(12, 00)),
    4: (time(12, 00), time(12, 50)),
    5: (time(14, 00), time(14, 50)),
    6: (time(15, 00), time(15, 50)),
    7: (time(16, 00), time(16, 50)),
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

# 선택과목: 학생마다 담당 선생님·교실이 다른 과목 (알파벳이 붙은 과목 코드)
ELECTIVE_CODES = {"탐구A", "탐구B", "탐구C", "탐구D", "탐구E1", "탐구E2", "교과F", "교과G"}
TANGU_CODES = ELECTIVE_CODES  # 하위 호환


def is_elective(subject) -> bool:
    return str(subject) in ELECTIVE_CODES


def is_unselected_elective(subject) -> bool:
    """개인 설정에서 아직 선생님을 고르지 않은 선택과목인지."""
    return is_elective(subject) and str(subject) not in st.session_state.get("tangu_map", {})


# ── 표시 설정 (개인 설정 페이지에서 저장) ────────────────────────
PASTEL_PALETTE = [
    "#FDE2E2", "#FFE9CF", "#FFF6C9", "#E6F4D5", "#D5EFE6", "#D3ECF5",
    "#DBE4F8", "#E8DEF6", "#F6DEEE", "#EFE3D5", "#E3E8EC", "#F0EAD2",
]


def get_prefs() -> dict:
    return st.session_state.get("prefs", {})


def auto_subject_color(subject) -> str:
    """과목명 해시 기반의 파스텔 기본 색상 (항상 같은 과목 = 같은 색)."""
    import hashlib
    h = int(hashlib.md5(str(subject).encode()).hexdigest(), 16)
    return PASTEL_PALETTE[h % len(PASTEL_PALETTE)]


def subject_color(subject) -> str | None:
    """과목 색상 표시를 켠 경우에만 색상 반환 (기본은 꺼짐 = 원래 디자인)."""
    prefs = get_prefs()
    if not prefs.get("subject_colors", False):
        return None
    return prefs.get("color_map", {}).get(str(subject)) or auto_subject_color(subject)


@st.cache_data(ttl=60, show_spinner=False)
def teacher_subjects(teacher) -> str:
    """선생님이 실제로 가르치는 과목 전체 (예: '화작 · 학특 · 논술').

    teachers.csv 담당과목은 한 과목만 적혀 있어, 교사 시간표에서
    선택과목 코드를 제외한 실제 과목들을 모아 표시한다.
    """
    # 담임 배정·창체 등으로 붙는 과목은 담당 과목 표시에서 제외
    NON_MAIN = {"학특", "자율", "동아리", "스생", "스생1", "자치", "진로"}
    try:
        ttt = load_teacher_timetable()
        codes = [s for s in ttt[ttt["교사명"] == teacher]["과목"].unique()
                 if s not in NON_MAIN]
        subs = []
        for code in codes:
            # 선택과목은 (코드, 교사) 매핑의 실제 과목명으로 치환
            subs.append(elective_subject_name(code, teacher) if is_elective(code) else code)
        subs = sorted(set(s for s in subs if s))
        if subs:
            return " · ".join(subs)
    except FileNotFoundError:
        pass
    t = load_teachers()
    row = t[t["교사명"] == teacher]
    return str(row.iloc[0]["담당과목"]) if not row.empty else ""


def week_dates(now=None) -> dict:
    """이번 주(주말이면 다음 주) 월~금의 날짜 문자열. {'월': '7/13', ...}"""
    n = now or datetime.now(KST)
    monday = n - timedelta(days=n.weekday())
    if n.weekday() >= 5:
        monday += timedelta(days=7)
    return {
        d: f"{(monday + timedelta(days=i)).month}/{(monday + timedelta(days=i)).day}"
        for i, d in enumerate(["월", "화", "수", "목", "금"])
    }


def day_label(day: str) -> str:
    """요일 라벨. 설정이 켜져 있으면 날짜를 붙임 (예: '월 (7/13)')."""
    if get_prefs().get("show_dates", True):
        return f"{day} ({week_dates()[day]})"
    return day


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


def _sheets_configured() -> bool:
    try:
        return "gcp_service_account" in st.secrets and "sheets" in st.secrets
    except Exception:
        return False


@st.cache_data(ttl=60)
def load_timetable():
    if _sheets_configured():
        try:
            from utils.sheets_sync import load_timetable_sheets
            df = load_timetable_sheets()
        except Exception:
            df = pd.read_csv(os.path.join(DATA_DIR, "timetable.csv"))
    else:
        df = pd.read_csv(os.path.join(DATA_DIR, "timetable.csv"))
    df["교시"] = df["교시"].astype(int)
    df["층"]   = df["층"].astype(int)
    df["교실위치"] = df["교실위치"].astype(str)
    from utils.room_overrides import apply_room_overrides
    return apply_room_overrides(df)

@st.cache_data(ttl=300)
def load_teachers():
    return pd.read_csv(os.path.join(DATA_DIR, "teachers.csv"))

@st.cache_data(ttl=300)
def load_elective_subjects() -> dict:
    """(과목코드, 교사명) → 실제 과목명 (예: (탐구D, 이지원) → 물리Ⅱ).

    data/elective_subjects.csv 를 수정해 실제 과목명을 관리한다.
    """
    try:
        df = pd.read_csv(os.path.join(DATA_DIR, "elective_subjects.csv"))
        return {
            (str(r["과목코드"]), str(r["교사명"])): str(r["과목명"])
            for _, r in df.iterrows() if str(r.get("과목명", "")).strip()
        }
    except FileNotFoundError:
        return {}


def elective_subject_name(code, teacher) -> str:
    """선택과목 코드+교사 → 실제 과목명. 매핑이 없으면 teachers.csv 담당과목."""
    name = load_elective_subjects().get((str(code), str(teacher)))
    if name:
        return name
    t = load_teachers()
    row = t[t["교사명"] == teacher]
    return str(row.iloc[0]["담당과목"]) if not row.empty else ""


@st.cache_data(ttl=60)
def load_teacher_timetable():
    """교사별 시간표 (교사명,요일,교시,과목,교실위치,층) — 선택과목 포함 전체 수업.

    학급 시간표(load_timetable)에서 파생하므로 관리자 페이지에서 수정한
    내용(Google Sheets 포함)이 교사 시간표에도 그대로 반영된다.
    같은 (교사, 요일, 교시)에 여러 반 수업(합반 등)이 있으면 한 행만 남긴다.
    """
    try:
        df = load_timetable()[["교사명", "요일", "교시", "과목", "교실위치", "층"]]
        df = df.drop_duplicates(subset=["교사명", "요일", "교시"]).reset_index(drop=True)
    except Exception:
        df = pd.read_csv(os.path.join(DATA_DIR, "teacher_timetable.csv"))
        df["교시"] = df["교시"].astype(int)
        df["층"]   = df["층"].astype(int)
        df["교실위치"] = df["교실위치"].astype(str)
        from utils.room_overrides import apply_room_overrides
        df = apply_room_overrides(df)
    return df

@st.cache_data(ttl=300)
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
    from utils.floorplan import find_room_floor
    floor = find_room_floor(row["교실위치"])
    if floor is not None:
        row["층"] = floor
    return row


def get_personalized_timetable(df: pd.DataFrame, class_name: str, day: str) -> pd.DataFrame:
    """반/요일 시간표를 가져오되 탐구 매핑을 적용해 반환."""
    sub = df[(df["반"] == class_name) & (df["요일"] == day)].copy().sort_values("교시")
    tangu_map = st.session_state.get("tangu_map", {})
    if tangu_map:
        sub = sub.apply(lambda row: apply_tangu_map(row, tangu_map), axis=1)
    return sub


def get_teacher_location(timetable_df, teachers_df, teacher_name, day, period):
    # 1순위: 교사 시간표 (선택과목 포함 전체 수업이 들어 있음)
    try:
        ttt = load_teacher_timetable()
        row = ttt[
            (ttt["교사명"] == teacher_name) &
            (ttt["요일"]   == day) &
            (ttt["교시"]   == period)
        ]
        if not row.empty:
            r = row.iloc[0]
            from utils.floorplan import room_display_name
            ban = room_display_name(r["교실위치"])
            return {"상태": "수업중", "교실": r["교실위치"], "층": r["층"],
                    "과목": r["과목"], "반": ban}
    except FileNotFoundError:
        pass
    # 2순위: 반별 시간표
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
