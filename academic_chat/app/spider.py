"""Restricted, read-only public PNU board spider; invoked as a subprocess."""
import re
from urllib.parse import urlparse

import scrapy

BOARD = "https://biz.pusan.ac.kr/biz/8941/subview.do"


class AcademicSpider(scrapy.Spider):
    name = "pnu_academic"
    allowed_domains = ["biz.pusan.ac.kr"]
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "USER_AGENT": "AcademicFAQMVP/1.0 (public academic notice research)",
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 1,
        "DOWNLOAD_TIMEOUT": 8,
        "RETRY_ENABLED": False,
        "REDIRECT_ENABLED": False,
        "COOKIES_ENABLED": False,
        "CLOSESPIDER_PAGECOUNT": 5,
        "DOWNLOAD_MAXSIZE": 1_000_000,
        "LOG_LEVEL": "ERROR",
        "TELNETCONSOLE_ENABLED": False,
        "REMOTE_CONTROL_ENABLED": False,
    }

    def __init__(self, topic="", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.topic = topic if topic in {"졸업", "수강", "휴학", "복학", "전과", "장학", "성적", "재이수", "등록"} else ""

    async def start(self):
        if self.topic:
            yield scrapy.Request(BOARD, callback=self.parse)

    def parse(self, response):
        seen = set()
        count = 0
        for link in response.css('a[href*="artclView.do"]'):
            label = " ".join(link.css("::text").getall()).strip()
            if self.topic not in label:
                continue
            url = response.urljoin(link.attrib.get("href", ""))
            parsed = urlparse(url)
            if parsed.scheme != "https" or parsed.hostname != "biz.pusan.ac.kr" or not re.fullmatch(r"/bbs/biz/109[15]/\d+/artclView\.do", parsed.path) or parsed.query or url in seen:
                continue
            seen.add(url)
            yield scrapy.Request(url, callback=self.parse_article, meta={"notice_title": label})
            count += 1
            if count >= 3:
                break

    def parse_article(self, response):
        if response.url.split("?", 1)[0] != response.request.url:
            return
        for node in response.css("script, style, nav, header, footer"):
            node.root.drop_tree()
        pieces = [re.sub(r"\s+", " ", x).strip() for x in response.css("body ::text").getall()]
        text = " ".join(x for x in pieces if x)
        if len(text) >= 60:
            yield {"title": response.meta["notice_title"], "text": text[:4000], "url": response.url, "source": "부산대학교 경영학과 공개 공지", "period": "crawled"}
