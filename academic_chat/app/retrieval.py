from __future__ import annotations

import json
import re
import threading
from functools import lru_cache

from .config import DATA, chroma_path, setting, threshold

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_lock = threading.Lock()


def documents():
    documents = json.loads((DATA / "sources" / "rules_curated.json").read_text(encoding="utf-8"))
    specs = [
        ("graduation_notice_2026.md", "2026년 8월 졸업 관련 공지 요약", "https://biz.pusan.ac.kr/bbs/biz/1095/1448026/artclView.do", "2026-08"),
        ("course_notice_2026_2.md", "2026학년도 2학기 수강제도 안내 요약", "https://ihis.pusan.ac.kr/bbs/biz/1091/1452956/artclView.do?layout=unknown", "2026-2"),
    ]
    for filename, title, url, period in specs:
        text = (DATA / "sources" / filename).read_text(encoding="utf-8-sig")
        # Preserve section boundaries; every retrieved section retains document context.
        sections = re.split(r"(?m)^##\s+", text)[1:]
        for i, part in enumerate(sections):
            heading, _, body = part.partition("\n")
            # Earlier cohort-specific credit tables conflict with the user's single-rule MVP.
            # The shared demo credit rule is the separately curated biz-major-2021 chunk.
            if filename == "course_notice_2026_2.md" and "졸업·수료 이수학점" in heading:
                continue
            segments = re.split(r"(?m)^###\s+([^\n]+)\n", body)
            chunks = [(heading.strip(), segments[0])]
            chunks.extend((f"{heading.strip()} > {segments[j].strip()}", segments[j + 1]) for j in range(1, len(segments) - 1, 2))
            for j, (subheading, chunk) in enumerate(chunks):
                if len(chunk.strip()) < 25:
                    continue
                documents.append({"id": f"{filename}-{i}-{j}", "title": f"{title} / {subheading}", "text": chunk.strip(), "source": title + " (사용자 제공 요약, 해당 학기 공지)", "url": url, "topic": "", "period": period})
    return documents


@lru_cache(maxsize=1)
def embedder():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=MODEL, cache_dir=str(DATA / "models"))


@lru_cache(maxsize=1)
def collection():
    import chromadb
    client = chromadb.PersistentClient(path=chroma_path())
    # Separate collection: preserve v1 as a rollback while rebuilding vectors.
    col = client.get_or_create_collection("academic_public_v2", metadata={"hnsw:space": "cosine"})
    return col


def build_index():
    docs = documents()
    with _lock:
        # Blend the section heading with its opening passage so paraphrased questions
        # can match evidence absent from the heading. Chroma uses cosine similarity.
        import numpy as np
        headings = [d["title"].split(" / ")[-1] for d in docs]
        passages = [heading + '. ' + re.sub(r'\s+', ' ', d['text'])[:450] for d, heading in zip(docs, headings)]
        title_vectors = list(embedder().embed(headings, batch_size=16))
        passage_vectors = list(embedder().embed(passages, batch_size=16))
        vectors = []
        for title_vec, passage_vec in zip(title_vectors, passage_vectors):
            title_vec = title_vec / (np.linalg.norm(title_vec) + 1e-12)
            passage_vec = passage_vec / (np.linalg.norm(passage_vec) + 1e-12)
            combined = title_vec * 0.5 + passage_vec * 0.5
            vectors.append(combined / (np.linalg.norm(combined) + 1e-12))
        col = collection()
        current_ids = {d["id"] for d in docs}
        stale = [item for item in col.get(include=[])["ids"] if item not in current_ids]
        if stale:
            col.delete(ids=stale)
        col.upsert(ids=[d["id"] for d in docs], embeddings=[v.tolist() for v in vectors], documents=[d["text"] for d in docs], metadatas=[{k: str(d[k]) for k in ("title", "source", "url", "topic", "period")} for d in docs])
    return len(docs)


def topics(text: str) -> set[str]:
    patterns = {"졸업": ("졸업", "수료", "학점", "전공필수"), "등록": ("등록", "수강", "신청"), "성적": ("성적", "평점", "학점"), "재이수": ("재이수", "재수강"), "전과": ("전과",), "휴학": ("휴학",), "복학": ("복학",), "장학": ("장학",)}
    return {k for k, vals in patterns.items() if any(v in text for v in vals)}


