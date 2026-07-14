import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from utils.auth import (
    handle_oauth_callback, render_auth_sidebar,
    get_role, get_user, has_permission,
    ROLE_PAGES, ROLE_LABELS, ROLE_COLORS
)

st.set_page_config(
    page_title="길잡이 GIL-ZABI",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── OAuth 콜백 처리 (최상단) ──────────────────────────────────
handle_oauth_callback()

# ── 전역 CSS ─────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

.stApp { background: #FAF7F2; color: #3D3929; }

section[data-testid="stSidebar"] {
    background: #F2EDE4;
    border-right: 1px solid #E0D8CC;
}
section[data-testid="stSidebar"] * { color: #3D3929 !important; }

/* pages/ 폴더 기반 스트림릿 기본 내비게이션(중복 메뉴)은 숨기고
   위 사이드바 라디오 메뉴만 사용한다. */
div[data-testid="stSidebarNav"] { display: none; }

.main-header {
    background: #fff;
    border: 1px solid #E0D8CC;
    border-left: 4px solid #7D6B2E;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
}
.main-header h1 { font-size: 2rem; font-weight: 900; color: #3D3929; margin: 0 0 6px 0; }
.main-header h1 span { color: #7D6B2E; }
.main-header p { color: #9E9070; font-size: 0.9rem; margin: 0; }

.status-badge {
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 0.72rem; font-weight: 700;
}
.badge-current  { background:#FEF3C7; color:#92400E; border:1px solid #D97706; }
.badge-next     { background:#ECFDF5; color:#065F46; border:1px solid #059669; }
.badge-done     { background:#F5F0E8; color:#9E9070; border:1px solid #D4C9A8; }
.badge-upcoming { background:#F5F0E8; color:#9E9070; border:1px solid #E0D8CC; }

.card {
    background: #fff; border: 1px solid #E0D8CC;
    border-radius: 10px; padding: 18px; margin-bottom: 10px;
    transition: border-color 0.2s;
}
.card:hover { border-color: #B8A05A; }
.card-current { border-color:#D97706 !important; border-left:3px solid #D97706 !important; background:#FFFBF0; }
.card-next    { border-color:#059669 !important; border-left:3px solid #059669 !important; background:#F6FFFA; }

.role-banner {
    background: #fff; border: 1px solid #E0D8CC; border-radius: 8px;
    padding: 8px 14px; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px; font-size: 0.82rem;
}

div[data-baseweb="select"] > div {
    background: #fff !important; border-color: #E0D8CC !important; color: #3D3929 !important;
}
.stButton > button {
    background: #7D6B2E !important; color: #FAF7F2 !important;
    border: none !important; font-weight: 700 !important;
    border-radius: 8px !important; padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { background: #6A5A26 !important; }
.stTextInput > div > div > input {
    background: #fff !important; border-color: #E0D8CC !important; color: #3D3929 !important;
}
hr { border-color: #E0D8CC; }
[data-testid="metric-container"] {
    background: #fff; border: 1px solid #E0D8CC; border-radius: 10px; padding: 14px;
}
[data-testid="metric-container"] label { color: #9E9070 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #3D3929 !important; }
[data-testid="metric-container"] [data-testid="stMetricDelta"] { color: #7D6B2E !important; }
button[data-baseweb="tab"] { color: #9E9070 !important; font-weight: 600; }
button[data-baseweb="tab"][aria-selected="true"] {
    color: #7D6B2E !important; border-bottom-color: #7D6B2E !important;
}
h1, h2, h3, h4 { color: #3D3929 !important; }
.stCheckbox label { color: #3D3929 !important; }
.stDownloadButton > button {
    background: #F5F0E8 !important; color: #7D6B2E !important;
    border: 1px solid #D4C9A8 !important; font-weight: 600 !important;
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 20px 0 20px 0;'>
        <div style='font-size:2.2rem;'>🗺️</div>
        <div style='font-size:1.2rem; font-weight:900; color:#3D3929; margin-top:6px;'>길잡이</div>
        <div style='font-size:0.65rem; color:#9E9070; letter-spacing:0.15em; margin-top:2px;'>GIL-ZABI v1.0</div>
        <div style='width:36px; height:2px; background:#7D6B2E; margin:10px auto 0;'></div>
    </div>
    """, unsafe_allow_html=True)

    render_auth_sidebar()

    role  = get_role()
    pages = ROLE_PAGES[role]
    page  = st.radio("메뉴", pages, label_visibility="collapsed")

    st.markdown(
        "<div style='color:#9E9070;font-size:0.72rem;text-align:center;'>"
        "팀 GIL-ZABI · 2026</div>",
        unsafe_allow_html=True,
    )

# ── 권한 배너 (로그인 시) ──────────────────────────────────────
role = get_role()
if role != "guest":
    user = get_user()
    color = ROLE_COLORS.get(role, "#9E9070")
    label_text = ROLE_LABELS.get(role, ("", ""))[0]
    icon = "🎓" if role == "student" else "👩‍🏫" if role == "teacher" else "⚙️"
    st.markdown(
        f'<div class="role-banner">'
        f'<span style="font-size:1rem;">{icon}</span>'
        f'<span style="color:#3D3929;"><b>{user["name"]}</b>님 환영해요</span>'
        f'<span style="margin-left:auto;color:{color};font-weight:700;">{label_text}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── 페이지 라우팅 ─────────────────────────────────────────────
if page == "🏠 홈":
    from pages.home import show; show()
elif page == "🗺️ 학교 지도":
    from pages.map_view import show; show()
elif page == "🔍 선생님 찾기":
    from pages.teacher_search import show; show()
elif page == "👤 개인 설정":
    from pages.my_settings import show; show()
elif page == "⚙️ 관리자":
    if has_permission("teacher"):
        from pages.admin import show; show()
    else:
        from utils.auth import show_permission_denied
        show_permission_denied("teacher")
