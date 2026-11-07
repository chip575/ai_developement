"""Pure comparison of the supported demo requirements; never a final graduation decision."""
from datetime import date, datetime, timedelta, timezone


def check_pnu_biz_graduation(*, record: dict, rule: dict, required_courses: list[dict], english_rule: dict | None, english_scores: list[dict], today: date | None = None) -> dict:
    """Compare authenticated student's DB data against the common demo rule.

    Per-item status is met, below, or unknown. The caller supplies only records
    fetched for the authenticated student. Missing TOEIC data and incomplete
    required-course rules cannot be interpreted as a failed or passed condition.
    """
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    english = {'status': 'unknown', 'exam_type': 'TOEIC', 'required_score': english_rule['minimum_score'] if english_rule else None, 'score': None, 'remaining_score': None, 'valid_until': None, 'source': english_rule['source'] if english_rule else None}
    eligible = []
    for score in english_scores:
        try:
            if score['exam_type'] == 'TOEIC' and score['approval_status'] == 'approved' and date.fromisoformat(score['taken_on']) <= today <= date.fromisoformat(score['valid_until']):
                eligible.append(score)
        except (TypeError, ValueError, KeyError):
            continue
    if english_rule and eligible:
        best = max(eligible, key=lambda score: (score['score'], score['taken_on']))
        minimum = english_rule['minimum_score']
        english.update(score=best['score'], remaining_score=max(0, minimum - best['score']), valid_until=best['valid_until'], status='met' if best['score'] >= minimum else 'below')

    recognized = {row['course_code']: row for row in record['recognized']}
    major_summary, missing = [], []
    # The current common demo requirement has 4 basic and 9 core courses.
    for category, expected_count in (('전공기초', 4), ('전공필수', 9)):
        courses = [c for c in required_courses if c['category'] == category]
        if len(courses) != expected_count or len({c['code'] for c in courses}) != expected_count:
            major_summary.append({'category': category, 'status': 'unknown', 'earned_credits': None, 'required_credits': None, 'remaining_credits': None})
            continue
        required_credits = sum(c['credits'] for c in courses)
        earned_credits = sum(min(c['credits'], recognized[c['code']]['earned_credits']) for c in courses if c['code'] in recognized)
        remaining = max(0, required_credits - earned_credits)
        major_summary.append({'category': category, 'status': 'below' if remaining else 'met', 'earned_credits': earned_credits, 'required_credits': required_credits, 'remaining_credits': remaining})
        missing.extend(c for c in courses if c['code'] not in recognized or recognized[c['code']]['earned_credits'] < c['credits'])

    earned = record['total_credits']
    required_total = rule['total_credits']
    total_remaining = max(0, required_total - earned)
    checks = {'total_credits': {'status': 'below' if total_remaining else 'met', 'current': earned, 'required': required_total, 'remaining': total_remaining}, 'major_basic': major_summary[0], 'major_required': major_summary[1], 'english': english}
    return {'student_name': record['student']['name'], 'curriculum': '공통 데모 기준', 'earned_credits': earned, 'required_credits': required_total, 'remaining_credits': total_remaining, 'major_summary': major_summary, 'missing_courses': missing, 'english': english, 'checks': checks, 'overall_status': 'unknown', 'source': rule['source'], 'unchecked': ['실제 적용 교육과정', '교양 세부요건', '전공선택 학점', '전체 평점평균', '영어강의 이수 여부 및 영어 대체인정', '심화전공 및 기타 졸업요건', '대체과목·개인별 인정 내역'], 'note': record['note']}
