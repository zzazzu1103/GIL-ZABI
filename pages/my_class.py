"""내 반 설정 페이지 — 학생 로그인 후 첫 접속 시 반 선택"""
import streamlit as st
from utils.helpers import load_timetable
from utils.auth import get_current_user, get_role

def show():
    user = get_current_user()
    role = get_role()

    st.markdown("""
    <div class="main-header">
        <h1>🏫 내 반 설정</h1>
        <p>로그인 후 내 반을 선택하면 맞춤 시간표가 표시돼요</p>
    </div>
    """, unsafe_allow_html=True)

    if not user:
        st.info("로그인 후 이용할 수 있어요.")
        return

    df = load_timetable()
    classes = sorted(df["반"].unique().tolist())
    current = st.session_state.get("my_class", "")

    if current:
        st.success(f"현재 설정된 반: **{current}**")

    st.markdown("### 내 반 선택")
    sel = st.selectbox("반을 선택하세요", classes,
                       index=classes.index(current) if current in classes else 0)

    if st.button("저장", type="primary"):
        st.session_state["my_class"] = sel
        st.success(f"✅ {sel}반으로 설정됐어요! 홈으로 이동하세요.")
        st.balloons()
