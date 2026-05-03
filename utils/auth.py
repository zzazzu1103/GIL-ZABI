"""
구글 OAuth 로그인 + 권한 관리 모듈
새로고침 후에도 로그인 + 개인설정 상태 유지 (서버사이드 토큰 파일)
학교 계정(@jeohyeon.hs.kr)만 로그인 허용
"""

import streamlit as st
import requests
import urllib.parse
import json
import os
import secrets
import time as _time
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

# ── 학교 계정 도메인 ──────────────────────────────────────────
ALLOWED_DOMAIN = "jeohyeon.hs.kr"

_TOKEN_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "_sessions"
)
_TOKEN_TTL = 60 * 60 * 24 * 7  # 7일

ROLE_LABELS = {
    "guest":   ("👤 비로그인",  "#9E9070"),
    "student": ("🎓 학생",      "#2E6B7D"),
    "teacher": ("👩‍🏫 교사",     "#5C7A3E"),
    "admin":   ("⚙️ 관리자",    "#7D6B2E"),
}

ROLE_COLORS = {
    "guest":   "#9E9070",
    "student": "#2E6B7D",
    "teacher": "#5C7A3E",
    "admin":   "#7D6B2E",
}

ROLE_PAGES = {
    "guest":   ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기"],
    "student": ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "👤 개인 설정"],
    "teacher": ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "👤 개인 설정", "⚙️ 관리자"],
    "admin":   ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "👤 개인 설정", "⚙️ 관리자"],
}


# ── 도메인 검사 ───────────────────────────────────────────────

def is_allowed_email(email: str) -> bool:
    """학교 계정 도메인인지 확인. secrets에 allowed_domain 있으면 우선 사용."""
    try:
        domain = st.secrets.get("roles", {}).get("allowed_domain", ALLOWED_DOMAIN)
    except Exception:
        domain = ALLOWED_DOMAIN
    return email.lower().endswith(f"@{domain}")


# ── 서버사이드 세션 토큰 ──────────────────────────────────────

def _ensure_token_dir():
    os.makedirs(_TOKEN_DIR, exist_ok=True)

def _token_path(token: str) -> str:
    safe = "".join(c for c in token if c.isalnum() or c in "-_")
    return os.path.join(_TOKEN_DIR, f"{safe}.json")

def _save_session_token(token: str, user_data: dict):
    _ensure_token_dir()
    with open(_token_path(token), "w", encoding="utf-8") as f:
        json.dump({"user": user_data, "expires": _time.time() + _TOKEN_TTL}, f, ensure_ascii=False)

def _load_session_token(token: str) -> dict | None:
    path = _token_path(token)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if _time.time() > payload.get("expires", 0):
            os.remove(path)
            return None
        return payload.get("user")
    except Exception:
        return None

def _delete_session_token(token: str):
    path = _token_path(token)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass

def _cleanup_expired_tokens():
    try:
        for fname in os.listdir(_TOKEN_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(_TOKEN_DIR, fname)
            try:
                with open(fpath) as f:
                    payload = json.load(f)
                if _time.time() > payload.get("expires", 0):
                    os.remove(fpath)
            except Exception:
                pass
    except Exception:
        pass


def _restore_user_settings(email: str):
    try:
        from utils.user_settings import apply_user_settings_to_session
        apply_user_settings_to_session(email)
    except Exception:
        pass


# ── OAuth 헬퍼 ────────────────────────────────────────────────

def get_oauth_url() -> str:
    try:
        client_id    = st.secrets["oauth"]["client_id"]
        redirect_uri = st.secrets["oauth"]["redirect_uri"]
    except Exception as e:
        st.error(f"❌ secrets.toml 읽기 실패: {e}")
        return ""
    if not client_id or not redirect_uri:
        st.error("❌ client_id 또는 redirect_uri가 비어 있습니다.")
        return ""
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
        "hd":            ALLOWED_DOMAIN,  # 구글 로그인 화면에서 학교 계정 우선 표시
    }
    return GOOGLE_AUTH_URL + "?" + urllib.parse.urlencode(params)


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


def resolve_role(email: str) -> str:
    try:
        admins   = list(st.secrets.get("roles", {}).get("admin_emails",   []))
        teachers = list(st.secrets.get("roles", {}).get("teacher_emails", []))
    except Exception:
        admins, teachers = [], []
    if email in admins:   return "admin"
    if email in teachers: return "teacher"
    return "student"


# ── 핵심: 로그인 상태 복원 + OAuth 콜백 처리 ─────────────────

