from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import database
from .chat import respond
from .config import DATA, ROOT, setting


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="부산대학교 경영학과 학사 챗봇", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/assets", StaticFiles(directory=ROOT / "frontend" / "dist" / "assets", check_dir=False), name="frontend_assets")


def verify_origin(request: Request):
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "허용되지 않은 요청입니다.")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=100)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


@app.get("/")
def home():
    frontend = ROOT / "frontend" / "dist" / "index.html"
    return FileResponse(frontend if frontend.is_file() else ROOT / "static" / "index.html")


@app.get("/api/sources/regulations.pdf")
def source_pdf():
    return FileResponse(DATA / "sources" / "regulations.pdf", media_type="application/pdf")


@app.get("/api/session")
def session(response: Response, campus_session: str | None = Cookie(default=None)):
    response.headers["Cache-Control"] = "no-store"
    user = database.session_user(campus_session)
    return {"user": user, "access_mode": "student" if user else "guest"}


@app.post("/api/login")
def login(body: LoginRequest, request: Request, response: Response, campus_session: str | None = Cookie(default=None)):
    verify_origin(request)
    result = database.login(body.username, body.password)
    if result is None:
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다.")
    token, user = result
    database.logout(campus_session)
    response.set_cookie("campus_session", token, httponly=True, samesite="strict", secure=setting("COOKIE_SECURE", "0") == "1", max_age=database.SESSION_SECONDS, path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"user": user}


@app.post("/api/logout")
def logout(request: Request, response: Response, campus_session: str | None = Cookie(default=None)):
    verify_origin(request)
    database.logout(campus_session)
    response.delete_cookie("campus_session", path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"ok": True}


@app.post("/api/chat")
def chat(body: ChatRequest, request: Request, response: Response, campus_session: str | None = Cookie(default=None)):
    verify_origin(request)
    if not body.message.strip():
        raise HTTPException(422, "질문을 입력해 주세요.")
    user = database.session_user(campus_session)
    result = respond(body.message.strip(), user)
    response.headers["Cache-Control"] = "no-store"
    return {**result, "user": user, "access_mode": "student" if user else "guest"}
