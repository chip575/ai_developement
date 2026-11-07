# 캠퍼스톡 — 부산대학교 경영학과 학사 챗봇 MVP

부산대학교 경영학과 학부 단일전공을 가정한 로컬 데모입니다. 공개 학사 안내는 누구나 이용하고, 로그인한 가상 학생은 본인 이수기록과 총 학점·전공기초·전공필수 비교를 확인할 수 있습니다. **실제 학교 계정·학사 시스템과 연결되어 있지 않습니다.**

## 실행

### 이메일 전달용 ZIP

상위 폴더의 `PNU_Assistant_Windows.zip`은 Gmail이 차단하는 `.cmd`, `.ps1`, `.js` 확장자를 제외한 전송용 소스 패키지입니다. ZIP의 `.env`에는 실제 API 키가 없고 주석과 예시 값만 있으므로, 받는 사람이 본인의 키를 직접 입력해야 합니다. 전송본의 실행·설정 방법은 [전송용 README](README_EMAIL.md)를 확인하세요. 전송 성공 여부는 Gmail의 추가 콘텐츠 검사에 따라 달라질 수 있습니다. ZIP은 Git에 올리지 않으며, 직접 만들려면 원본 폴더에서 `uv run python -m scripts.package_demo`를 실행합니다.

### 이 원본 폴더에서 Windows로 실행

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/)을 설치하고 실행합니다. 설치 후 재시작이나 WSL 설정이 필요하면 Docker Desktop의 안내를 따릅니다.
2. 원본 `academic_chat` 폴더를 엽니다. 이메일 전달용 ZIP은 위의 별도 안내를 사용합니다.
3. 처음 내려받았다면 이 폴더에서 PowerShell을 열고 `Copy-Item .env.example .env`를 실행한 다음 `notepad .env`에서 `PICKLE_API_KEY=` 뒤에 본인 키를 입력하고 저장합니다. `.env`는 Git에 올리지 마세요.
4. **START_PNU.cmd**를 더블클릭합니다. 첫 실행에는 인터넷이 필요하며 이미지, 패키지, 임베딩 모델을 다운로드하므로 몇 분 이상 걸릴 수 있습니다.
5. 준비가 완료되면 브라우저가 자동으로 열립니다. 기본 주소는 http://127.0.0.1:8771 입니다.
6. 종료하려면 **STOP_PNU.cmd**를 더블클릭합니다. 이후 다시 시작하려면 START_PNU.cmd를 실행합니다. DB와 검색 인덱스는 보존됩니다.

Vue 화면, 서버, 데이터와 문서는 이 폴더에 포함되어 있습니다. 다른 프로젝트나 별도의 Python, Node.js, uv 설치는 필요하지 않습니다. 앱은 실행한 PC의 localhost에만 열립니다. 이메일 수신자는 각자 Docker Desktop을 설치하고 실행해야 합니다.

같은 폴더의 `.env`에 API 키와 설정이 있습니다. 키를 바꾸려면 메모장으로 `PICKLE_API_KEY=` 값을 수정하고 저장한 뒤 앱을 중지하고 다시 실행하세요. `.env`가 없으면 `.env.example`을 `.env`로 복사해 작성하세요. 전송용 ZIP에는 예시 키만 포함됩니다. 키의 유효성·모델 접근 권한이 필요하며 AI 호출 비용이 발생할 수 있습니다.

포트 충돌 시 `.env`의 `APP_PORT` 또는 `POSTGRES_PORT`를 사용하지 않는 번호로 바꾸고 재실행하세요. 앱이 시작되지 않으면 Docker Desktop, 인터넷과 포트를 확인하세요. 상세 오류는 이 폴더에서 `docker compose logs --tail 100 app`으로 확인합니다. 같은 이름의 Windows 프로세스 환경 변수가 있으면 포트 설정이 `.env`보다 우선될 수 있습니다.

### Docker + PostgreSQL

```powershell
# 압축을 푼 academic_chat 폴더에서 실행합니다.
docker compose up --build -d
```

