"""Small, manually labeled natural-language checks for public academic search."""
import argparse
from unittest.mock import patch

from app.chat import respond
from app.config import ROOT
from app.retrieval import documents, search

CASES = [
    ('휴학할 수 있는 기간이 얼마나 돼?', ['reg-064']),
    ('휴학이 끝나면 언제 복학해야 하나요?', ['reg-065']),
    ('다른 학과로 전과할 조건은?', ['reg-063']),
    ('재수강할 수 있는 성적 기준은?', ['reg-060']),
    ('졸업하려면 전체 평점이 몇 점이어야 하나요?', ['reg-056']),
    ('경영학과 졸업에 필요한 학점은?', ['biz-major-2021', 'reg-052']),
    ('장학금은 어떤 학생에게 주나요?', ['reg-083']),
    ('등록을 완료하려면 무엇이 필요한가요?', ['reg-048']),
    ('1차 수강신청 일정이 어떻게 되나요?', ['course_notice_2026_2.md-0-0']),
    ('경영통계학 분반은 누가 신청할 수 있나요?', ['course_notice_2026_2.md-2-1']),
    ('전공 수업 여석 조정은 어떻게 신청하나요?', ['course_notice_2026_2.md-2-3']),
    ('같은 이름의 타학과 수업을 수강해도 되나요?', ['course_notice_2026_2.md-3-0', 'course_notice_2026_2.md-3-2']),
    ('경영학과 전공기초 필수과목 목록을 알려줘', ['biz-major-2021', 'course_notice_2026_2.md-3-1']),
    ('교과구분 정정은 어떻게 신청하나요?', ['course_notice_2026_2.md-6-0', 'graduation_notice_2026.md-2-0']),
    ('표준외국어능력시험 성적표 제출 안내', ['graduation_notice_2026.md-1-0']),
    ('조기졸업 신청서 제출 안내', ['graduation_notice_2026.md-4-0']),
]

ADDITIONAL_CASES = [
    ('등록을 마치려면 등록금 납부 외에 무엇을 해야 하나요?', ['reg-048']),
    ('일반휴학은 총 몇 학기까지 가능한가요?', ['reg-064']),
    ('휴학 사유가 끝나면 어떻게 해야 하나요?', ['reg-065']),
    ('전과하려면 1학년 수료가 필요한가요?', ['reg-063']),
    ('재이수할 때 받을 수 있는 최고 성적은?', ['reg-060']),
    ('성적평점평균이 어느 정도면 졸업할 수 있나요?', ['reg-056']),
    ('성적증명서의 교과구분을 바꾸려면?', ['course_notice_2026_2.md-6-0', 'graduation_notice_2026.md-2-0']),
    ('조기졸업을 포기할 때 제출할 서류는?', ['graduation_notice_2026.md-4-0']),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--set', choices=('development', 'additional'), default='development')
    args = parser.parse_args()
    corpus = documents()
    by_title_text = {(doc['title'], doc['text']): doc['id'] for doc in corpus}
    rows = []
    for question, expected in (ADDITIONAL_CASES if args.set == 'additional' else CASES):
        matches = search(question)
        ids = [by_title_text.get((m['title'], m['text']), '?') for m in matches]
        with patch('app.chat.search', return_value=matches), patch('app.chat.crawl_academic_notices', return_value=[]), patch('app.chat.general_response', return_value={'answer':'일반 대화 분기', 'sources':[], 'route':'general_chat'}):
            result = respond(question, None)
        first = bool(result['route'] == 'vector' and ids and ids[0] in expected)
        top3 = result['route'] in ('vector', 'not_found') and any(id_ in expected for id_ in ids)
        rows.append((question, expected, ids, result['route'], first, top3, ' '.join(result['answer'].split())[:100]))
    n = len(rows)
    first = sum(r[4] for r in rows)
    top3 = sum(r[5] for r in rows)
    lines = ['# 공개 학사 자연어 검색 평가', '', '- 직접 작성한 소규모 질문과 수동 정답 조각 기준이며 실제 사용자 질문 전체의 정확도가 아닙니다.', '- 검색 엔진과 응답 분기를 확인합니다. 일반 모델과 대체 크롤러는 호출하지 않았습니다.', f'- 첫 답변 일치: {first}/{n} ({first/n:.1%})', f'- 상위 3개에 정답 포함: {top3}/{n} ({top3/n:.1%})', '', '| 질문 | 정답 ID | 실제 검색 후보 | 응답 분기 | 결과 | 응답 발췌 |', '|---|---|---|---|---|---|']
    if args.set == 'additional':
        lines.insert(4, '- 추가 질문도 결과를 확인하고 분류 규칙을 수정했으므로 독립 검증이 아닙니다.')
    else:
        lines.insert(4, '- 이 질문들의 결과를 보고 검색 방식을 조정했으므로 독립 검증이 아닙니다.')
    for q, exp, ids, route, ok, _, excerpt in rows:
        escape = lambda x: str(x).replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {escape(q)} | {escape(', '.join(exp))} | {escape(', '.join(ids) or '-')} | {route} | {'일치' if ok else '불일치'} | {escape(excerpt)} |")
    out = ROOT / 'docs' / ('natural_retrieval_improved.md' if args.set == 'development' else 'natural_retrieval_additional.md')
    out.parent.mkdir(exist_ok=True)
    out.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(f'first={first}/{n} top3={top3}/{n} report={out}')


if __name__ == '__main__':
    main()
