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

## 🗄️ 3. 데이터베이스 초기화 및 데이터 수집 (Backfill)

Git 저장소에는 대용량 데이터베이스 파일(`stock_data.db`)이 제외되어 있으므로, 처음 셋업 시 로컬 데이터베이스를 생성하고 과거 6년 치 주가 및 시그널 통계를 채워 넣어야 합니다.

### 단계 1: 상장 종목 목록 및 지수 매핑 데이터 초기화
먼저, `initialize_db.py`를 실행하여 한국 및 미국 상장 종목 리스트를 가져오고, 지수 구성 정보(`index_constituents.json`)를 바탕으로 KOSPI 200, KOSDAQ 150 매핑 플래그를 세팅합니다.
```bash
# uv 사용 시
uv run python initialize_db.py

# 일반 python 실행 시
python initialize_db.py
```
*(성공적으로 실행되면 `stock_data.db` 파일이 생성되고 `tickers` 및 `us_tickers` 테이블이 채워집니다.)*

### 단계 2: 과거 6개년 주가 및 Stage 시그널 자동 수집
`incremental_update.py`를 실행하면 데이터베이스에 있는 모든 종목에 대해 FinanceDataReader로부터 과거 주가 데이터(2000년 혹은 2020년 이후 전체 기간)를 병렬 다운로드합니다. 
주가 수집이 완료되면 내부적으로 `scanner.py`가 자동으로 호출되어 순환 주기 Stage 계산 및 실시간 신호 캐싱, 과거 추세 통계 백필링까지 완벽히 마무리합니다.
```bash
# uv 사용 시
uv run python incremental_update.py

# 일반 python 실행 시
python incremental_update.py
```
*(참고: 6개년 1,500영업일 이상의 전체 시계열 Stage 정보를 계산하고 적재하는 작업이므로 최초 실행 시 인터넷 속도 및 CPU 사양에 따라 수십 분 이상의 시간이 소요될 수 있습니다.)*

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

---

## 📊 5. 명령행(CLI) 시장 신호 보고서 실행

대시보드 웹 브라우저를 열지 않고도, 당일 혹은 특정 과거 일자 기준의 지수별 세부 지표 현황과 전략 포지션 상태(최근 매매 신호 일자 및 가격 정보)를 콘솔창에 즉시 리포트로 출력할 수 있습니다.

```bash
# uv 사용 시 최신 영업일 기준 현황 보고
uv run python signal_status.py

# 특정 날짜 기준 현황 및 전일/5일평균 대비 증감 보고
uv run python signal_status.py 2026-06-18
```
*(참고: 조회하고자 하는 입력 날짜가 휴일이나 주말일 경우, 자동으로 데이터베이스에 적재된 직전 가장 최근 영업일을 역산해 찾아 안전하게 현황을 표출해 줍니다.)*
