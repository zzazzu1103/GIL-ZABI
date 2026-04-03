"""
구글 OAuth 로그인 + 권한 관리 모듈
────────────────────────────────────
권한 등급:
  guest   — 비로그인, 시간표/지도 조회만 가능
  student — 구글 로그인, 자기 반 시간표만 조회
  teacher — 교사 계정, 시간표 수정/추가 가능
  admin   — 관리자, 모든 기능 접근

secrets.toml 필요 항목:
  [oauth]
  client_id     = "....apps.googleusercontent.com"
  client_secret = "GOCSPX-..."
  redirect_uri  = "https://gil-zabi.streamlit.app/"

  [roles]
  teachers = ["teacher1@school.kr", "teacher2@school.kr"]
  admins   = ["admin@school.kr"]
"""

import streamlit as st
import requests
import urllib.parse
import json
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

ROLE_PAGES = {
    "guest":   ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기"],
    "student": ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "🏫 내 반 설정"],
    "teacher": ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "🏫 내 반 설정", "⚙️ 관리자"],
}

ROLE_LABELS = {
    "guest":   ("👤 비로그인",  "#9E9070"),
    "student": ("🎓 학생",      "#2E6B7D"),
    "teacher": ("👩‍🏫 교사",     "#5C7A3E"),
    "admin":   ("⚙️ 관리자",    "#7D6B2E"),
}

# ── OAuth URL 생성 ─────────────────────────────────────────────
def get_oauth_url() -> str:
    try:
        client_id    = st.secrets["oauth"]["client_id"]
        redirect_uri = st.secrets["oauth"]["redirect_uri"]
    except Exception:
        return ""

    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


# ── 인가 코드 → 토큰 교환 ──────────────────────────────────────
def exchange_code_for_token(code: str) -> dict | None:
    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     st.secrets["oauth"]["client_id"],
            "client_secret": st.secrets["oauth"]["client_secret"],
            "redirect_uri":  st.secrets["oauth"]["redirect_uri"],
            "grant_type":    "authorization_code",
        }, timeout=10)
        return resp.json() if resp.ok else None
    except Exception:
        return None


# ── 토큰 → 사용자 정보 ─────────────────────────────────────────
def get_user_info(access_token: str) -> dict | None:
    try:
        resp = requests.get(
            GOOGLE_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        return resp.json() if resp.ok else None
    except Exception:
        return None


# ── 이메일 → 권한 등급 결정 ────────────────────────────────────
def resolve_role(email: str) -> str:
    try:
        admins   = st.secrets.get("roles", {}).get("admins",   [])
        teachers = st.secrets.get("roles", {}).get("teachers", [])
    except Exception:
        admins, teachers = [], []

    if email in admins:
        return "admin"
    if email in teachers:
        return "teacher"
    return "student"


# ── 로그인 처리 (URL 파라미터에서 code 감지) ───────────────────
def handle_oauth_callback():
    params = st.query_params
    if "code" not in params:
        return

    code = params["code"]
    # 이미 처리된 코드면 스킵
    if st.session_state.get("_processed_code") == code:
        return

    with st.spinner("구글 로그인 처리 중..."):
        token_data = exchange_code_for_token(code)
        if not token_data or "access_token" not in token_data:
            st.error("로그인 실패: 토큰 발급 오류")
            return

        user_info = get_user_info(token_data["access_token"])
        if not user_info:
            st.error("로그인 실패: 사용자 정보 조회 오류")
            return

        email = user_info.get("email", "")
        role  = resolve_role(email)

        st.session_state["user"] = {
            "email":   email,
            "name":    user_info.get("name", email),
            "picture": user_info.get("picture", ""),
            "role":    role,
            "login_at": datetime.now(KST).strftime("%H:%M"),
        }
        st.session_state["_processed_code"] = code

    # URL에서 code 제거 후 새로고침
    st.query_params.clear()
    st.rerun()


# ── 로그아웃 ───────────────────────────────────────────────────
def logout():
    for key in ["user", "_processed_code"]:
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


# ── 현재 유저/권한 조회 ────────────────────────────────────────
def get_current_user() -> dict | None:
    return st.session_state.get("user")

def get_role() -> str:
    user = get_current_user()
    return user["role"] if user else "guest"

def has_permission(required: str) -> bool:
    hierarchy = ["guest", "student", "teacher", "admin"]
    current   = get_role()
    return hierarchy.index(current) >= hierarchy.index(required)


# ── 사이드바 로그인 위젯 ───────────────────────────────────────
def render_auth_sidebar():
    handle_oauth_callback()

    user = get_current_user()
    role = get_role()
    label, color = ROLE_LABELS.get(role, ROLE_LABELS["guest"])

    st.sidebar.markdown("---")

    if user:
        # 로그인 상태
        pic = user.get("picture", "")
        pic_html = (
            f'<img src="{pic}" style="width:36px;height:36px;border-radius:50%;'
            f'border:2px solid #D4C9A8;vertical-align:middle;margin-right:8px;">'
            if pic else
            f'<div style="width:36px;height:36px;border-radius:50%;background:#F5F0E8;'
            f'border:2px solid #D4C9A8;display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:14px;font-weight:700;color:#7D6B2E;'
            f'vertical-align:middle;margin-right:8px;">'
            f'{user["name"][0]}</div>'
        )
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;margin-bottom:6px;">'
            f'{pic_html}'
            f'<div><div style="font-size:0.85rem;font-weight:700;color:#3D3929;">{user["name"]}</div>'
            f'<div style="font-size:0.72rem;color:#9E9070;">{user["email"]}</div></div>'
            f'</div>'
            f'<span style="display:inline-block;background:#F5F0E8;color:{color};'
            f'border:1px solid #D4C9A8;border-radius:20px;padding:2px 10px;'
            f'font-size:0.72rem;font-weight:700;">{label}</span>',
            unsafe_allow_html=True,
        )
        st.sidebar.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.sidebar.button("로그아웃", key="logout_btn", use_container_width=True):
            logout()
    else:
        # 비로그인 상태
        st.sidebar.markdown(
            f'<div style="text-align:center;margin-bottom:8px;">'
            f'<span style="display:inline-block;background:#F5F0E8;color:{color};'
            f'border:1px solid #D4C9A8;border-radius:20px;padding:2px 10px;'
            f'font-size:0.72rem;font-weight:700;">{label}</span></div>',
            unsafe_allow_html=True,
        )
        oauth_url = get_oauth_url()
        if oauth_url:
            st.sidebar.markdown(
                f'<a href="{oauth_url}" target="_self" style="display:block;text-align:center;'
                f'background:#7D6B2E;color:#FAF7F2;padding:8px;border-radius:8px;'
                f'text-decoration:none;font-size:0.85rem;font-weight:700;">'
                f'🔐 구글 계정으로 로그인</a>',
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.warning("OAuth 설정이 필요합니다.")


# ── 권한 없음 안내 화면 ────────────────────────────────────────
def show_permission_denied(required: str):
    labels = {"student":"학생", "teacher":"교사", "admin":"관리자"}
    st.markdown(
        f'<div class="card" style="text-align:center;padding:40px;">'
        f'<div style="font-size:2.5rem;margin-bottom:12px;">🔒</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:#3D3929;margin-bottom:8px;">'
        f'접근 권한이 없습니다</div>'
        f'<div style="color:#9E9070;font-size:0.9rem;">'
        f'이 페이지는 <b>{labels.get(required, required)}</b> 이상만 접근할 수 있어요.<br>'
        f'구글 계정으로 로그인해 주세요.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