브라우저에서 http://127.0.0.1:8771 을 엽니다. FastAPI와 PostgreSQL이 각각 컨테이너에서 실행됩니다. 처음 실행할 때 비어 있는 DB에는 가상 데이터를, 비어 있는 Chroma에는 문서 인덱스를 생성합니다. API 키가 없으면 개인 조회의 모델 도구 호출과 일반 대화는 사용할 수 없습니다. 모델 캐시는 Docker 볼륨에 보관합니다.

기존 SQLite 데이터를 PostgreSQL로 한 번 복사하려면 **앱을 시작하기 전 비어 있는 PostgreSQL**을 실행하고 아래 명령을 사용합니다. 이미 데이터가 있는 대상은 덮어쓰지 않으며, 로그인 세션은 복사하지 않습니다.

```powershell
docker compose up -d postgres
$env:DATABASE_URL = 'postgresql://academic:academic_demo@127.0.0.1:55432/academic_chat'
uv run python -m app.migrate_sqlite
Remove-Item Env:DATABASE_URL
docker compose up --build -d
```

SQLite와 PostgreSQL은 이후 자동 동기화되지 않습니다. 기존 로컬 8770번 서버는 SQLite, Docker의 8771번 서버는 PostgreSQL을 사용합니다. Docker DB와 Chroma는 명명된 볼륨에 보관하며 `docker compose down`으로 컨테이너를 중지해도 데이터가 남습니다. 로컬 데모용 DB 암호이므로 외부 공개에는 적합하지 않습니다.

### SQLite 로컬 실행

PowerShell에서 이 폴더로 이동합니다.

```powershell
# academic_chat 폴더에서 실행합니다. uv 및 Node.js 별도 설치 필요
uv sync
uv run python -m app.seed
uv run python -m app.index_docs
cd frontend
npm install
npm run build
cd ..
uv run uvicorn app.main:app --host 127.0.0.1 --port 8765
```

브라우저에서 http://127.0.0.1:8765 를 엽니다. `app.seed`는 제공된 전공 과목 파일을 읽어 SQLite에 과목과 가상 계정·이수기록을 준비합니다. `app.index_docs`는 제공된 학사 문서와 학칙 요약을 Chroma에 적재합니다. 최초 실행 시 오픈소스 다국어 임베딩 모델을 내려받으므로 시간이 걸릴 수 있습니다. 수집 문서나 임베딩 설정을 변경한 경우 인덱싱을 다시 실행하세요.

Vue 화면을 빌드하려면 Node.js와 npm이 필요합니다. `frontend/dist`가 있으면 FastAPI가 Vue 화면을 제공하며, 빌드 전에는 기존 정적 화면이 열립니다. 프런트엔드를 수정한 후에는 `npm run build`를 다시 실행하세요.

프런트엔드 개발 중에는 별도 터미널에서 `cd frontend` 후 `npm run dev`를 실행하고 출력된 주소를 엽니다. Vite 개발 서버는 `/api` 요청을 기본적으로 `http://127.0.0.1:8765`로 전달하므로 FastAPI 서버도 실행해야 합니다. 백엔드 주소를 바꾸려면 개발 서버 실행 전에 `VITE_BACKEND_URL`을 설정하세요.

| 계정 | 비밀번호 | 데이터 |
|---|---|---|
| `student` | `demo1234` | 김민준, 취득 99학점, 가상 TOEIC 750점 |
| `student2` | `demo1234` | 이서연, 취득 3학점, 가상 TOEIC 830점 |

졸업요건은 제공된 수강제도 정리의 2021 교육과정 예시를 모든 데모 학생에게 하나의 공통 기준으로 적용합니다. 이는 실제 입학 연도별 규정을 판정한 것이 아니며, 공식 원문과 개별 적용 여부를 별도 확인해야 합니다. 가상 학생의 총 학점은 모두 전공 과목으로 구성한 테스트 데이터입니다.

영어 성적은 제공된 졸업 공지의 2023학년도 신입학 TOEIC 800점 기준을 모든 가상 학생에게 적용합니다. 이는 공통 **데모 기준**이며 실제 기준은 입학·편입 시기, 예외, 제출 승인 및 대체 요건을 확인해야 합니다. 승인되고 유효기간 안에 있는 TOEIC 성적만 비교하며, 없으면 미확인으로 표시합니다. 제공된 문서의 2026년 8월 졸업 공지 기준이므로 실제 현재 적용은 재확인해야 합니다. 다른 시험 환산, 영어강의 및 대체인정은 확인하지 않습니다.

