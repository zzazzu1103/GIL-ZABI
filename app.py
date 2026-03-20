import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="길잡이 GIL-ZABI",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 전역 CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=Space+Grotesk:wght@400;600;700&display=swap');

/* 기본 */
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', sans-serif;
}

/* 배경 */
.stApp {
    background: #0D1117;
    color: #E6EDF3;
}

/* 사이드바 */
section[data-testid="stSidebar"] {
    background: #161B22;
    border-right: 1px solid #30363D;
}
section[data-testid="stSidebar"] * {
    color: #E6EDF3 !important;
}

/* 헤더 */
.main-header {
    background: linear-gradient(135deg, #1F2937 0%, #111827 100%);
    border: 1px solid #374151;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.main-header::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(78,205,196,0.08) 0%, transparent 70%);
    pointer-events: none;
}
.main-header h1 {
    font-size: 2.2rem;
    font-weight: 900;
    background: linear-gradient(90deg, #4ECDC4, #FF6B35);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 6px 0;
}
.main-header p {
    color: #8B949E;
    font-size: 0.95rem;
    margin: 0;
}

/* 상태 뱃지 */
.status-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.05em;
}
.badge-current  { background: rgba(255,107,53,0.15);  color: #FF6B35;  border: 1px solid #FF6B35; }
.badge-next     { background: rgba(78,205,196,0.15);  color: #4ECDC4;  border: 1px solid #4ECDC4; }
.badge-done     { background: rgba(149,165,166,0.10); color: #95A5A6;  border: 1px solid #95A5A6; }
.badge-upcoming { background: rgba(44,62,80,0.30);    color: #BDC3C7;  border: 1px solid #4A5568; }

/* 카드 */
.card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.card:hover { border-color: #4ECDC4; }
.card-current { border-color: #FF6B35 !important; background: rgba(255,107,53,0.06); }
.card-next    { border-color: #4ECDC4 !important; background: rgba(78,205,196,0.06); }

/* 선택 박스 */
div[data-baseweb="select"] > div {
    background: #161B22 !important;
    border-color: #30363D !important;
    color: #E6EDF3 !important;
}

/* 버튼 */
.stButton > button {
    background: linear-gradient(135deg, #4ECDC4, #44B5AC) !important;
    color: #0D1117 !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.5rem !important;
}

/* 입력 필드 */
.stTextInput > div > div > input {
    background: #161B22 !important;
    border-color: #30363D !important;
    color: #E6EDF3 !important;
}

/* 구분선 */
hr { border-color: #30363D; }

/* metric */
[data-testid="metric-container"] {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 16px;
}

/* info/warning box */
.stAlert { border-radius: 10px; }

/* 탭 */
button[data-baseweb="tab"] {
    color: #8B949E !important;
    font-weight: 600;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #4ECDC4 !important;
    border-bottom-color: #4ECDC4 !important;
}
</style>
""", unsafe_allow_html=True)

# ── 사이드바 네비게이션 ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 16px 0 24px 0;'>
        <div style='font-size:2.5rem;'>🗺️</div>
        <div style='font-size:1.3rem; font-weight:900; 
                    background:linear-gradient(90deg,#4ECDC4,#FF6B35);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
            길잡이
        </div>
        <div style='font-size:0.7rem; color:#8B949E; letter-spacing:0.15em;'>GIL-ZABI v1.0</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "메뉴",
        ["🏠 홈", "📅 시간표 조회", "🗺️ 학교 지도", "🔍 선생님 찾기", "⚙️ 관리자"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        "<div style='color:#8B949E; font-size:0.75rem; text-align:center;'>"
        "ⓘ 데이터는 Google Sheets와 연동됩니다<br><br>"
        "팀 GIL-ZABI · 2025</div>",
        unsafe_allow_html=True,
    )

# ── 페이지 라우팅 ─────────────────────────────────────────────────────────────
if page == "🏠 홈":
    from pages.home import show
    show()
elif page == "📅 시간표 조회":
    from pages.timetable import show
    show()
elif page == "🗺️ 학교 지도":
    from pages.map_view import show
    show()
elif page == "🔍 선생님 찾기":
    from pages.teacher_search import show
    show()
elif page == "⚙️ 관리자":
    from pages.admin import show
    show()
