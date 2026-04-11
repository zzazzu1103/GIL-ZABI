"""
pages/my_settings.py
─────────────────────
로그인한 사용자의 개인 설정 페이지
- 학생: 학년 버튼 → 반 버튼 분리 선택 + 탐구 과목 개인화
- 교사: 담당 과목/반 선택
"""

import streamlit as st
from utils.helpers import load_timetable, load_teachers, sort_classes
from utils.auth import get_current_user, get_role
from utils.user_settings import load_user_settings, save_user_settings


def _get_tangu_options(timetable_df, my_class, tangu_code):
    if not my_class:
        return []
    rows = timetable_df[
        (timetable_df["반"] == my_class) &
        (timetable_df["과목"] == tangu_code)
    ][["교사명", "교실위치"]].drop_duplicates()
    return [
        {
            "교사명": r["교사명"],
            "교실위치": str(r["교실위치"]),
            "label": f"{r['교사명']} 선생님 · {r['교실위치']}호",
        }
        for _, r in rows.iterrows()
    ]


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
    <div class="card" style="display:flex;align-items:center;gap:14px;padding:16px 20px;margin-bottom:8px;">
        <div style="font-size:2rem;">{role_icon}</div>
        <div>
            <div style="font-weight:700;font-size:1rem;color:#3D3929;">{user['name']}</div>
            <div style="color:#9E9070;font-size:0.82rem;">{email}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    df = load_timetable()
    teachers_df = load_teachers()

    # ── 학생 설정 ──────────────────────────────────────────────────────────
    if role in ("student", "admin"):

        st.markdown("### 🏫 내 학년 · 반 설정")
        st.caption("학년과 반을 선택한 뒤 저장 버튼을 눌러주세요.")

        current_class = saved.get("my_class", "")

        # 전체 반을 숫자 정렬 후 학년별 그룹화
        all_classes = sort_classes(df["반"].unique().tolist())
        grades: dict[int, list[str]] = {}
        for c in all_classes:
            try:
                g = int(c.split("-")[0])
            except Exception:
                g = 0
            grades.setdefault(g, []).append(c)
        grade_list = sorted(grades.keys())

        # 현재 저장된 반에서 학년 추출 (초기값)
        if current_class and "-" in current_class:
            try:
                default_grade = int(current_class.split("-")[0])
            except Exception:
                default_grade = grade_list[0]
        else:
            default_grade = grade_list[0]

        # 세션에서 선택 중인 학년/반 읽기
        if "_set_grade" not in st.session_state:
            st.session_state["_set_grade"] = default_grade
        if "_set_class" not in st.session_state:
            st.session_state["_set_class"] = current_class

        sel_grade = st.session_state["_set_grade"]
        sel_class = st.session_state["_set_class"]

        # ── 학년 버튼 ────────────────────────────────────────────────────
        st.markdown("**학년**")
        grade_cols = st.columns(len(grade_list))
        for i, g in enumerate(grade_list):
            with grade_cols[i]:
                label = f"{g}학년"
                is_sel = (sel_grade == g)
                # 선택된 학년은 채워진 버튼처럼 보이게 마크다운 오버레이
                if is_sel:
                    st.markdown(
                        f'<div style="text-align:center;padding:6px 0;'
                        f'background:#7D6B2E;color:#FAF7F2;border-radius:8px;'
                        f'font-weight:700;font-size:0.9rem;cursor:default;">{label}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    if st.button(label, key=f"gbtn_{g}", use_container_width=True):
                        st.session_state["_set_grade"] = g
                        # 학년이 바뀌면 반도 해당 학년 첫 번째 반으로 초기화
                        st.session_state["_set_class"] = grades[g][0]
                        st.rerun()

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        # ── 반 버튼 ──────────────────────────────────────────────────────
        class_list = grades.get(sel_grade, [])

        # sel_class가 현재 학년에 없으면 첫 번째로 교정
        if sel_class not in class_list and class_list:
            sel_class = class_list[0]
            st.session_state["_set_class"] = sel_class

        st.markdown("**반**")
        COLS = 6
        for row_i in range((len(class_list) + COLS - 1) // COLS):
            chunk = class_list[row_i * COLS : (row_i + 1) * COLS]
            cols = st.columns(COLS)
            for ci, cls in enumerate(chunk):
                with cols[ci]:
                    short = cls.split("-")[1] if "-" in cls else cls
                    label = f"{short}반"
                    is_sel = (sel_class == cls)
                    if is_sel:
                        st.markdown(
                            f'<div style="text-align:center;padding:6px 0;'
                            f'background:#7D6B2E;color:#FAF7F2;border-radius:8px;'
                            f'font-weight:700;font-size:0.9rem;cursor:default;">{label}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        if st.button(label, key=f"cbtn_{cls}", use_container_width=True):
                            st.session_state["_set_class"] = cls
                            st.rerun()

        # 선택 결과 표시
        sel_class = st.session_state.get("_set_class", "")
        st.markdown(
            f'<div style="margin:14px 0 4px;padding:10px 16px;background:#F5F0E8;'
            f'border-radius:8px;border-left:3px solid #7D6B2E;font-size:0.9rem;">'
            f'<span style="color:#9E9070;">선택된 반</span> &nbsp;'
            f'<b style="color:#3D3929;">{sel_class}</b>'
            + (f'&nbsp;<span style="color:#9E9070;font-size:0.78rem;">'
               f'(현재 저장: {current_class})</span>' if current_class and current_class != sel_class else "")
            + f'</div>',
            unsafe_allow_html=True
        )

        # ── 탐구 과목 개인화 ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🔬 탐구 과목 설정")
        st.caption("탐구 A~E 과목은 학생마다 담당 선생님과 교실이 달라요. 내 수업에 맞게 선택해 주세요.")

        saved_tangu = saved.get("tangu_map", {})
        new_tangu_map = {}
        tangu_found_any = False

        for tangu_code in ["탐구A", "탐구B", "탐구C", "탐구D", "탐구E1", "탐구E2"]:
            options = _get_tangu_options(df, sel_class, tangu_code)
            if not options:
                continue
            tangu_found_any = True
            option_labels = [o["label"] for o in options]

            prev = saved_tangu.get(tangu_code, {})
            prev_label = (
                f"{prev.get('교사명','')} 선생님 · {prev.get('교실위치','')}호"
                if prev else None
            )
            default_idx = option_labels.index(prev_label) if prev_label in option_labels else 0

            col_l, col_r = st.columns([1, 3])
            with col_l:
                st.markdown(
                    f'<div style="padding:8px 0;font-weight:700;color:#3D3929;">{tangu_code}</div>',
                    unsafe_allow_html=True
                )
            with col_r:
                if len(options) == 1:
                    st.markdown(
                        f'<div style="padding:8px 12px;background:#F5F0E8;border-radius:8px;'
                        f'font-size:0.88rem;color:#7D6B2E;">'
                        f'✔ {option_labels[0]} <span style="color:#D4C9A8;">(자동)</span></div>',
                        unsafe_allow_html=True
                    )
                    chosen_idx = 0
                else:
                    chosen_label = st.selectbox(
                        tangu_code,
                        option_labels,
                        index=default_idx,
                        key=f"tangu_{tangu_code}",
                        label_visibility="collapsed"
                    )
                    chosen_idx = option_labels.index(chosen_label)

            chosen = options[chosen_idx]
            new_tangu_map[tangu_code] = {
                "교사명":   chosen["교사명"],
                "교실위치": chosen["교실위치"],
            }

        if not tangu_found_any:
            st.info(f"{sel_class}반에는 탐구 과목이 없어요.")

        # ── 저장 ────────────────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 설정 저장", type="primary", key="save_student", use_container_width=True):
            saved["my_class"]  = sel_class
            saved["tangu_map"] = new_tangu_map
            save_user_settings(email, saved)
            st.session_state["my_class"]  = sel_class
            st.session_state["tangu_map"] = new_tangu_map
            st.success(f"✅ {sel_class}반으로 저장됐어요! 탐구 과목 {len(new_tangu_map)}개 설정 완료.")
            st.balloons()

    # ── 교사 설정 ──────────────────────────────────────────────────────────
    if role in ("teacher", "admin"):
        st.markdown("---")
        st.markdown("### 👩‍🏫 담당 과목 · 반 설정")

        all_subjects = sorted(df["과목"].unique().tolist())
        all_classes  = sort_classes(df["반"].unique().tolist())

        saved_subjects = saved.get("my_subjects", [])
        saved_classes  = saved.get("my_classes",  [])

        sel_subjects = st.multiselect(
            "담당 과목 선택", all_subjects,
            default=[s for s in saved_subjects if s in all_subjects],
            key="set_subjects"
        )
        sel_classes_t = st.multiselect(
            "담당 반 선택", all_classes,
            default=[c for c in saved_classes if c in all_classes],
            key="set_classes"
        )

        if st.button("💾 담당 설정 저장", type="primary", key="save_teacher"):
            saved["my_subjects"] = sel_subjects
            saved["my_classes"]  = sel_classes_t
            save_user_settings(email, saved)
            st.session_state["my_subjects"] = sel_subjects
            st.session_state["my_classes"]  = sel_classes_t
            st.success(f"✅ 담당 과목 {len(sel_subjects)}개, 반 {len(sel_classes_t)}개 저장됐어요!")

    # ── 설정 초기화 ────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("⚠️ 설정 초기화"):
        st.warning("저장된 모든 개인 설정이 삭제돼요.")
        if st.button("초기화", key="reset_settings"):
            save_user_settings(email, {})
            for key in ["my_class", "my_subjects", "my_classes", "tangu_map",
                        "_set_grade", "_set_class"]:
                st.session_state.pop(key, None)
            st.success("✅ 설정이 초기화됐어요.")
            st.rerun()
