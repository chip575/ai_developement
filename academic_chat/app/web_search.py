"""Public web search; never fetch arbitrary URLs returned by a search engine."""
import re
from urllib.parse import urlparse

from ddgs import DDGS


def search_web(query: str) -> list[dict]:
    query = query.strip()
    if not query or len(query) > 200:
        raise ValueError('검색어를 확인해 주세요.')
    # Avoid sending obvious personal identifiers or secrets to a search provider.
    if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b|(?:비밀번호|password|api[_ -]?key|주민등록번호)', query, re.I):
        raise ValueError('검색어에 민감한 정보가 포함되어 있습니다.')
    results = DDGS(timeout=6).text(query, region='kr-kr', max_results=5, backend='duckduckgo')
    found = []
    seen = set()
    for item in results:
        url = item.get('href', '')
        parsed = urlparse(url)
        title = str(item.get('title') or '').strip()
        snippet = str(item.get('body') or '').strip()
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or not title or not snippet or url in seen:
            continue
        seen.add(url)
        found.append({'title': title[:200], 'url': url, 'snippet': snippet[:800]})
    return found
