---
title: 길잡이 GIL-ZABI
emoji: 🗺️
colorFrom: yellow
colorTo: green
sdk: streamlit
sdk_version: "1.49.1"
app_file: app.py
pinned: false
---

# 🗺️ 길잡이 GIL-ZABI

시간표를 지도 위에 펼치다 — 내 수업의 위치를 한눈에.

저현고등학교 학생·선생님을 위한 교내 길찾기 서비스입니다.

- 🏠 **홈**: 오늘 날짜·교시 기준 실시간 시간표
- 🗺️ **학교 지도**: 1~5층 평면도에서 교실 위치 확인
- 🔍 **선생님 찾기**: 이름/과목으로 검색해 현재 위치 확인
- 👤 **개인 설정**: 내 반·탐구 과목 기반 맞춤 시간표
- ⚙️ **관리자**: 시간표 실시간 수정 (Google Sheets 연동)

## 배포 (Hugging Face Spaces)

이 저장소는 GitHub `main` 브랜치에 푸시하면 GitHub Actions가
Hugging Face Space로 자동 배포합니다
(`.github/workflows/deploy-to-hf.yml` 참고).

시크릿은 Space **Settings → Variables and secrets**에
`SECRETS_TOML`이라는 이름으로 `.streamlit/secrets.toml` 전체 내용을
넣으면 앱 시작 시 자동으로 파일로 만들어집니다.