## Pickle API 설정

Docker 실행 시 이 폴더의 `.env`를 컨테이너 환경 변수로 전달합니다. 로컬 Python 직접 실행은 `.env`를 자동으로 불러오지 않으므로 현재 프로세스 또는 Windows 사용자 환경 변수에 설정해야 합니다. `.env`는 Git 추적에서 제외되며 전달용 ZIP에는 예시 값만 들어갑니다.

| 환경 변수 | 기본값 / 의미 |
|---|---|
| `PICKLE_API_KEY` | 사용자의 Pickle API 키. 개인 도구 호출에 필요 |
| `PICKLE_BASE_URL` | `https://llm.pcl.kr/v1` |
| `PICKLE_TOOL_MODEL` | `google/gemini-2.5-flash`. 사용 계정에서 허용한 함수 도구 호출 모델로 변경 가능 |
| `PICKLE_CHAT_MODEL` | `google/gemini-2.5-flash`. 일반 대화 모델로, 사용 계정에 맞게 변경 가능 |
| `VECTOR_SCORE_THRESHOLD` | `0.38`. 다국어 임베딩·짧은 제목 기준 초기 실험값 |
| `CRAWLER_ENABLED` | `1`. `0`이면 대체 크롤링을 중지 |
| `COOKIE_SECURE` | `0`. HTTPS에서만 운영하도록 구성할 때 `1` |

`PICKLE_TOOL_MODEL`의 기본값은 게이트웨이에서 보이는 유료 모델 후보입니다. **실제 허용 여부·비용·도구 호출 성능은 계정마다 다르므로 확인해야 합니다.** 예를 들어 기존 자체 모델로 지정하려면 서버 실행 전에 `$env:PICKLE_TOOL_MODEL = 'pickle-general'`을 설정합니다. 모델을 사용할 수 없으면 개인 조회 요청은 오류를 안내하며 자동으로 다른 유료 모델을 호출하지 않습니다. 공개 학사 답변은 모델이 생성한 요약이 아닌 검증된 문서 발췌와 출처입니다.

일반적인 본인 학사 조회에서는 질문과 허용 테이블의 스키마를 모델에 보내 SQLite SELECT를 생성합니다. 이메일·전화번호·학생 이름 등 일부 식별자는 전송 전 가리지만 모든 민감정보 탐지를 보장하지 않으므로 질문에 개인정보를 입력하지 마세요. DB의 학생 정보나 성적 결과는 모델에 보내지 않습니다. PostgreSQL에서 로그인한 본인의 허용된 기록만 읽어 요청별 메모리 DB에 담고, 허용된 테이블의 단일 SELECT만 읽기 전용으로 실행합니다. 최대 50건을 표시하며 SQL은 답변의 '생성된 SQL 보기'에서 확인합니다. 모델 생성 SQL은 오류나 의도와 다른 결과가 발생할 수 있습니다. 졸업요건 판단은 이 일반 조회와 분리해 기존 결정적 비교 함수를 사용합니다.

인사에는 고정된 응답을 제공하고, 일반 대화는 `PICKLE_CHAT_MODEL`에 전송합니다. 모델이 최신 정보나 출처가 필요하다고 판단하면 무료 오픈소스 DDGS 검색 도구를 사용하며 검색어가 DuckDuckGo에 전달됩니다. 검색 결과의 발췌문과 링크를 기반으로 답변하므로 결과가 최신이거나 질문에 충분하다는 보장은 없습니다. 검색어에 민감한 개인 정보를 넣지 마세요. 일반 대화에서도 모델 사용 비용이 발생할 수 있습니다. 학사 질문은 공개 문서 검색 또는 본인 조회를 우선하며, 명시적으로 최신 정보를 요청하면 웹 검색을 시도합니다. 단순한 규칙 기반 분류이므로 표현에 따라 잘못 분류될 수 있습니다.

## DataGrip에서 DB 확인

1. Docker에서 PostgreSQL을 실행합니다.
2. DataGrip에서 **New → Data Source → PostgreSQL**을 선택합니다.
3. 아래 설정으로 연결합니다.

```text
Host: 127.0.0.1
Port: 55432
Database: academic_chat
User: academic
Password: academic_demo
```

