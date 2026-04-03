"""
pages/my_settings.py
─────────────────────
로그인한 사용자의 개인 설정 페이지
- 학생: 내 반 선택 → 저장
- 교사: 담당 과목 / 반 선택 → 저장
"""

import streamlit as st
from utils.helpers import load_timetable, load_teachers
from utils.auth import get_current_user, get_role
from utils.user_settings import load_user_settings, save_user_settings


def show():
    user = get_current_user()
    role = get_role()

    st.markdown("""
    <div class="main-header">
        <h1>⚙️ 개인 설정</h1>
        <p>내 정보를 설정하면 맞춤형 시간표와 위치 정보를 바로 확인할 수 있어요</p>
    </div>
    """, unsafe_allow_html=True)

    if not user:
        st.warning("🔒 로그인 후 이용할 수 있어요.")
        return

    email = user["email"]
    saved = load_user_settings(email)

    st.markdown(f"""
    <div class="card" style="display:flex;align-items:center;gap:14px;padding:16px 20px;">
        <div style="font-size:2rem;">{"🎓" if role=="student" else "👩‍🏫" if role=="teacher" else "⚙️"}</div>
        <div>
            <div style="font-weight:700;font-size:1rem;color:#3D3929;">{user['name']}</div>
            <div style="color:#9E9070;font-size:0.82rem;">{email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    df = load_timetable()
    teachers_df = load_teachers()

    # ── 학생 설정 ──────────────────────────────────────────────
    if role in ("student", "admin"):
        st.markdown("### 🏫 내 반 설정")
        st.markdown(
            '<div style="color:#9E9070;font-size:0.85rem;margin-bottom:12px;">'
            '내 반을 설정하면 홈과 시간표에서 바로 내 반 정보가 표시돼요.</div>',
            unsafe_allow_html=True
        )

        classes = sorted(df["반"].unique().tolist())
        current_class = saved.get("my_class", "")
        default_idx = classes.index(current_class) if current_class in classes else 0

        sel_class = st.selectbox("내 반 선택", classes, index=default_idx, key="set_class")

        if current_class:
            st.success(f"현재 설정: **{current_class}**")

        if st.button("💾 반 설정 저장", type="primary", key="save_class"):
            saved["my_class"] = sel_class
            save_user_settings(email, saved)
            st.session_state["my_class"] = sel_class
            st.success(f"✅ {sel_class}반으로 저장됐어요!")
            st.balloons()

    # ── 교사 설정 ──────────────────────────────────────────────
    if role in ("teacher", "admin"):
        st.markdown("---")
        st.markdown("### 👩‍🏫 담당 과목 / 반 설정")
        st.markdown(
            '<div style="color:#9E9070;font-size:0.85rem;margin-bottom:12px;">'
            '담당 과목과 반을 설정하면 선생님 찾기와 관리자 페이지에서 빠르게 접근할 수 있어요.</div>',
            unsafe_allow_html=True
        )

        all_subjects = sorted(df["과목"].unique().tolist())
        all_classes  = sorted(df["반"].unique().tolist())

        saved_subjects = saved.get("my_subjects", [])
        saved_classes  = saved.get("my_classes",  [])

        sel_subjects = st.multiselect(
            "담당 과목 선택",
            all_subjects,
            default=[s for s in saved_subjects if s in all_subjects],
            key="set_subjects"
        )
        sel_classes = st.multiselect(
            "담당 반 선택",
            all_classes,
            default=[c for c in saved_classes if c in all_classes],
            key="set_classes"
        )

        if st.button("💾 담당 설정 저장", type="primary", key="save_teacher"):
            saved["my_subjects"] = sel_subjects
            saved["my_classes"]  = sel_classes
            save_user_settings(email, saved)
            st.session_state["my_subjects"] = sel_subjects
            st.session_state["my_classes"]  = sel_classes
            st.success(f"✅ 담당 과목 {len(sel_subjects)}개, 반 {len(sel_classes)}개 저장됐어요!")

    # ── 설정 초기화 ────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚠️ 설정 초기화"):
        st.warning("저장된 모든 개인 설정이 삭제돼요.")
        if st.button("초기화", key="reset_settings"):
            save_user_settings(email, {})
            for key in ["my_class", "my_subjects", "my_classes"]:
                st.session_state.pop(key, None)
            st.success("✅ 설정이 초기화됐어요.")
            st.rerun()
