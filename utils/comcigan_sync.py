"""
utils/comcigan_sync.py ― 컴시간알리미에서 시간표 가져오기
──────────────────────────────────────────────────────────
비공식 comcigan 파서를 사용해 학급별 시간표(요일·교시·과목·교사)를
받아오고, 교실 위치는 우리 데이터와 결합해 timetable.csv 형식으로
변환한다.

교실 결정 규칙:
  1) 교사 시간표(teacher_timetable.csv)에 같은 (교사, 요일, 교시)
     수업이 있으면 그 교실 (선택과목·특별실 대응)
  2) 없으면 그 반의 홈룸 교실 (예: 1-1 → 101)

컴시간은 비공식 서비스라 언제든 구조가 바뀔 수 있다. 실패 시 예외를
그대로 올려 호출부(관리자 페이지)에서 안내하고, 기존 CSV는 건드리지
않는다.
"""

import pandas as pd

from utils.helpers import load_teachers, load_teacher_timetable
from utils.floorplan import ROOM_NAME, ROOM_FLOOR

DAYS = ["월", "화", "수", "목", "금"]

# 반 이름 → 홈룸 교실 코드 (floorplan의 ROOM_NAME 역매핑: '101' → '1-1')
CLASS_HOMEROOM = {name: rid for rid, name in ROOM_NAME.items() if rid.isdigit()}


def _full_teacher_name(short: str, full_names: list[str]) -> str:
    """컴시간은 교사명 끝 글자를 '*'로 가리는 경우가 있어 원본 이름으로 복원."""
    short = (short or "").strip()
    if not short:
        return ""
    if short in full_names:
        return short
    if short.endswith("*"):
        prefix = short[:-1]
        matches = [n for n in full_names if n.startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
    return short


def _lecture_fields(lec):
    """comcigan 파서 버전에 따라 Lecture 가 객체/튜플로 달라지는 것을 흡수.

    comcigan 1.4.x 는 (과목, 과목전체이름, 교사) 튜플을 반환한다.
    """
    subject = getattr(lec, "subject", None)
    teacher = getattr(lec, "teacher", None)
    if subject is None and isinstance(lec, (tuple, list)):
        subject = lec[0] if len(lec) > 0 else ""
        teacher = lec[2] if len(lec) > 2 else ""
    return str(subject or "").strip(), str(teacher or "").strip()


def fetch_comcigan_timetable(school_name: str) -> pd.DataFrame:
    """컴시간에서 전 학년 시간표를 받아 timetable.csv 스키마로 반환."""
    # comcigan 은 모듈 임포트 시점부터 requests.get 을 타임아웃 없이 호출해
    # 서버가 응답하지 않으면 무한 대기한다. comcigan 이 바인딩하기 전에
    # requests.get 을 타임아웃 있는 래퍼로 바꿔 모든 호출을 15초로 제한한다.
    import requests
    if not getattr(requests.get, "_comci_wrapped", False):
        _orig_get = requests.get

        def _get_with_timeout(*args, **kwargs):
            kwargs.setdefault("timeout", 15)
            return _orig_get(*args, **kwargs)

        _get_with_timeout._comci_wrapped = True
        requests.get = _get_with_timeout

    from comcigan import School   # 지연 임포트 (미설치/차단 환경 대비)

    school = School(school_name)

    teachers_df = load_teachers()
    full_names = teachers_df["교사명"].tolist()

    try:
        ttt = load_teacher_timetable()
        teacher_room = {
            (r["교사명"], r["요일"], int(r["교시"])): str(r["교실위치"])
            for _, r in ttt.iterrows()
        }
    except FileNotFoundError:
        teacher_room = {}

    rows = []
    for grade in (1, 2, 3):
        try:
            grade_obj = school[grade]
        except Exception:
            continue
        cls_num = 1
        while cls_num <= 20:
            try:
                week = grade_obj[cls_num]
            except Exception:
                break
            class_name = f"{grade}-{cls_num}"
            homeroom = CLASS_HOMEROOM.get(class_name, "")
            for day_idx, day_lectures in enumerate(list(week)[:5]):
                for period_idx, lec in enumerate(day_lectures, start=1):
                    subject, teacher_short = _lecture_fields(lec)
                    if not subject:
                        continue
                    day = DAYS[day_idx]
                    teacher = _full_teacher_name(teacher_short, full_names)
                    if teacher.endswith("*"):
                        # 동명 접두어가 여럿이면 (예: 부지영/부지예) 그 시간에
                        # 수업이 있는 선생님으로 판별
                        cands = [n for n in full_names if n.startswith(teacher[:-1])]
                        slot = [n for n in cands if (n, day, period_idx) in teacher_room]
                        if len(slot) == 1:
                            teacher = slot[0]
                    room = teacher_room.get((teacher, day, period_idx), "") or homeroom
                    rows.append({
                        "반": class_name,
                        "요일": day,
                        "교시": period_idx,
                        "과목": subject,
                        "교사명": teacher,
                        "교실위치": room,
                        "층": ROOM_FLOOR.get(str(room), 0),
                    })
            cls_num += 1

    if not rows:
        raise RuntimeError("컴시간에서 시간표를 읽지 못했습니다 (학교명 확인 필요)")
    return pd.DataFrame(rows, columns=["반", "요일", "교시", "과목", "교사명", "교실위치", "층"])
