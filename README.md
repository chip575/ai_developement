# PNU 도우미

부산대학교 경영학과의 공개 학사 안내와 가상 학생의 학점·졸업요건을 확인하는 데모입니다. 실제 학교 계정이나 학사 시스템과 연결되지 않습니다. 앱 코드는 [academic_chat](academic_chat/)에 있습니다.

## 시작하기

Windows에서 Docker Desktop을 설치·실행하고, PowerShell에서 다음 명령을 입력합니다.

```powershell
git clone https://github.com/chip575/ai_developement.git
cd ai_developement/academic_chat
Copy-Item .env.example .env
notepad .env
```

열린 `.env`의 `PICKLE_API_KEY=` 뒤에 **본인의 Pickle API 키**를 입력하고 저장하세요. 실제 키와 개인 DB는 저장소에 포함하지 않습니다. 키의 유효성 및 모델 사용 권한에 따라 AI 기능과 호출 비용이 달라질 수 있습니다.

```powershell
docker compose up --build -d
docker compose logs -f app
```

첫 실행에는 인터넷 연결이 필요하며, 이미지·패키지·검색 모델 다운로드와 인덱싱에 시간이 걸립니다. `Uvicorn running`이 표시되면 [http://127.0.0.1:8771](http://127.0.0.1:8771)을 여세요. `Ctrl+C`는 로그 보기만 종료합니다.

학생 기능은 가상 계정 `student` / `demo1234`로 시험할 수 있습니다. 종료 명령은 `docker compose down`입니다. 포트 설정, 데이터 구성과 문제 해결은 [상세 안내](academic_chat/README.md)를 확인하세요.

이 프로젝트는 localhost에서 실행하는 데모입니다. 데이터베이스와 학생 계정에는 데모용 자격 증명이 사용되므로 운영 서비스로 외부에 공개하지 마세요.
