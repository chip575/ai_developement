from __future__ import annotations

import json
import subprocess
import sys
from urllib.parse import urlparse

import httpx

from .config import ROOT, setting

TOPICS = ("졸업", "수강", "휴학", "복학", "전과", "장학", "성적", "재이수", "등록")


def crawl_academic_notices(question: str) -> list[dict]:
    """Only send a fixed public topic to the crawler, never the user's text."""
    if setting("CRAWLER_ENABLED", "1") != "1":
        return []
    topic = next((item for item in TOPICS if item in question), "")
    if not topic:
        return []
    # Fail closed when robots.txt cannot be checked. A 404 means no robots file.
    try:
        robots = httpx.get("https://biz.pusan.ac.kr/robots.txt", timeout=5, follow_redirects=False)
        if robots.status_code not in (200, 404):
            return []
        cmd = [sys.executable, "-m", "scrapy", "runspider", str(ROOT / "app" / "spider.py"), "-a", f"topic={topic}", "-o", "-:jsonlines"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=22, cwd=str(ROOT))
        if proc.returncode != 0:
            return []
        found = []
        for line in proc.stdout.splitlines():
            try:
                item = json.loads(line)
                url = urlparse(item.get("url", ""))
                if url.scheme == "https" and url.hostname == "biz.pusan.ac.kr" and url.path.startswith("/bbs/biz/"):
                    found.append(item)
            except (ValueError, TypeError):
                continue
        return found
    except (httpx.HTTPError, subprocess.TimeoutExpired, OSError):
        return []
