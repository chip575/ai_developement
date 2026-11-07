from datetime import date
import unittest

from app.graduation import check_pnu_biz_graduation
from app.chat import format_student_result


class GraduationFunctionTests(unittest.TestCase):
    def setUp(self):
        self.courses = [
            {'category': category, 'code': f'{category}{i}', 'name': f'{category}과목{i}', 'credits': 3}
            for category, count in (('전공기초', 4), ('전공필수', 9)) for i in range(count)
        ]
        self.record = {'student': {'name': '가상 학생'}, 'total_credits': 126, 'recognized': [{'course_code': c['code'], 'earned_credits': 3} for c in self.courses], 'note': '데모'}
        self.rule = {'total_credits': 126, 'source': '공통 데모'}
        self.english_rule = {'exam_type': 'TOEIC', 'minimum_score': 800, 'source': '데모'}
        self.today = date(2026, 11, 7)

    def check(self, *, courses=None, scores=None, english_rule='default'):
        return check_pnu_biz_graduation(record=self.record, rule=self.rule, required_courses=self.courses if courses is None else courses, english_rule=self.english_rule if english_rule == 'default' else english_rule, english_scores=scores or [], today=self.today)

    def test_checked_items_met_do_not_decide_final_graduation(self):
        score = {'exam_type':'TOEIC', 'score':800, 'taken_on':'2026-01-01', 'valid_until':'2027-01-01', 'approval_status':'approved'}
        result = self.check(scores=[score])
        self.assertEqual(result['checks']['total_credits']['status'], 'met')
        self.assertEqual(result['checks']['major_basic']['status'], 'met')
        self.assertEqual(result['checks']['major_required']['status'], 'met')
        self.assertEqual(result['english']['status'], 'met')
        self.assertEqual(result['overall_status'], 'unknown')

    def test_incomplete_required_course_rule_is_unknown(self):
        result = self.check(courses=self.courses[:-1])
        self.assertEqual(result['checks']['major_required']['status'], 'unknown')
        answer = format_student_result({'name':'check_my_graduation', 'data':result}, '내 전공필수 남은 과목 알려줘')['answer']
        self.assertIn('기준이 불완전', answer)
        self.assertNotIn('모두 이수', answer)

    def test_english_selects_best_valid_approved_score(self):
        base = {'exam_type':'TOEIC', 'taken_on':'2026-01-01', 'valid_until':'2027-01-01', 'approval_status':'approved'}
        scores = [{**base, 'score':750}, {**base, 'score':850, 'approval_status':'pending'}, {**base, 'score':900, 'valid_until':'2026-02-01'}]
        result = self.check(scores=scores)
        self.assertEqual(result['english']['score'], 750)
        self.assertEqual(result['english']['remaining_score'], 50)
        self.assertEqual(result['english']['status'], 'below')
        self.assertEqual(self.check(scores=[])['english']['status'], 'unknown')
        self.assertEqual(self.check(scores=scores, english_rule=None)['english']['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
