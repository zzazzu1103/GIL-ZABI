"""
utils/user_settings.py
──────────────────────
이메일 기반 사용자 설정 저장/불러오기
저장 위치: data/user_settings.json
"""

import json
import os
import streamlit as st

SETTINGS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "user_settings.json"
)

# 탐구 과목 코드 → 표시명
TANGU_SUBJECTS = {
    "탐구A": "탐구A",
    "탐구B": "탐구B",
    "탐구C": "탐구C",
    "탐구D": "탐구D",
    "탐구E1": "탐구E1",
    "탐구E2": "탐구E2",
}

DEFAULT_SETTINGS = {
    "my_class":    "",   # 학생: 내 반 (예: "1-1")
    "my_subjects": [],   # 교사: 담당 과목 목록
    "my_classes":  [],   # 교사: 담당 반 목록
    "tangu_map":   {},   # 학생: 탐구 과목 매핑 {"탐구A": {"교사명": "박지인", "교실위치": "211"}}
}


def _load_all() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        return {}
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_user_settings(email: str) -> dict:
    all_data = _load_all()
    settings = all_data.get(email, {})
    return {**DEFAULT_SETTINGS, **settings}


def save_user_settings(email: str, settings: dict):
    all_data = _load_all()
    all_data[email] = settings
    _save_all(all_data)


def apply_user_settings_to_session(email: str):
    """로그인 시 저장된 설정을 세션에 자동 적용"""
    settings = load_user_settings(email)
    if settings.get("my_class"):
        st.session_state["my_class"] = settings["my_class"]
    if settings.get("my_subjects"):
        st.session_state["my_subjects"] = settings["my_subjects"]
    if settings.get("my_classes"):
        st.session_state["my_classes"] = settings["my_classes"]
    if settings.get("tangu_map"):
        st.session_state["tangu_map"] = settings["tangu_map"]
