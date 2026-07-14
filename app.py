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
    # auto: 데스크톱에서는 펼치고, 모바일에서는 접은 채로 시작
    initial_sidebar_state="auto",
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

/* ── 공용 카드 내부 레이아웃 (모바일 재배치용) ──────────────── */
.card-row   { display: flex; align-items: center; gap: 16px; }
.card-split { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.card-main  { flex: 1; min-width: 0; }
.card-side  { text-align: right; flex-shrink: 0; }
.period-chip {
    min-width: 56px; text-align: center; background: #FAF7F2;
    border-radius: 10px; padding: 10px 0; flex-shrink: 0;
}
.badge-row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.loc-strong { font-size: 1.3rem; font-weight: 900; color: #7D6B2E; }

.home-card { text-align: center; }
.home-card-icon  { font-size: 1.8rem; }
.home-card-title { font-weight: 700; margin: 8px 0 4px; color: #3D3929; }
.home-card-desc  { color: #9E9070; font-size: 0.82rem; }

/* 메트릭 카드 — 신형(stMetric)·구형(metric-container) testid 모두 지원 */
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #E0D8CC; border-radius: 10px; padding: 14px;
}
[data-testid="stMetricLabel"] p { color: #9E9070 !important; }

/* ══ 모바일 (≤ 640px) ════════════════════════════════════════ */
@media (max-width: 640px) {
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        padding: 4.25rem 0.9rem 3rem !important;
    }
    div[data-testid="stVerticalBlock"] { gap: 0.75rem; }

    .main-header { padding: 14px 16px; margin-bottom: 14px; border-radius: 10px; }
    .main-header h1 { font-size: 1.3rem; }
    .main-header p  { font-size: 0.78rem; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.05rem !important; }
    h4 { font-size: 0.95rem !important; }

    /* 컬럼: 한 줄에 하나씩 길게 쌓이는 대신 2개씩 배치 */
    div[data-testid="stHorizontalBlock"] {
        flex-direction: row !important; flex-wrap: wrap !important; gap: 0.6rem !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
        flex: 1 1 calc(50% - 0.6rem) !important;
        min-width: calc(50% - 0.6rem) !important;
        width: auto !important;
    }
    /* 검색창·넓은 카드가 든 컬럼은 한 줄 전체 사용 */
    div[data-testid="stColumn"]:has(.stTextInput),
    div[data-testid="stColumn"]:has(.mob-full),
    div[data-testid="column"]:has(.stTextInput),
    div[data-testid="column"]:has(.mob-full) {
        flex-basis: 100% !important; min-width: 100% !important;
    }
    /* 홈 바로가기 카드는 한 줄에 하나씩 (가로형 카드로 전환) */
    div[data-testid="stColumn"]:has([class*="st-key-home_card_"]),
    div[data-testid="column"]:has([class*="st-key-home_card_"]) {
        flex-basis: 100% !important; min-width: 100% !important;
    }
    /* 선택과목 코드 라벨은 내용 폭만 차지하고 셀렉트가 나머지를 채움 */
    div[data-testid="stColumn"]:has(.elective-code),
    div[data-testid="column"]:has(.elective-code) {
        flex: 0 0 auto !important; min-width: 64px !important;
    }
    .home-card { display: flex; align-items: center; gap: 12px; text-align: left; }
    .home-card-icon  { font-size: 1.5rem; }
    .home-card-title { margin: 0 0 2px; }

    [data-testid="stMetric"], [data-testid="metric-container"] { padding: 10px 12px; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] p { font-size: 0.75rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.72rem !important; }

    .card { padding: 12px 14px; }
    .card-row   { gap: 10px; flex-wrap: wrap; }
    .card-split { flex-wrap: wrap; }
    .period-chip { min-width: 46px; padding: 7px 0; }
    .period-chip > div:first-child { font-size: 1.1rem !important; }
    /* 오른쪽 정보(교실·층·상태 배지)는 카드 하단 한 줄로 이동 */
    .card-side {
        flex-basis: 100%; min-width: 0 !important; text-align: left !important;
        display: flex; align-items: center; flex-wrap: wrap; gap: 4px 10px;
        border-top: 1px dashed #E0D8CC; padding-top: 8px; margin-top: 2px;
    }
    .card-side br { display: none; }
    .card-side > div { margin: 0 !important; }
    .card-side .status-badge { margin-left: auto; }
    .loc-strong { font-size: 1.05rem; }

    .role-banner { padding: 6px 10px; font-size: 0.75rem; margin-bottom: 10px; }
    .status-badge { font-size: 0.68rem; padding: 2px 8px; }
    .stButton > button { padding: 0.45rem 1rem !important; font-size: 0.85rem !important; }

    /* 주간·학년 피벗 표 압축 (가로 스크롤은 유지) */
    .tt-pivot { -webkit-overflow-scrolling: touch; }
    .tt-pivot table { border-spacing: 3px !important; }
    .tt-pivot td { padding: 6px 4px !important; font-size: 0.74rem !important; border-radius: 8px !important; }
    .tt-pivot th { padding: 6px 3px !important; font-size: 0.72rem !important; min-width: 38px !important; border-radius: 8px !important; }
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
    if "nav_target" in st.session_state:
        st.session_state["nav_page"] = st.session_state.pop("nav_target")
    if st.session_state.get("nav_page") not in pages:
        st.session_state.pop("nav_page", None)
    page  = st.radio("메뉴", pages, label_visibility="collapsed", key="nav_page")

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