4. `students`, `accounts`, `courses`, `course_records`, `graduation_rules`, `required_courses`, `english_requirements`, `student_english_scores`, `sessions` 테이블을 확인합니다. 계정 비밀번호는 해시로 보관합니다.
5. [DataGrip 예시 SQL](datagrip_examples.sql)을 열어 과목과 가상 이수기록, 필수과목을 조회할 수 있습니다. 이는 로컬 데모 DB이므로 DataGrip에서 수정한 값은 앱 조회에도 반영됩니다.

## Postman에서 API 테스트

1. 위의 명령으로 서버를 실행합니다.
2. Postman에서 **Import**를 선택하고 [컬렉션 파일](postman/AcademicChat.postman_collection.json)을 가져옵니다.
3. 컬렉션의 `baseUrl` 기본값은 Docker 주소인 `http://127.0.0.1:8771`입니다. 로컬 SQLite 서버를 사용하면 `http://127.0.0.1:8765`로 변경합니다.
4. 컬렉션을 위에서 아래 순서로 실행합니다. 데모 로그인 뒤 Postman 쿠키 저장소가 `campus_session`을 다음 요청에 전달합니다. 쿠키가 꺼져 있으면 개인 조회 테스트가 실패합니다.
5. 공개 졸업학점 검색, 비로그인 개인 조회 차단, 데모 로그인, 본인 이수기록·졸업요건, 타인 정보 차단 및 로그아웃을 확인합니다. 개인 조회는 유효한 Pickle 키와 도구 호출 모델이 필요합니다.

FastAPI 자동 API 문서는 Docker 실행 후 http://127.0.0.1:8771/docs 에서 확인할 수 있습니다. 로컬 직접 실행의 기본 주소는 http://127.0.0.1:8765/docs 입니다.

## 검색과 대체 크롤링

질문은 다음 순서로 분기합니다. 로그인 상태와 본인 정보는 서버에서 확인합니다.

```mermaid
flowchart TD
    Q[질문] --> D{타인 정보 요청?}
    D -->|예| DENY[조회 거부]
    D -->|아니요| I{개인 학사 질문?}
    I -->|예, 비로그인| LOGIN[로그인 안내]
    I -->|예, 로그인| TOOL[본인 SQL 조회 또는 졸업 비교 도구]
    I -->|아니요| A{공개 학사 질문?}
    A -->|예| V[공개 문서 벡터 검색]
    V -->|근거 있음| ANSWER[출처와 함께 답변]
    V -->|근거 부족| C[공개 게시판 크롤링 및 검증]
    C -->|근거 있음| ANSWER
    C -->|근거 부족| NONE[확인 불가 안내]
    A -->|아니요| G[인사 또는 일반 대화 모델]
```

학기별 수강신청 가능 학점은 별도 기능이 필요하므로 현재 확인 불가를 안내합니다. ‘남은 수강 학점’처럼 졸업 여부가 명시되지 않은 표현은 졸업까지 남은 총 학점으로 해석하고, 답변에 기준을 표시합니다.

개인 졸업 비교는 공통 데모 기준의 총 취득·잔여 학점, 전공기초·전공필수 과목과 TOEIC 점수를 확인합니다. 교양, 전체 평점평균, 부전공·복수전공·심화전공, 영어강의와 대체과목은 계산하지 않습니다. 지원 항목과 제외 항목을 함께 질문하면 지원하는 부분만 비교하고 미확인 항목을 명시합니다. 일반적인 공개 규정 질문은 개인 판정과 구분합니다.

`app/database.py`는 인증된 학생의 이수 및 영어 성적과 공통 규정을 읽어 `app/graduation.py`의 `check_pnu_biz_graduation`에 전달합니다. 이 함수는 총학점, 전공기초, 전공필수, 영어시험을 각각 `met`(충족), `below`(기준 미달), `unknown`(미확인)으로 반환합니다. 필수과목 기준이 누락되거나 영어 성적이 없고 만료·미승인인 경우에는 미확인으로 표시합니다. 결과에 확인하지 않은 요건이 있으므로 최종 졸업 여부는 항상 미확인으로 남깁니다. 챗봇은 질문한 항목에 맞춰 결과를 선택해 표시합니다.

