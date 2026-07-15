import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Hugging Face Spaces 지원 ──────────────────────────────────
# HF는 시크릿을 환경변수로만 주입하므로, SECRETS_TOML 환경변수에 담긴
# secrets.toml 전체 내용을 앱 시작 시 파일로 만들어 st.secrets가 읽게 한다.
_secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".streamlit", "secrets.toml")
if not os.path.exists(_secrets_path) and os.environ.get("SECRETS_TOML"):
    os.makedirs(os.path.dirname(_secrets_path), exist_ok=True)
    with open(_secrets_path, "w", encoding="utf-8") as _f:
        _f.write(os.environ["SECRETS_TOML"])

import streamlit as st
from utils.auth import (
    handle_oauth_callback, render_auth_sidebar,
    get_role, get_user, get_current_user, has_permission,
    get_oauth_url, logout,
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

/* ── 스트림릿 기본 UI 정리 ───────────────────────────────────
   하단의 'Hosted with Streamlit' 배지·푸터·배포 버튼이 화면(특히
   모바일 하단 탭바)을 가리므로 숨긴다. 배지는 배포 세대에 따라
   클래스명이 달라 알려진 패턴을 모두 커버한다. */
footer,
.stAppDeployButton,
[data-testid="stAppDeployButton"],
[class*="viewerBadge"],
[class*="_profileContainer"],
[class*="_profilePreview"],
[class*="_viewerBadge"] {
    display: none !important;
}

/* 모바일 하단 내비게이션 — 데스크톱에서는 숨김 (미디어쿼리에서 표시) */
div[class*="st-key-mobile_nav"] { display: none; }

/* ══ 모바일 (≤ 640px) ════════════════════════════════════════ */
@media (max-width: 640px) {
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        /* 아래 여백은 하단 탭바에 가리지 않도록 넉넉하게 */
        padding: 4.25rem 0.9rem 5.5rem !important;
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
    /* 선생님 목록 버튼: 컬럼별로 버튼이 쌓이는 구조라 2열로 줄이면
       2명씩·1명씩 섞여 보이므로 모바일에서도 3열 그리드를 유지 */
    div[data-testid="stColumn"]:has([class*="st-key-tsbtn_"]),
    div[data-testid="column"]:has([class*="st-key-tsbtn_"]) {
        flex: 1 1 calc(33.333% - 0.6rem) !important;
        min-width: calc(33.333% - 0.6rem) !important;
    }
    div[data-testid="stColumn"]:has([class*="st-key-tsbtn_"]) .stButton > button {
        padding: 0.45rem 0.3rem !important; font-size: 0.82rem !important;
    }
    .home-card { display: flex; align-items: center; gap: 12px; text-align: left; }
    .home-card-icon  { font-size: 1.5rem; }
    .home-card-title { margin: 0 0 2px; }

    /* 메트릭: 모바일에서만 카드 형태 + 압축 (데스크톱은 기존 디자인 유지) */
    [data-testid="stMetric"], [data-testid="metric-container"] {
        background: #fff; border: 1px solid #E0D8CC; border-radius: 10px;
        padding: 10px 12px; height: 100%; box-sizing: border-box;
    }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; }
    [data-testid="stMetricLabel"] p { color: #9E9070 !important; font-size: 0.75rem !important; }
    [data-testid="stMetricDelta"] { font-size: 0.72rem !important; }

    /* 나란히 놓인 메트릭·카드 높이 맞춤 (모바일 전용) */
    div[data-testid="stHorizontalBlock"] { align-items: stretch; }
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"],
    div[data-testid="column"]  > div[data-testid="stVerticalBlock"] { height: 100%; }
    div[data-testid="stVerticalBlock"] > div:has([data-testid="stMetric"]),
    div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stMarkdown"] .card),
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-home_card_"]) {
        flex: 1 1 auto;
    }
    div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stMarkdown"] .card) [data-testid="stMarkdown"],
    div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stMarkdown"] .card) [data-testid="stMarkdown"] > div,
    div[data-testid="stVerticalBlock"] > div:has(> [data-testid="stMarkdown"] .card) .card {
        height: 100%; box-sizing: border-box;
    }

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

    /* ── 하단 탭바 내비게이션 (앱처럼 아이콘 + 작은 라벨) ──────
       주의: st-key-mobile_nav 클래스는 stVerticalBlock 자체에 붙으므로
       이 요소를 직접 가로 flex 컨테이너로 만든다. */
    div[class*="st-key-mobile_nav"] {
        display: flex !important;
        flex-direction: row !important;
        align-items: stretch !important;
        gap: 2px !important;
        height: auto !important;
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 9999;
        background: #FFFFFF;
        border-top: 1px solid #E0D8CC;
        box-shadow: 0 -2px 12px rgba(0,0,0,0.06);
        padding: 4px 6px calc(4px + env(safe-area-inset-bottom, 0px)) !important;
        margin: 0 !important;
    }
    div[class*="st-key-mobile_nav"] > div {
        flex: 1 1 0 !important; min-width: 0 !important; width: auto !important;
    }
    div[class*="st-key-mobile_nav"] .stButton,
    div[class*="st-key-mobile_nav"] .stLinkButton { width: 100% !important; }
    div[class*="st-key-mobile_nav"] .stButton > button,
    div[class*="st-key-mobile_nav"] .stLinkButton > a {
        display: block !important; width: 100% !important;
        background: transparent !important;
        color: #9E9070 !important;
        border: none !important; box-shadow: none !important;
        text-decoration: none !important; text-align: center !important;
        font-size: 1.15rem !important; font-weight: 600 !important;
        padding: 5px 0 !important; border-radius: 10px !important;
        line-height: 1.35 !important; min-height: 0 !important;
    }
    div[class*="st-key-mobile_nav"] .stButton > button p,
    div[class*="st-key-mobile_nav"] .stLinkButton > a p {
        line-height: 1.3; white-space: nowrap; font-size: inherit;
    }
    div[class*="st-key-mobile_nav"] .stButton > button small,
    div[class*="st-key-mobile_nav"] .stLinkButton > a small { font-size: 0.62rem; }
    div[class*="st-key-mobile_nav"] .stButton > button:hover,
    div[class*="st-key-mobile_nav"] .stButton > button:active,
    div[class*="st-key-mobile_nav"] .stLinkButton > a:hover {
        background: #F5F0E8 !important; color: #7D6B2E !important;
    }
    /* 현재 페이지 강조 */
    div[class*="st-key-mobile_nav"] .stButton > button[kind="primary"] {
        background: #F5F0E8 !important; color: #7D6B2E !important;
    }
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

# ── 모바일 하단 탭바 (CSS로 모바일에서만 표시, 데스크톱에선 숨김) ──
with st.container(key="mobile_nav"):
    for p in pages:
        icon, _, name = p.partition(" ")
        if st.button(
            f"{icon}  \n:small[{name}]",
            key=f"mnav_{p}",
            type="primary" if p == page else "secondary",
            use_container_width=True,
        ):
            if p != page:
                st.session_state["nav_target"] = p
                st.rerun()

    # 로그인/로그아웃 탭 — get_user()는 비로그인이어도 더미 dict를 돌려줘
    # 항상 참이므로, 실제 로그인 여부는 get_current_user()(None 가능)로 판정
    if get_current_user():
        if st.button("🚪  \n:small[로그아웃]", key="mnav_logout", use_container_width=True):
            logout()
    else:
        oauth_url = get_oauth_url()
        if oauth_url:
            st.link_button("🔐  \n:small[로그인]", oauth_url, use_container_width=True)
