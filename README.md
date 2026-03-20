# 🗺️ 길잡이 GIL-ZABI

> **시간표를 지도 위에 펼치다, 내 수업의 위치를 한눈에**

개인별 맞춤 시간표 + 실시간 교실 위치 + 선생님 찾기를 하나로 묶은 학교 스마트 안내 시스템

---

## 📁 프로젝트 구조

```
gilzabi/
├── app.py                  # 메인 진입점 (사이드바 라우팅)
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── config.toml         # 다크 테마 설정
│
├── pages/
│   ├── home.py             # 홈 (실시간 현황 + 빠른 시간표 조회)
│   ├── timetable.py        # 시간표 상세 조회
│   ├── map_view.py         # 1~5층 SVG 인터랙티브 지도
│   └── teacher_search.py   # 선생님 찾기 검색
│
├── utils/
│   └── helpers.py          # 교시 시간, 데이터 로드, 위치 계산 공통 함수
│
└── data/
    ├── timetable.csv       # 시간표 DB (요일/교시/반/과목/교사/교실)
    ├── teachers.csv        # 선생님 DB (교사명/담당과목/교무실)
    └── rooms.csv           # 교실 정보 DB
```

---

## 🚀 실행 방법

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. 앱 실행
```bash
streamlit run app.py
```

---

## 📊 데이터 구조

### timetable.csv
| 컬럼 | 설명 | 예시 |
|------|------|------|
| 요일 | 한글 요일 | 월, 화, 수, 목, 금 |
| 교시 | 교시 번호 | 1~7 |
| 반 | 학년-반 | 1-1, 2-3 |
| 과목 | 과목명 | 국어, 수학 |
| 교사명 | 담당 선생님 | 김영희 |
| 교실위치 | 교실 코드 | 1-101, 과학실A |
| 층 | 층 번호 | 1~5 |

### teachers.csv
| 컬럼 | 설명 |
|------|------|
| 교사명 | 선생님 성함 |
| 담당과목 | 담당 과목 |
| 교무실 | 교무실 이름 |
| 교무실위치 | 교무실 코드 |
| 층 | 교무실 층 |

---

## 🔗 Google Sheets 연동 (선택)

`utils/helpers.py`에서 `load_timetable()` 함수를 수정하면 CSV 대신 Google Sheets에서 실시간 데이터를 가져올 수 있습니다.

```python
# .streamlit/secrets.toml 에 추가 (git에 올리지 마세요!)
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key = "..."
# ... 나머지 서비스 계정 정보

[sheets]
timetable_id = "스프레드시트_ID"
```

```python
# helpers.py - Google Sheets 연동 예시
import gspread
from google.oauth2.service_account import Credentials

def load_timetable_from_sheets():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(st.secrets["sheets"]["timetable_id"])
    ws = sh.worksheet("시간표")
    return pd.DataFrame(ws.get_all_records())
```

---

## 🌐 Streamlit Cloud 배포

1. GitHub에 이 저장소를 push
2. [share.streamlit.io](https://share.streamlit.io) 접속
3. GitHub 연결 → 저장소 선택 → `app.py` 지정
4. Deploy!

**⚠️ 주의:** `.streamlit/secrets.toml`은 절대 GitHub에 올리지 말고,
Streamlit Cloud의 **Secrets 설정**에 직접 입력하세요.

---

## 📅 로드맵

- [x] 시간표 조회 (현재/다음 교시 강조)
- [x] 1~5층 SVG 인터랙티브 지도
- [x] 선생님 찾기 검색
- [ ] Google Sheets 실시간 연동
- [ ] 관리자 페이지 (시간표 수정)
- [ ] QR 코드 생성 (빠른 접속)
- [ ] 푸시 알림 (다음 교시 알림)

---

## 👥 팀 GIL-ZABI

| 이름 | 역할 |
|------|------|
| 장주형 | 시스템 구현 및 기술 지원 |
| 김주원 | UI/UX 및 인터랙티브 디자인 |
| 전화용 | 데이터 아키텍트 및 콘텐츠 구축 |
