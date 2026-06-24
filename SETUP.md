# Kojiro Moving Average Grand Cycle Analyzer - Setup Guide

본 프로젝트는 주식 종목들의 이동평균선 대순환 상태(Kojiro Stage)를 분석하고, 실시간 투자 신호 현황판을 제공하는 웹 애플리케이션입니다.
이 가이드는 다른 컴퓨터에서 프로젝트를 클론받은 뒤 로컬 환경에서 구동하는 전체 셋업 절차를 다룹니다.

---

## 🛠️ 1. 사전 요구사항

프로젝트를 실행하려면 다음 소프트웨어가 설치되어 있어야 합니다:
- **Python**: 3.10 이상 권장
- **uv** (권장): 고속 Python 패키지 인스톨러 및 환경 관리 도구
- 또는 **pip & venv**: 표준 파이썬 가상환경 도구

---

## 🚀 2. 개발 환경 구축 및 의존성 설치

### 방법 A: `uv` 패키지 매니저 사용 (권장)
`uv`가 설치되어 있다면 즉시 환경 구축 및 패키지 실행이 가능합니다.

1. **가상환경 생성 및 의존성 설치**:
   ```bash
   uv venv
   source .venv/bin/activate  # macOS / Linux
   # .venv\Scripts\activate  # Windows
   
   uv sync
   ```

### 방법 B: 표준 `pip` 및 가상환경 사용
1. **가상환경 생성 및 활성화**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   # .venv\Scripts\activate  # Windows
   ```
2. **필요 패키지 설치**:
   - `pyproject.toml`에 명시된 필수 패키지 목록을 참고하여 설치합니다.
   ```bash
   pip install --upgrade pip
   pip install fastapi uvicorn pandas numpy sqlite3 html5lib requests bs4  # 주요 의존성
   ```

---

## 🗄️ 3. 데이터베이스 초기화 및 데이터 백필링

Git 저장소에는 대용량 데이터베이스 파일(`stock_data.db`)이 제외되어 있으므로, 처음 셋업 시 로컬 데이터베이스를 생성하고 과거 6년 치 주가 및 시그널 통계를 채워 넣어야 합니다.

1. **마켓 데이터 수집 및 과거 신호 백필(Backfill) 실행**:
   `scanner.py` 스크립트를 실행하면 `stock_data.db` 파일을 자동으로 초기화하고, 필요한 주가 수집 및 6개년 시각화용 Stage 통계 계산을 일괄 진행합니다.
   ```bash
   # uv 사용 시
   uv run python scanner.py
   
   # pip 가상환경 활성화 상태 시
   python scanner.py
   ```
   *(참고: 6개년 1,500영업일 이상의 전체 시계열 Stage 정보를 계산하고 적재하는 작업이므로 최초 실행 시 수 분에서 수십 분의 시간이 소요될 수 있습니다.)*

---

## 💻 4. 웹 어플리케이션 실행

데이터 수집 및 적재가 완료되었다면 FastAPI 웹 서버를 구동합니다.

1. **개발 서버 구동**:
   ```bash
   # uv 사용 시
   uv run python -m uvicorn main:app --host 0.0.0.0 --port 8081 --reload
   
   # 또는 uvicorn 직접 구동
   uvicorn main:app --host 0.0.0.0 --port 8081 --reload
   ```
2. **웹 브라우저 접속**:
   - 주소창에 `http://localhost:8081`을 입력하고 이동합니다.
   - 상단 메뉴의 **Signals** 탭을 통해 실시간 투자 지표 현황판(코스피 200 동일가중, 코스닥 150)을 확인할 수 있습니다.
