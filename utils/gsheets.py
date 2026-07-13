"""
utils/gsheets.py
─────────────────
Google Sheets 연결 공용 헬퍼. secrets["gcp_service_account"] 로 인증하고,
secrets["sheets"]["timetable_id"] 스프레드시트 안에 원하는 탭을 열거나
(쓰기 모드에서는) 자동으로 만든다. 실패 사유는 last_error() 로 확인 가능.

utils/user_settings.py 의 개인 설정, utils/auth.py 의 로그인 세션 등
여러 모듈이 "같은 스프레드시트, 다른 탭" 패턴으로 이 헬퍼를 공유한다.
"""

import streamlit as st

_last_error: str | None = None


def _fail(msg: str):
    global _last_error
    _last_error = msg
    return None


def last_error() -> str | None:
    return _last_error


def sheet_id() -> str | None:
    """공용 스프레드시트 ID. secrets["sheets"]["user_settings_id"] 가 있으면
    우선 쓰고, 없으면 timetable_id 를 재사용한다."""
    try:
        sheets = st.secrets["sheets"]
        return sheets.get("user_settings_id") or sheets["timetable_id"]
    except Exception:
        return None


def get_client(readonly=True):
    if "gcp_service_account" not in st.secrets:
        return _fail("secrets.toml 에 [gcp_service_account] 섹션이 없어요.")
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except Exception as e:
        # ImportError(미설치) 외에 native crypto 라이브러리 로드 실패(예:
        # 환경별 cryptography/cffi 바이너리 불일치)도 폴백으로 처리한다.
        return _fail(f"gspread/google-auth 로드 실패: {type(e).__name__}: {e}")
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
    except Exception as e:
        return _fail(f"서비스 계정 인증 실패: {type(e).__name__}: {e}")


def open_worksheet(tab_name: str, header: list[str], readonly=True):
    """공용 스프레드시트 안의 탭을 연다. 쓰기 모드에서 탭이 없으면
    header 행과 함께 자동 생성한다."""
    sid = sheet_id()
    if not sid:
        return _fail("secrets.toml 의 [sheets] 에 timetable_id (또는 user_settings_id) 가 없어요.")
    gc = get_client(readonly)
    if not gc:
        return None  # get_client 가 이미 사유를 기록함
    try:
        sh = gc.open_by_key(sid)
    except Exception as e:
        return _fail(
            f"스프레드시트 열기 실패 (ID: {sid[:6]}…{sid[-4:]}): "
            f"{type(e).__name__}: {e} — 서비스 계정 이메일이 이 시트에 편집자로 "
            f"공유되어 있는지, ID가 정확한지 확인하세요."
        )
    try:
        ws = sh.worksheet(tab_name)
        global _last_error
        _last_error = None
        return ws
    except Exception as e:
        # 탭이 아직 없으면 쓰기 모드에서만 새로 만든다
        # (읽기 전용 권한으로는 add_worksheet 이 실패하므로 그대로 None 반환)
        if readonly:
            return _fail(f"'{tab_name}' 탭이 아직 없어요 (읽기 전용이라 자동 생성 안 함): {e}")
        try:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=max(len(header), 1))
            ws.append_row(header, value_input_option="USER_ENTERED")
            _last_error = None
            return ws
        except Exception as e2:
            return _fail(f"'{tab_name}' 탭 자동 생성 실패: {type(e2).__name__}: {e2}")


def find_row(ws, key: str, col: int = 1) -> int | None:
    """지정한 열(1-based)에서 key 값과 일치하는 행 번호(1-based) 반환."""
    try:
        values = ws.col_values(col)
        for i, v in enumerate(values):
            if v == key:
                return i + 1
        return None
    except Exception:
        return None