def primary_topic(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    if '재이수' in text or '재수강' in text:
        return '재이수'
    if '전과' in text:
        return '전과'
    if '복학' in text and '휴학' in text:
        return '복학' if text.rfind('복학') > text.rfind('휴학') else '휴학'
    if re.search(r'휴학(?:기간|사유).{0,10}(?:종료|만료|끝나|끝났)', text):
        return '복학'
    if '평점' in text or ('성적' in text and '시험' not in text):
        return '성적'
    if any(word in text for word in ('여석', '증원', '분반')):
        return '수강'
    for topic, aliases in (
        ("재이수", ("재이수", "재수강")), ("졸업", ("졸업", "수료", "전공필수", "전공기초")),
        ("휴학", ("휴학",)), ("복학", ("복학",)), ("전과", ("전과",)),
        ("장학", ("장학",)), ("성적", ("성적", "평점")),
        ("수강", ("수강",)), ("등록", ("등록",)), ("졸업", ("학점",)),
    ):
        if any(word in text for word in aliases):
            return topic
    return ""


def title_matches_query(query: str, title: str) -> bool:
    """Recognize specific course and policy names without matching generic words."""
    ignored = {"부산대학교", "부산대", "경영학과", "알려줘", "알려주세요", "어떻게", "무엇인가요", "궁금합니다"}
    normalized_title = re.sub(r'\s+', '', title).replace('타학과', '다른학과').replace('같은이름', '동일')
    query = query.replace('타학과', '다른학과').replace('같은 이름', '동일')
    for token in re.findall(r"[가-힣A-Za-z0-9]+", query):
        stem = re.sub(r"(?:은|는|이|가|을|를|의|에서|으로|에)$", "", token)
        if len(stem) >= 3 and stem not in ignored and stem in normalized_title:
            return True
    return False


def academic_query(query: str) -> bool:
    if topics(query) or any(word in query for word in ("전공", "교과", "과목", "학적", "학사", "분반", "증원")):
        return True
    return any(title_matches_query(query, doc["title"]) for doc in documents())


def safe_match(query: str, candidate: dict) -> bool:
    topic = primary_topic(query)
    tagged_topic = candidate.get("topic", "")
    heading = candidate.get("title", "").split(" / ")[-1]
    compact_query = re.sub(r'\s+', '', query)
    evidence = re.sub(r'\s+', '', heading + ' ' + candidate.get('text', ''))
    # A general graduation passage is not evidence for a specific required-course list.
    for specific in ('전공기초', '전공필수'):
        if specific in compact_query and specific not in evidence:
            return False
    if not topic:
        return title_matches_query(query, heading)
    if topic == "졸업" and "학점" in query and "학점" not in heading:
        return False
    # Never treat a passing similarity score or incidental words in a long body as topic relevance.
    if tagged_topic:
        return bool(topic and tagged_topic == topic)
    # For old notices, use the section heading, not the shared document title.
    return bool(topic and (topic in heading or title_matches_query(query, heading)))


def score_candidates(query: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    texts = [query] + [x["title"] for x in candidates]
    vectors = list(embedder().embed(texts, batch_size=16))
    import numpy as np
    q = vectors[0]
    matches = []
    for doc, vec in zip(candidates, vectors[1:]):
        cosine = float(np.dot(q, vec) / (np.linalg.norm(q) * np.linalg.norm(vec) + 1e-12))
        if cosine >= threshold() and safe_match(query, doc):
            matches.append({**doc, "score": round(cosine, 4)})
    return sorted(matches, key=lambda x: x["score"], reverse=True)


def search(query: str) -> list[dict]:
    col = collection()
    if col.count() == 0:
        raise RuntimeError("학사 문서 인덱스가 비어 있습니다. uv run python -m app.index_docs 를 실행해 주세요.")
    vector = next(embedder().embed([query])).tolist()
    result = col.query(query_embeddings=[vector], n_results=min(100, col.count()), include=["documents", "metadatas", "distances"])
    matches = []
    for text, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        score = 1.0 - float(distance)  # cosine distance, larger score means more similar
        doc = {**meta, "text": text, "score": round(score, 4)}
        if score >= threshold() and safe_match(query, doc):
            matches.append(doc)
    return matches[:3]
