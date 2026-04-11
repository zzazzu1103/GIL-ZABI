"""
pages/my_settings.py
─────────────────────
로그인한 사용자의 개인 설정 페이지
- 학생: 학년/반 선택 + 탐구 과목 개인화
- 교사: 담당 과목/반 선택
"""

import streamlit as st
from utils.helpers import load_timetable, load_teachers
from utils.auth import get_current_user, get_role
from utils.user_settings import (
    load_user_settings, save_user_settings, TANGU_SUBJECTS
)


def _get_tangu_options_for_code(timetable_df, my_class, tangu_code):
    """특정 반의 특정 탐구 코드에 해당하는 (교사명, 교실위치) 조합 목록 반환"""
    if not my_class:
        return []
    rows = timetable_df[
        (timetable_df["반"] == my_class) &
        (timetable_df["과목"] == tangu_code)
    ][["교사명", "교실위치"]].drop_duplicates()
    if rows.empty:
        return []
    options = []
    for _, r in rows.iterrows():
        options.append({
            "교사명": r["교사명"],
            "교실위치": str(r["교실위치"]),
            "label": f"{r['교사명']} 선생님 · {r['교실위치']}호",
        })
    return options


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

    role_icon = "🎓" if role == "student" else "👩‍🏫" if role == "teacher" else "⚙️"
    st.markdown(f"""
    <div class="card" style="display:flex;align-items:center;gap:14px;padding:16px 20px;">
        <div style="font-size:2rem;">{role_icon}</div>
        <div>
            <div style="font-weight:700;font-size:1rem;color:#3D3929;">{user['name']}</div>
            <div style="color:#9E9070;font-size:0.82rem;">{email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    df = load_timetable()
    teachers_df = load_teachers()

    # ── 학생 설정 ──────────────────────────────────────────────────────────
    if role in ("student", "admin"):

        # 1) 학년/반 선택
        st.markdown("### 🏫 내 학년 · 반 설정")
        st.markdown(
            '<div style="color:#9E9070;font-size:0.85rem;margin-bottom:16px;">'
            '학년과 반을 설정하면 홈·시간표·지도에서 내 반 정보가 바로 표시돼요.</div>',
            unsafe_allow_html=True
        )

        all_classes = sorted(df["반"].unique().tolist())

        # 학년별로 그룹화
        grades = {}
        for c in all_classes:
            try:
                grade = int(c.split("-")[0])
            except Exception:
                grade = 0
            grades.setdefault(grade, []).append(c)

        current_class = saved.get("my_class", "")

        # 학년 먼저 선택
        grade_list = sorted(grades.keys())
        current_grade = int(current_class.split("-")[0]) if current_class and "-" in current_class else grade_list[0]
        sel_grade = st.selectbox(
            "학년 선택",
            grade_list,
            index=grade_list.index(current_grade) if current_grade in grade_list else 0,
            format_func=lambda x: f"{x}학년",
            key="set_grade"
        )

        # 해당 학년의 반 목록
        class_list = grades.get(sel_grade, [])
        current_idx = class_list.index(current_class) if current_class in class_list else 0
        sel_class = st.selectbox(
            "반 선택",
            class_list,
            index=current_idx,
            key="set_class"
        )

        if current_class:
            st.success(f"현재 설정된 반: **{current_class}**")

        # ── 2) 탐구 과목 개인화 ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔬 탐구 과목 설정")
        st.markdown(
            '<div style="color:#9E9070;font-size:0.85rem;margin-bottom:16px;">'
            '탐구 A~E 과목은 학생마다 담당 선생님과 교실이 달라요.<br>'
            '내 수업 반에 맞게 선택해 주세요. 저장하면 시간표에 정확한 정보가 표시돼요.</div>',
            unsafe_allow_html=True
        )

        # 선택 중인 반 기준으로 탐구 과목 옵션 조회
        preview_class = sel_class  # 저장 전이라도 선택한 반 기준으로 미리 보기
        saved_tangu = saved.get("tangu_map", {})

        new_tangu_map = {}
        tangu_found_any = False

        for tangu_code in ["탐구A", "탐구B", "탐구C", "탐구D", "탐구E1", "탐구E2"]:
            options = _get_tangu_options_for_code(df, preview_class, tangu_code)
            if not options:
                continue
            tangu_found_any = True

            st.markdown(f"**{tangu_code}**")
            option_labels = [o["label"] for o in options]

            # 이전 저장값 찾기
            prev = saved_tangu.get(tangu_code, {})
            prev_label = f"{prev.get('교사명','')} 선생님 · {prev.get('교실위치','')}" if prev else None
            default_idx = option_labels.index(prev_label) if prev_label in option_labels else 0

            if len(options) == 1:
                # 선택지가 하나면 자동 선택
                chosen_label = option_labels[0]
                st.markdown(
                    f'<div style="background:#F5F0E8;border-radius:8px;padding:8px 12px;'
                    f'font-size:0.88rem;color:#7D6B2E;margin-bottom:12px;">'
                    f'✔ {chosen_label} (자동 선택)</div>',
                    unsafe_allow_html=True
                )
                chosen_idx = 0
            else:
                chosen_label = st.selectbox(
                    f"{tangu_code} 선택",
                    option_labels,
                    index=default_idx,
                    key=f"tangu_{tangu_code}",
                    label_visibility="collapsed"
                )
                chosen_idx = option_labels.index(chosen_label)

            chosen_opt = options[chosen_idx]
            new_tangu_map[tangu_code] = {
                "교사명": chosen_opt["교사명"],
                "교실위치": chosen_opt["교실위치"],
            }

        if not tangu_found_any:
            st.info(f"{preview_class}반에는 탐구 과목 데이터가 없어요.")

        # ── 저장 버튼 ────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 설정 저장", type="primary", key="save_student"):
            saved["my_class"] = sel_class
            saved["tangu_map"] = new_tangu_map
            save_user_settings(email, saved)
            st.session_state["my_class"] = sel_class
            st.session_state["tangu_map"] = new_tangu_map
            st.success(f"✅ {sel_class}반으로 저장됐어요! 탐구 과목 {len(new_tangu_map)}개 설정 완료.")
            st.balloons()

    # ── 교사 설정 ──────────────────────────────────────────────────────────
    if role in ("teacher", "admin"):
        st.markdown("---")
        st.markdown("### 👩‍🏫 담당 과목 · 반 설정")
        st.markdown(
            '<div style="color:#9E9070;font-size:0.85rem;margin-bottom:12px;">'
            '담당 과목과 반을 설정하면 관리자 페이지에서 빠르게 접근할 수 있어요.</div>',
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

    # ── 설정 초기화 ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚠️ 설정 초기화"):
        st.warning("저장된 모든 개인 설정이 삭제돼요.")
        if st.button("초기화", key="reset_settings"):
            save_user_settings(email, {})
            for key in ["my_class", "my_subjects", "my_classes", "tangu_map"]:
                st.session_state.pop(key, None)
            st.success("✅ 설정이 초기화됐어요.")
            st.rerun()
