"""
관리자 페이지 — 교사·학급 임원용 시간표 수정
────────────────────────────────────────────
비밀번호로 접근을 제한합니다.
secrets.toml 에 아래 항목을 추가하세요:

[admin]
password = "your_secure_password"
"""

import os
import streamlit as st
import pandas as pd
from utils.helpers import load_timetable, load_teachers, DATA_DIR
from utils.auth import get_role, has_permission

# Google Sheets 연동 여부 확인
USE_SHEETS = False
try:
    if "gcp_service_account" in st.secrets and "sheets" in st.secrets:
        from utils.sheets_sync import (
            load_timetable_sheets, update_timetable_cell, append_timetable_row
        )
        USE_SHEETS = True
except Exception:
    pass


def _render_df_html(df: pd.DataFrame, max_height: int = 420):
    """읽기 전용 표를 HTML로 렌더링.

    st.dataframe 의 네이티브(pyarrow) 직렬화가 배포 서버(py3.14)에서
    프로세스를 죽이는 문제가 있어 pyarrow 를 타지 않는 경로를 사용한다.
    """
    th = ("padding:8px 10px; background:#F5F0E8; color:#7D6B2E; font-weight:700;"
          "border:1px solid #E0D8CC; position:sticky; top:0;")
    td = "padding:7px 10px; border:1px solid #E0D8CC; font-size:0.85rem; color:#3D3929;"
    head = "".join(f'<th style="{th}">{c}</th>' for c in df.columns)
    body = "".join(
        "<tr>" + "".join(f'<td style="{td}">{v}</td>' for v in row) + "</tr>"
        for row in df.astype(str).itertuples(index=False)
    )
    st.markdown(
        f'<div style="overflow:auto; max-height:{max_height}px; border:1px solid #E0D8CC; border-radius:8px;">'
        f'<table style="width:100%; border-collapse:collapse; background:#fff;">'
        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def _check_password() -> bool:
    """비밀번호 확인. secrets.toml 없으면 개발 모드로 통과."""
    try:
        correct = st.secrets["admin"]["password"]
    except Exception:
        st.warning("⚠️ secrets.toml에 admin.password가 설정되지 않아 개발 모드로 접근합니다.")
        return True

    if "admin_authenticated" in st.session_state and st.session_state["admin_authenticated"]:
        return True

    pwd = st.text_input("🔒 관리자 비밀번호", type="password", key="admin_pwd_input")
    if st.button("확인", key="admin_login_btn"):
        if pwd == correct:
            st.session_state["admin_authenticated"] = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False


def show():
    st.markdown("""
    <div class="main-header">
        <h1>⚙️ 관리자</h1>
        <p>시간표 변동 및 특별실 사용 현황을 실시간으로 수정할 수 있습니다</p>
    </div>
    """, unsafe_allow_html=True)

    if not _check_password():
        return

    st.success("✅ 관리자 로그인 성공")

    if USE_SHEETS:
        st.info("📡 Google Sheets 실시간 연동 모드")
        try:
            df = load_timetable_sheets()
        except Exception as e:
            from utils.sheets_sync import SheetColumnsMissing
            if isinstance(e, SheetColumnsMissing):
                st.error(
                    f"❌ 시간표 시트('{e.sheet_name}')에 필요한 컬럼이 없어요: "
                    f"**{', '.join(e.missing)}**\n\n"
                    f"시트의 실제 컬럼: {', '.join(e.actual) if e.actual else '(비어 있음)'}\n\n"
                    f"헤더 이름이 `요일 / 교시 / 반 / 과목 / 교사명 / 교실위치 / 층` 과 "
                    f"정확히 같은지(띄어쓰기·오타 포함) 확인해주세요."
                )
            else:
                st.error(f"❌ Google Sheets에서 시간표를 읽는 중 오류가 났어요: {e}")
            st.info("대신 로컬 CSV 데이터로 관리자 페이지를 보여드릴게요.")
            df = load_timetable()
    else:
        st.warning("📁 로컬 CSV 모드 (Google Sheets 미연동 — 변경 사항은 재시작 시 초기화됩니다)")
        df = load_timetable()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 시간표 조회/수정", "➕ 행 추가", "📤 CSV 내보내기", "🔄 컴시간 동기화"])

    # ── 탭1: 조회 및 수정 ──────────────────────────────────────────────────
    with tab1:
        st.markdown("#### 필터")
        col1, col2, col3 = st.columns(3)
        with col1:
            f_day = st.selectbox("요일", ["전체","월","화","수","목","금"])
        with col2:
            classes = ["전체"] + sorted(df["반"].unique().tolist())
            f_class = st.selectbox("반", classes)
        with col3:
            f_period = st.selectbox("교시", ["전체"] + list(range(1, 8)))

        view = df.copy()
        if f_day    != "전체": view = view[view["요일"] == f_day]
        if f_class  != "전체": view = view[view["반"]   == f_class]
        if f_period != "전체": view = view[view["교시"] == int(f_period)]

        st.markdown(f"#### 결과 ({len(view)}행)")

        if USE_SHEETS:
            st.markdown("셀을 직접 클릭해 수정 후 **저장** 버튼을 누르세요.")
            edited = st.data_editor(
                view.reset_index(drop=True),
                use_container_width=True,
                num_rows="fixed",
                key="admin_editor",
            )
            if st.button("💾 Google Sheets에 저장", type="primary"):
                # 변경된 행 감지 후 업데이트
                original = view.reset_index(drop=True)
                changes = 0
                for idx in range(len(edited)):
                    for col in ["과목","교사명","교실위치","층"]:
                        if str(edited.at[idx, col]) != str(original.at[idx, col]):
                            # 원본 df에서 실제 row 번호 찾기
                            mask = (
                                (df["요일"]  == original.at[idx,"요일"])  &
                                (df["교시"]  == original.at[idx,"교시"])  &
                                (df["반"]    == original.at[idx,"반"])
                            )
                            real_idx = df[mask].index
                            if len(real_idx):
                                update_timetable_cell(
                                    int(real_idx[0]) + 1, col,
                                    str(edited.at[idx, col])
                                )
                                changes += 1
                if changes:
                    st.success(f"✅ {changes}개 셀 업데이트 완료!")
                    st.cache_data.clear()
                else:
                    st.info("변경 사항이 없습니다.")
        else:
            # 로컬 모드: 읽기 전용 표시 + CSV 직접 수정 안내
            _render_df_html(view.reset_index(drop=True))
            st.info(
                "로컬 CSV 수정은 `data/timetable.csv` 파일을 직접 편집하거나 "
                "아래 '행 추가' 탭을 이용하세요."
            )

    # ── 탭2: 행 추가 ──────────────────────────────────────────────────────
    with tab2:
        st.markdown("#### 새 수업 추가")
        teachers_df = load_teachers()
        teacher_list = teachers_df["교사명"].tolist()

        c1, c2 = st.columns(2)
        with c1:
            new_day     = st.selectbox("요일",  ["월","화","수","목","금"], key="add_day")
            new_period  = st.number_input("교시", 1, 7, 1, key="add_period")
            new_class   = st.text_input("반 (예: 1-1)", key="add_class")
        with c2:
            new_subject = st.text_input("과목", key="add_subject")
            new_teacher = st.selectbox("교사명", teacher_list, key="add_teacher")
            new_room    = st.text_input("교실위치 (예: 1-101)", key="add_room")
            new_floor   = st.number_input("층", 1, 5, 1, key="add_floor")

        if st.button("➕ 추가", type="primary", key="add_btn"):
            if not all([new_class, new_subject, new_room]):
                st.warning("반, 과목, 교실위치를 모두 입력하세요.")
            else:
                new_row = {
                    "요일": new_day, "교시": int(new_period), "반": new_class,
                    "과목": new_subject, "교사명": new_teacher,
                    "교실위치": new_room, "층": int(new_floor),
                }
                if USE_SHEETS:
                    if append_timetable_row(new_row):
                        st.success("✅ Google Sheets에 추가 완료!")
                        st.cache_data.clear()
                else:
                    # 로컬 CSV에 추가
                    csv_path = os.path.join(DATA_DIR, "timetable.csv")
                    new_df = pd.DataFrame([new_row])
                    new_df.to_csv(csv_path, mode="a", header=False, index=False,
                                  encoding="utf-8-sig")
                    st.success("✅ CSV 파일에 추가했습니다. 앱을 새로고침하세요.")
                    st.cache_data.clear()

    # ── 탭3: CSV 내보내기 ──────────────────────────────────────────────────
    with tab3:
        st.markdown("#### 현재 데이터 CSV 다운로드")
        csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="📥 timetable.csv 다운로드",
            data=csv_bytes,
            file_name="timetable.csv",
            mime="text/csv",
        )
        st.markdown(f"총 **{len(df)}행** 데이터 (아래는 처음 20행)")
        _render_df_html(df.head(20))

    # ── 탭4: 컴시간알리미 동기화 ──────────────────────────────────────────
    with tab4:
        st.markdown("#### 컴시간알리미에서 최신 시간표 가져오기")
        st.caption(
            "컴시간(비공식 API)에서 학급별 시간표를 받아옵니다. "
            "교실 위치는 교사 시간표와 홈룸 규칙으로 자동 결합돼요. "
            "가져온 뒤 내용을 확인하고 적용하세요."
        )
        school_name = st.text_input("학교명", value="저현고등학교", key="comci_school")

        if st.button("📡 컴시간에서 가져오기", key="comci_fetch"):
            try:
                from utils.comcigan_sync import fetch_comcigan_timetable
                with st.spinner("컴시간 서버에서 시간표를 받아오는 중..."):
                    fetched = fetch_comcigan_timetable(school_name)
                st.session_state["comci_preview"] = fetched
                st.success(f"✅ {len(fetched)}행을 받아왔어요.")
            except ImportError:
                st.error("`comcigan` 패키지가 설치되어 있지 않아요. requirements.txt 반영 후 재배포하세요.")
            except Exception as e:
                st.error(f"가져오기 실패: {type(e).__name__} — {e}")
                st.info("컴시간은 비공식 서비스라 접속이 막히거나 구조가 바뀌면 실패할 수 있어요. 기존 시간표는 그대로 유지됩니다.")

        preview = st.session_state.get("comci_preview")
        if preview is not None:
            no_room = int((preview["교실위치"] == "").sum())
            unknown_teacher = int((~preview["교사명"].isin(load_teachers()["교사명"])).sum())
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("받아온 행", f"{len(preview)}행")
            with c2: st.metric("교실 미확정", f"{no_room}행")
            with c3: st.metric("교사명 미매칭", f"{unknown_teacher}행")
            _render_df_html(preview.head(30))

            st.download_button(
                "📥 받아온 시간표 CSV 다운로드 (저장소 반영용)",
                data=preview.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
                file_name="timetable.csv",
                mime="text/csv",
            )
            st.warning(
                "⚠️ 아래 '적용'은 서버의 timetable.csv 를 덮어쓰지만, "
                "Streamlit Cloud 는 재배포 시 파일이 초기화돼요. "
                "영구 반영하려면 위 CSV를 내려받아 GitHub 의 data/timetable.csv 에 커밋하세요."
            )
            if st.button("✅ 이 시간표를 지금 서버에 적용", key="comci_apply", type="primary"):
                csv_path = os.path.join(DATA_DIR, "timetable.csv")
                preview.to_csv(csv_path, index=False, encoding="utf-8-sig")
                st.cache_data.clear()
                st.success("✅ 적용 완료! 시간표·지도에 바로 반영됩니다.")
