# PNU 도우미 — 이메일 전달용 실행 안내

부산대학교 경영학과 학사 안내와 가상 학생의 학점·졸업요건 조회를 시험하는 로컬 데모입니다. 이 폴더만으로 프런트엔드, FastAPI, PostgreSQL과 학사 문서를 실행할 수 있습니다. 실제 학사 시스템이나 학교 계정과는 연결되지 않습니다.

## 준비물

- Windows PC와 인터넷 연결
- [Docker Desktop](https://www.docker.com/products/docker-desktop/): 설치한 뒤 실행하세요. Docker Desktop의 설치 안내에 따라 WSL 설정이나 PC 재시작이 필요할 수 있습니다.
- 본인이 사용할 수 있는 **Pickle API 키**와 해당 모델 사용 권한. AI 모델 호출에 비용이 발생할 수 있습니다.

Python, Node.js, uv 또는 다른 프로젝트를 별도로 설치할 필요는 없습니다. ZIP을 완전히 압축 해제한 다음 아래 순서대로 진행하세요.

## 1. PowerShell 열기

압축 해제한 `academic_chat` 폴더를 파일 탐색기로 열고, 탐색기 주소창에 `powershell`을 입력한 뒤 Enter를 누릅니다. 이 폴더가 PowerShell의 현재 위치여야 합니다.

## 2. 예시 API 키 수정하기

PowerShell에서 다음 명령을 실행합니다.

```powershell
notepad .env
```

파일에 들어 있는 `YOUR_PICKLE_API_KEY`는 작동하지 않는 예시입니다. 아래처럼 **본인의 실제 키**로 교체하고 저장하세요. `#`으로 시작하는 줄은 수정 방법을 설명하는 주석입니다.

```dotenv
# 아래 예시를 지우고 본인의 실제 Pickle API 키를 입력하세요.
PICKLE_API_KEY=여기에_본인의_Pickle_API_키
```

키의 앞뒤에 따옴표나 공백을 넣지 마세요. `.env`를 삭제했다면 `Copy-Item .env.example .env`를 실행한 다음 `notepad .env`로 키를 입력하세요. 이 전달용 ZIP에는 실제 키가 들어 있지 않습니다. 키는 별도 안전한 방법으로 전달받거나 직접 발급받아야 합니다.

## 3. 서버와 화면 실행하기

Docker Desktop이 실행 중인지 확인한 다음 PowerShell에서 입력합니다.

```powershell
docker compose up --build -d
```

처음 실행할 때는 Docker 이미지와 프런트엔드·서버 의존성, 임베딩 모델을 인터넷에서 내려받고 문서 검색 인덱스를 만듭니다. 완료까지 몇 분 이상 걸릴 수 있습니다. 진행 상황과 오류는 아래 명령으로 확인합니다. 로그 보기를 끝낼 때는 `Ctrl+C`를 누릅니다. 서버는 계속 실행됩니다.

```powershell
docker compose logs -f app
```

로그에 `Uvicorn running`이 표시되면 브라우저에서 **http://127.0.0.1:8771/** 을 여세요. API 문서는 http://127.0.0.1:8771/docs 입니다. 로그인하지 않아도 공개 안내를 사용할 수 있습니다.

| 가상 계정 | 비밀번호 | 예시 데이터 |
|---|---|---|
| `student` | `demo1234` | 김민준, 취득 99학점, TOEIC 750점 |
| `student2` | `demo1234` | 이서연, 취득 3학점, TOEIC 830점 |

개인 질의의 SQL 생성과 일반 AI 대화는 올바른 API 키, 허용된 모델, 네트워크가 필요합니다. 개인 조회 결과와 졸업요건은 테스트용 가상 자료이며 최종 졸업 판정이 아닙니다.

## 4. 종료와 다시 실행

```powershell
docker compose down
```

다시 시작하려면 `docker compose up --build -d`를 실행하세요. 일반적인 종료 명령은 PostgreSQL 데이터, 검색 인덱스와 임베딩 모델의 Docker 볼륨을 유지합니다. `.env`를 수정한 후에도 같은 시작 명령을 다시 실행해야 변경이 반영됩니다.

## 문제가 생기면

- **Docker 명령을 찾을 수 없음:** Docker Desktop 설치를 확인하고 PowerShell을 다시 여세요.
- **Docker 엔진에 연결할 수 없음:** Docker Desktop을 실행하고 완전히 시작될 때까지 기다리세요.
- **포트 사용 중:** `.env`의 `APP_PORT=8771` 또는 `POSTGRES_PORT=55432`를 사용하지 않는 번호로 변경하고 다시 실행하세요. 웹 포트를 바꾸면 브라우저 주소에도 새 번호를 사용합니다. 같은 이름의 프로세스 환경 변수가 설정돼 있으면 `.env`보다 우선할 수 있습니다.
- **AI 기능 실패:** `.env`의 키와 모델 이름, 계정 권한, 인터넷 연결을 확인하고 재시작하세요. `YOUR_PICKLE_API_KEY`는 예시여서 작동하지 않습니다.
- **모델 다운로드 실패 또는 화면이 열리지 않음:** 인터넷 연결을 확인하고 `docker compose logs --tail 100 app`으로 오류를 확인하세요.

## 전송본에 포함된 내용

Gmail의 차단 형식을 피할 수 있도록 별도의 `.cmd`, `.ps1`, `.js` 파일을 포함하지 않았습니다. 실행 스크립트 대신 위 Docker Compose 명령을 사용하세요. Vue 소스는 빌드 가능한 TypeScript 파일로 제공하며 화면과 기능은 포함됩니다. Gmail의 콘텐츠 검사에 따라 이 ZIP도 차단될 수 있습니다. 전송이 계속 차단되면 안전한 파일임을 확인한 후 Google Drive 공유를 이용할 수 있습니다.
