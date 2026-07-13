"""
utils/user_settings.py
──────────────────────
이메일 기반 사용자 설정 저장/불러오기
저장 위치: Google Sheets (user_settings 시트)
폴백: data/user_settings.json (시트 연동 실패 시)
"""

import json
import os
import streamlit as st
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# 시간표 동기화용으로 이미 연결된 스프레드시트(secrets["sheets"]["timetable_id"])를
# 그대로 재사용하고, 그 안에 user_settings 탭을 둔다.
# 별도 시트를 쓰고 싶으면 secrets.toml 에 sheets.user_settings_id 를 추가하면 된다.
SHEET_NAME = "user_settings"


def _sheet_id():
    try:
        sheets = st.secrets["sheets"]
        return sheets.get("user_settings_id") or sheets["timetable_id"]
    except Exception:
        return None

SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "user_settings.json"
)

DEFAULT_SETTINGS = {
    "my_class":    "",
    "my_subjects": [],
    "my_classes":  [],
    "tangu_map":   {},
    "prefs":       {},   # 표시 설정: subject_colors, show_dates, color_map
}


# ── Google Sheets 헬퍼 ────────────────────────────────────────

def _get_client(readonly=True):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception:
        # ImportError(미설치) 외에 native crypto 라이브러리 로드 실패(예:
        # 환경별 cryptography/cffi 바이너리 불일치)도 폴백으로 처리한다.
        return None
    try:
        scopes = (
            ["https://www.googleapis.com/auth/spreadsheets.readonly",
             "https://www.googleapis.com/auth/drive.readonly"]
            if readonly else
            ["https://www.googleapis.com/auth/spreadsheets"]
        )
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scopes
        )
        return gspread.authorize(creds)
    except Exception:
        return None


def _get_worksheet(readonly=True):
    sheet_id = _sheet_id()
    if not sheet_id:
        return None
    gc = _get_client(readonly)
    if not gc:
        return None
    try:
        sh = gc.open_by_key(sheet_id)
    except Exception:
        return None
    try:
        return sh.worksheet(SHEET_NAME)
    except Exception:
        # user_settings 탭이 아직 없으면 쓰기 모드에서만 새로 만든다
        # (읽기 전용 권한으로는 add_worksheet 이 실패하므로 그대로 None 반환)
        if readonly:
            return None
        try:
            ws = sh.add_worksheet(title=SHEET_NAME, rows=1000, cols=7)
            ws.append_row(
                ["email", "my_class", "tangu_map", "my_subjects",
                 "my_classes", "updated_at", "prefs"],
                value_input_option="USER_ENTERED",
            )
            return ws
        except Exception:
            return None


def _find_row(ws, email: str):
    """이메일로 행 번호(1-based) 반환. 없으면 None."""
    try:
        emails = ws.col_values(1)  # A열 전체
        for i, e in enumerate(emails):
            if e == email:
                return i + 1  # gspread는 1-based
        return None
    except Exception:
        return None


# ── JSON 폴백 ─────────────────────────────────────────────────

def _load_json_all() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(email: str, settings: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    all_data = _load_json_all()
    all_data[email] = settings
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)


# ── 공개 API ──────────────────────────────────────────────────

def storage_backend() -> str:
    """현재 사용 중인 저장 방식. 'sheets' 가 아니면 로컬 파일이라
    Streamlit Cloud 재배포·재시작 시 초기화된다."""
    return "sheets" if _get_worksheet(readonly=True) else "json"


def load_user_settings(email: str) -> dict:
    """이메일로 설정 불러오기. 시트 → JSON 폴백 순서."""
    ws = _get_worksheet(readonly=True)
    if ws:
        try:
            row_num = _find_row(ws, email)
            if row_num:
                row = ws.row_values(row_num)
                # 컬럼 순서: email, my_class, tangu_map, my_subjects, my_classes, updated_at
                def _safe_json(val, default):
                    try:
                        return json.loads(val) if val else default
                    except Exception:
                        return default

                # 컬럼: A=email, B=my_class, C=tangu_map, D=my_subjects,
                #       E=my_classes, F=updated_at, G=prefs(표시 설정)
                return {
                    "my_class":    row[1] if len(row) > 1 else "",
                    "tangu_map":   _safe_json(row[2] if len(row) > 2 else "", {}),
                    "my_subjects": _safe_json(row[3] if len(row) > 3 else "", []),
                    "my_classes":  _safe_json(row[4] if len(row) > 4 else "", []),
                    "prefs":       _safe_json(row[6] if len(row) > 6 else "", {}),
                }
        except Exception:
            pass

    # 폴백: JSON
    all_data = _load_json_all()
    settings = all_data.get(email, {})
    return {**DEFAULT_SETTINGS, **settings}


def save_user_settings(email: str, settings: dict):
    """설정 저장. 시트 우선, 실패 시 JSON 폴백."""
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    row_data = [
        email,
        settings.get("my_class", ""),
        json.dumps(settings.get("tangu_map", {}),   ensure_ascii=False),
        json.dumps(settings.get("my_subjects", []), ensure_ascii=False),
        json.dumps(settings.get("my_classes", []),  ensure_ascii=False),
        now_str,
        json.dumps(settings.get("prefs", {}),       ensure_ascii=False),
    ]

    ws = _get_worksheet(readonly=False)
    if ws:
        try:
            row_num = _find_row(ws, email)
            if row_num:
                ws.update(f"A{row_num}:G{row_num}", [row_data])
            else:
                ws.append_row(row_data, value_input_option="USER_ENTERED")
            return  # 시트 저장 성공
        except Exception:
            pass

    # 폴백: JSON
    _save_json(email, settings)


def apply_user_settings_to_session(email: str):
    """로그인 시 저장된 설정을 세션에 자동 적용"""
    settings = load_user_settings(email)
    if settings.get("my_class"):
        st.session_state["my_class"] = settings["my_class"]
    if settings.get("tangu_map"):
        st.session_state["tangu_map"] = settings["tangu_map"]
    if settings.get("my_subjects"):
        st.session_state["my_subjects"] = settings["my_subjects"]
    if settings.get("my_classes"):
        st.session_state["my_classes"] = settings["my_classes"]
    if settings.get("prefs"):
        st.session_state["prefs"] = settings["prefs"]
