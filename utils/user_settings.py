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

SHEET_ID   = "1-KT1n85tweEBfICn-9n10yKrRvY4vV-rwih5z-fslxU"
SHEET_NAME = "user_settings"

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
    except ImportError:
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
    gc = _get_client(readonly)
    if not gc:
        return None
    try:
        sh = gc.open_by_key(SHEET_ID)
        return sh.worksheet(SHEET_NAME)
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
