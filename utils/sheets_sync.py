"""
Google Sheets 실시간 연동 모듈
────────────────────────────────
사용 방법:
1. GCP에서 서비스 계정 생성 후 JSON 키 다운로드
2. .streamlit/secrets.toml 에 인증 정보 입력 (아래 형식 참고)
3. 구글 시트에 서비스 계정 이메일을 편집자로 공유
4. helpers.py 의 load_timetable() 를 load_timetable_sheets() 로 교체

── secrets.toml 형식 ──────────────────────────────────────
[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "key-id"
private_key = "-----BEGIN RSA PRIVATE KEY-----\\n...\\n-----END RSA PRIVATE KEY-----\\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"

[sheets]
timetable_id  = "스프레드시트_ID_여기에"   # URL에서 /d/XXXX/edit 부분
teachers_id   = "스프레드시트_ID_여기에"   # 선생님 시트 (같은 파일이면 동일 ID)
timetable_sheet  = "시간표"               # 시트 탭 이름
teachers_sheet   = "선생님"
rooms_sheet      = "교실"
────────────────────────────────────────────────────────────
"""

import pandas as pd
import streamlit as st

# ── 구글 시트 연결 ─────────────────────────────────────────────
def _get_gspread_client():
    """서비스 계정으로 gspread 클라이언트 반환."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        st.error("gspread 패키지가 없습니다. `pip install gspread google-auth` 실행 후 재시도하세요.")
        st.stop()

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)


def _sheet_to_df(gc, spreadsheet_id: str, sheet_name: str) -> pd.DataFrame:
    """지정 시트를 DataFrame으로 반환."""
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)


# ── 공개 API (ttl=60초 캐시) ───────────────────────────────────
@st.cache_data(ttl=60, show_spinner="📡 시간표 데이터 로드 중...")
def load_timetable_sheets() -> pd.DataFrame:
    gc = _get_gspread_client()
    df = _sheet_to_df(
        gc,
        st.secrets["sheets"]["timetable_id"],
        st.secrets["sheets"]["timetable_sheet"],
    )
    df["교시"] = pd.to_numeric(df["교시"], errors="coerce").astype("Int64")
    df["층"]   = pd.to_numeric(df["층"],   errors="coerce").astype("Int64")
    df = df.dropna(subset=["요일", "교시", "반"])
    return df


@st.cache_data(ttl=60, show_spinner="📡 선생님 데이터 로드 중...")
def load_teachers_sheets() -> pd.DataFrame:
    gc = _get_gspread_client()
    return _sheet_to_df(
        gc,
        st.secrets["sheets"]["timetable_id"],   # 같은 파일 내 다른 탭
        st.secrets["sheets"]["teachers_sheet"],
    )


@st.cache_data(ttl=300, show_spinner="📡 교실 데이터 로드 중...")
def load_rooms_sheets() -> pd.DataFrame:
    gc = _get_gspread_client()
    df = _sheet_to_df(
        gc,
        st.secrets["sheets"]["timetable_id"],
        st.secrets["sheets"]["rooms_sheet"],
    )
    for col in ["층", "x", "y", "width", "height"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


# ── 쓰기 권한 버전 (교사/임원용 수정) ─────────────────────────
def _get_gspread_client_rw():
    """읽기+쓰기 권한 클라이언트."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        st.error("gspread 패키지가 없습니다.")
        st.stop()

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    return gspread.authorize(creds)


def update_timetable_cell(row_index: int, col_name: str, new_value: str) -> bool:
    """
    시간표 시트의 특정 셀 업데이트.
    row_index: 헤더 제외 1-based 행 번호
    col_name:  컬럼 이름 (예: '교실위치')
    new_value: 새 값
    """
    try:
        gc = _get_gspread_client_rw()
        sh = gc.open_by_key(st.secrets["sheets"]["timetable_id"])
        ws = sh.worksheet(st.secrets["sheets"]["timetable_sheet"])

        headers = ws.row_values(1)
        if col_name not in headers:
            st.error(f"컬럼 '{col_name}'을 시트에서 찾을 수 없습니다.")
            return False

        col_index = headers.index(col_name) + 1   # gspread는 1-based
        ws.update_cell(row_index + 1, col_index, new_value)  # +1 for header

        # 캐시 무효화
        load_timetable_sheets.clear()
        return True

    except Exception as e:
        st.error(f"업데이트 실패: {e}")
        return False


def append_timetable_row(data: dict) -> bool:
    """
    새 시간표 행 추가.
    data 예: {"요일":"월","교시":1,"반":"1-1","과목":"국어","교사명":"김영희","교실위치":"1-101","층":1}
    """
    try:
        gc = _get_gspread_client_rw()
        sh = gc.open_by_key(st.secrets["sheets"]["timetable_id"])
        ws = sh.worksheet(st.secrets["sheets"]["timetable_sheet"])

        headers = ws.row_values(1)
        row = [str(data.get(h, "")) for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")

        load_timetable_sheets.clear()
        return True

    except Exception as e:
        st.error(f"행 추가 실패: {e}")
        return False