def handle_oauth_callback():
    if "user" in st.session_state:
        if "my_class" not in st.session_state:
            _restore_user_settings(st.session_state["user"].get("email", ""))
        return

    params = st.query_params

    # sid로 세션 복원
    sid = params.get("sid")
    if sid:
        user_data = _load_session_token(sid)
        if user_data:
            st.session_state["user"] = user_data
            st.session_state["_sid"] = sid
            _restore_user_settings(user_data.get("email", ""))
            return
        else:
            st.query_params.clear()
            st.rerun()

    if "code" not in params:
        return

    code = params["code"]
    if st.session_state.get("_processed_code") == code:
        return

    with st.spinner("구글 로그인 처리 중..."):
        token_data = exchange_code_for_token(code)
        if not token_data or "access_token" not in token_data:
            st.error(f"로그인 실패: 토큰 발급 오류")
            st.query_params.clear()
            return

        user_info = get_user_info(token_data["access_token"])
        if not user_info:
            st.error("로그인 실패: 사용자 정보 조회 오류")
            st.query_params.clear()
            return

        email = user_info.get("email", "")

        # ── 학교 계정 도메인 검사 ──────────────────────────────
        if not is_allowed_email(email):
            st.query_params.clear()
            st.error(
                f"⛔ 학교 계정으로만 로그인할 수 있어요.\n\n"
                f"`@{ALLOWED_DOMAIN}` 계정을 사용해 주세요.\n\n"
                f"현재 계정: `{email}`"
            )
            st.stop()

        role = resolve_role(email)

        user_data = {
            "email":    email,
            "name":     user_info.get("name", email),
            "picture":  user_info.get("picture", ""),
            "role":     role,
            "login_at": datetime.now(KST).strftime("%H:%M"),
        }

        sid = secrets.token_urlsafe(32)
        _save_session_token(sid, user_data)
        _cleanup_expired_tokens()

        st.session_state["user"] = user_data
        st.session_state["_sid"] = sid
        st.session_state["_processed_code"] = code
        _restore_user_settings(email)

    st.query_params.clear()
    st.query_params["sid"] = sid
    st.rerun()


def logout():
    sid = st.session_state.get("_sid")
    if sid:
        _delete_session_token(sid)
    for key in ["user", "_processed_code", "_sid",
                "my_class", "tangu_map", "my_subjects", "my_classes",
                "_set_grade", "_set_class"]:
        st.session_state.pop(key, None)
    st.query_params.clear()
    st.rerun()


# ── 유틸 함수 ─────────────────────────────────────────────────

def get_current_user() -> dict | None:
    return st.session_state.get("user")

def get_user() -> dict:
    user = st.session_state.get("user")
    return user if user else {"name": "비로그인", "email": "", "role": "guest"}

def get_role() -> str:
    user = get_current_user()
    return user["role"] if user else "guest"

def has_permission(required: str) -> bool:
    hierarchy = ["guest", "student", "teacher", "admin"]
    return hierarchy.index(get_role()) >= hierarchy.index(required)

def require_role(required: str) -> bool:
    if has_permission(required):
        return True
    show_permission_denied(required)
    return False


def render_auth_sidebar():
    user = get_current_user()
    role = get_role()
    label, color = ROLE_LABELS.get(role, ROLE_LABELS["guest"])

    st.markdown("---")

    if user:
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
        st.markdown(
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
        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
        if st.button("로그아웃", key="logout_btn", use_container_width=True):
            logout()
    else:
        st.markdown(
            f'<div style="text-align:center;margin-bottom:8px;">'
            f'<span style="display:inline-block;background:#F5F0E8;color:{color};'
            f'border:1px solid #D4C9A8;border-radius:20px;padding:2px 10px;'
            f'font-size:0.72rem;font-weight:700;">{label}</span></div>',
            unsafe_allow_html=True,
        )
        oauth_url = get_oauth_url()
        if oauth_url:
            st.link_button("🔐 학교 계정으로 로그인", oauth_url, use_container_width=True)
            st.markdown(
                f'<div style="text-align:center;font-size:0.72rem;color:#B8A05A;margin-top:6px;">'
                f'@{ALLOWED_DOMAIN} 계정만 가능</div>',
                unsafe_allow_html=True,
            )
        else:
            st.warning("OAuth 설정이 필요합니다.")


def show_permission_denied(required: str):
    labels = {"student": "학생", "teacher": "교사", "admin": "관리자"}
    st.markdown(
        f'<div class="card" style="text-align:center;padding:40px;">'
        f'<div style="font-size:2.5rem;margin-bottom:12px;">🔒</div>'
        f'<div style="font-size:1.1rem;font-weight:700;color:#3D3929;margin-bottom:8px;">'
        f'접근 권한이 없습니다</div>'
        f'<div style="color:#9E9070;font-size:0.9rem;">'
        f'이 페이지는 <b>{labels.get(required, required)}</b> 이상만 접근할 수 있어요.<br>'
        f'학교 계정으로 로그인해 주세요.</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