```text
공개 질문 → Chroma 제목·본문 임베딩 검색 → 관련성/적용 범위 검증
   → 근거가 있으면 발췌와 출처 제공
   → 부족하면 Scrapy로 경영학과 공개 공지 탐색 → 동일 기준 검증
   → 결과가 부족하면 답변 보류
```

- 검색 점수는 **코사인 유사도**이며 높을수록 유사합니다. 제목과 본문 앞부분의 임베딩을 결합한 새 컬렉션 `academic_public_v2`를 사용하며, 기존 `academic_public_v1`은 보존합니다. 임계값 `0.38`은 초기값이며 실제 질문·정답 데이터로 추가 평가와 조정이 필요합니다.
- 학생 개인 기록은 벡터 DB에 넣지 않습니다. 질문에 특정 연도나 학기가 들어 있는지에 따라 자료를 필터링하지 않습니다. 원문에 포함된 학기·일정은 출처 정보로 남기므로 실제 적용 여부를 원문에서 확인해야 합니다.
- 크롤러는 `biz.pusan.ac.kr`의 지정된 학부 공지 게시판만 조회하고 `robots.txt`, 요청 횟수·속도·시간 제한을 적용합니다. 로그인 페이지나 임의 URL은 조회하지 않습니다. 사이트 접근 실패나 정책 변경 시 결과가 없을 수 있습니다.
- 크롤링 후보는 자동으로 DB에 영구 적재하지 않습니다. 제공 문서나 크롤링 결과가 실제 최신 규정·해당 학생에게 적용되는지 확인이 필요합니다.

## 테스트

```powershell
uv run python -m unittest discover -s tests -v
cd frontend
npm test
```

자동 테스트는 API와 SQLite를 실제로 실행하고, 유료 Pickle 호출 대신 로컬 HTTP 테스트 서버를 사용합니다. 이는 실제 Pickle 모델의 성능이나 학교 게시판의 가용성을 보장하지 않습니다.

실행 중인 PostgreSQL의 임시 스키마에서 동일 테스트를 실행하려면 다음 명령을 사용합니다. 테스트 스키마는 실행 후 정리하며 실제 데이터는 건드리지 않습니다.

```powershell
$env:TEST_POSTGRES_URL = 'postgresql://academic:academic_demo@127.0.0.1:55432/academic_chat'
uv run python -m scripts.test_postgres
```

로컬 문서 소제목 검색 평가는 `uv run python -m scripts.evaluate_retrieval`로 재실행하며 결과는 [소제목 검색 평가](docs/retrieval_evaluation.md)에 기록됩니다. Docker의 [개선 전 v1](docs/docker_retrieval_evaluation.md)과 [개선 후 v2](docs/docker_retrieval_evaluation_v2.md) 결과도 보관합니다. 자연어 평가의 [개선 전](docs/natural_retrieval_baseline.md), [개선 후](docs/docker_natural_retrieval_improved.md), [추가 질문](docs/natural_retrieval_additional.md) 결과를 비교할 수 있습니다. 두 자연어 질문 세트 모두 개선에 사용한 소규모 예시여서 독립 검증이 아니며 실제 사용자 표현에 대한 정확도를 보장하지 않습니다.

## 주요 한계

- 학교 SSO, 실제 학사 DB, 실제 수강신청은 연결되어 있지 않습니다. 데모 계정과 데이터베이스는 로컬 개발용입니다.
- 졸업 비교는 총 취득 학점, 전공기초·전공필수와 TOEIC 점수만 확인합니다. 영어강의, 영어 대체 인정, 교양, 전체 평점평균, 심화전공과 대체과목·예외를 확인하지 않으며 **최종 졸업 판정이 아닙니다.**
- 유사도 임계값만으로 사실성이나 적용 대상이 보장되지 않습니다. 문서별 조건과 출처 확인이 필요합니다.
- 현재 최초 인덱싱은 명시적인 명령으로 실행합니다. 자동 수집 일정, 문서 승인 워크플로와 운영 수준 보안은 구현하지 않았습니다. 외부에 공개하지 마세요.

자세한 목표와 향후 개선점은 [기술요구사항](IMPLEMENTATION_REQUIREMENTS.md)을 참고하세요.
