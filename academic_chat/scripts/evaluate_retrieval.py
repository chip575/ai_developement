"""Evaluate 37 source headings against the actual Chroma index and retrieval filters.

This is an optimistic same-heading smoke test, not a labeled natural-question benchmark.
It does not call paid models or the live crawler.
"""
from collections import Counter
from pathlib import Path
import re
from unittest.mock import patch

from app.chat import respond
from app.config import ROOT, threshold
from app.retrieval import academic_query, collection, documents, embedder, safe_match


def query_for(doc):
    heading = doc['title'].split(' / ')[-1].split(' > ')[-1]
    return re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', heading).strip()


def main():
    docs = documents()
    queries = [query_for(doc) for doc in docs]
    vectors = [v.tolist() for v in embedder().embed(queries, batch_size=16)]
    col = collection()
    result = col.query(query_embeddings=vectors, n_results=min(100, col.count()), include=['documents', 'metadatas', 'distances'])
    rows = []
    for n, (doc, query) in enumerate(zip(docs, queries)):
        raw = []
        for id_, text, meta, dist in zip(result['ids'][n], result['documents'][n], result['metadatas'][n], result['distances'][n]):
            raw.append({**meta, 'id': id_, 'text': text, 'score': 1.0-float(dist)})
        eligible = [item for item in raw if item['score'] >= threshold() and safe_match(query, item)][:3]
        # Exercise the real response router and formatter, using the real batched Chroma results.
        # No paid model calls or external crawler requests in this repeatable benchmark.
        with patch('app.chat.search', return_value=eligible), patch('app.chat.crawl_academic_notices', return_value=[]), patch('app.chat.general_response', return_value={'answer': '일반 대화 분기', 'sources': [], 'route': 'general_chat'}):
            actual = respond(query, None)
        diverted = actual['route'] not in ('vector', 'not_found')
        exact_top1 = bool(actual['route'] == 'vector' and eligible and eligible[0]['id'] == doc['id'] and actual['answer'].startswith(doc['text'][:1100]))
        exact_top3 = any(x['id'] == doc['id'] for x in eligible) and not diverted
        match = next((x for x in raw if x['id'] == doc['id']), None)
        reason = '다른 분기' if diverted else ('일치' if exact_top1 else ('검색 안 됨' if not eligible else '다른 조각 우선'))
        rows.append((query, doc['id'], match['score'] if match else None, eligible[0]['title'] if eligible and not diverted else '-', exact_top1, exact_top3, reason, actual['route'], ' '.join(actual['answer'].split())[:100]))
    total = len(rows)
    top1 = sum(r[4] for r in rows)
    top3 = sum(r[5] for r in rows)
    lines = ['# 공개 학사 문서 소제목 검색 평가', '', f'- 평가 대상: {total}개 문서 조각; 컬렉션 저장 수: {col.count()}개', f'- 입력: 각 조각의 제목 또는 소제목에서 번호를 뺀 문구. 같은 문서에서 만든 시험이므로 실제 자연어 성능보다 낙관적입니다.', f'- 실제 응답이 기대 조각을 출력: {top1}/{total} ({top1/total:.1%})', f'- 검색 필터 통과 후 정답 상위 3개: {top3}/{total} ({top3/total:.1%})', f'- 실제 응답 분기와 본문 발췌를 검사하고 제목/주제 검사 및 threshold({threshold():g})를 반영했습니다. 검색 결과의 내용 정확성·최신성은 별도 검증하지 않았습니다.', '- 크롤러와 일반 대화 모델은 테스트 대역으로 대체했습니다. 실제 챗봇에서는 검색 실패 후 크롤링 등으로 결과가 달라질 수 있습니다.', '', '| 입력 소주제 | 기대 조각 ID | 기대 조각 유사도 (상위 100개 이내) | 실제 첫 후보 | 분기 | 실제 출력 발췌 | 결과 |', '|---|---|---:|---|---|---|---|']
    for query, id_, score, first, top, top_three, reason, route, excerpt in rows:
        esc = lambda s: str(s).replace('|', '\\|').replace('\n', ' ')
        score_text = f'{score:.3f}' if score is not None else '-'
        lines.append(f"| {esc(query)} | {esc(id_)} | {score_text} | {esc(first)} | {esc(route)} | {esc(excerpt)} | {reason} |")
    out = ROOT / 'docs' / 'retrieval_evaluation.md'
    out.parent.mkdir(exist_ok=True)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'top1={top1}/{total} top3={top3}/{total} reasons={dict(Counter(r[6] for r in rows))}')
    print(f'report={out}')


if __name__ == '__main__':
    main()
