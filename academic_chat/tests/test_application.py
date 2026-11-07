from __future__ import annotations

import json
import asyncio
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.seed import seed
from app.retrieval import documents, safe_match
from app.spider import AcademicSpider
from scrapy.http import HtmlResponse, Request


class PickleStub(BaseHTTPRequestHandler):
    calls = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PickleStub.calls.append({"path": self.path, "body": body})
        prompt = body["messages"][-1]["content"]
        name = "check_my_graduation" if "졸업요건" in prompt else "get_my_academic_record"
        if any(t.get("function", {}).get("name") == "submit_personal_sql" for t in body.get("tools", [])):
            if prompt == '학점 알려줘':
                query = 'SELECT SUM(earned_credits) AS total_credits FROM recognized_courses'
            elif '개인 정보' in prompt:
                query = 'SELECT name, department, admission_year, curriculum FROM student_profile'
            else:
                query = 'SELECT student_profile.name AS student_name, course_records.name AS course_name, course_records.earned_credits FROM student_profile CROSS JOIN course_records'
            message = {"role":"assistant","content":None,"tool_calls":[{"id":"call_test","type":"function","function":{"name":"submit_personal_sql","arguments":json.dumps({'sql':query})}}]}
            reason = "tool_calls"
        elif body.get("tools") and any(t.get("function", {}).get("name") == "get_my_academic_record" for t in body["tools"]):
            message = {"role":"assistant","content":None,"tool_calls":[{"id":"call_test","type":"function","function":{"name":name,"arguments":"{}"}}]}
            reason = "tool_calls"
        else:
            message = {"role":"assistant", "content":"일반 대화 응답입니다."}
            reason = "stop"
        result = {"id":"chatcmpl-test", "object":"chat.completion", "created":1, "model":"test-model", "choices":[{"index":0,"finish_reason":reason,"message":message}]}
        data = json.dumps(result).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, {"ACADEMIC_DB_PATH": str(Path(cls.tmp.name) / "test.db"), "PICKLE_API_KEY":"test-key", "PICKLE_TOOL_MODEL":"test-model"})
        cls.env.start()
        seed()
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), PickleStub)
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        os.environ["PICKLE_BASE_URL"] = f"http://127.0.0.1:{cls.server.server_port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.env.stop()
        cls.tmp.cleanup()

    def setUp(self):
        self.client = TestClient(app)
        PickleStub.calls.clear()

    def login(self, client, user="student"):
        r = client.post("/api/login", json={"username":user,"password":"demo1234"})
        self.assertEqual(r.status_code, 200)

    def test_guest_personal_requires_login_without_model_or_db(self):
        res = self.client.post("/api/chat", json={"message":"내 졸업요건 확인해줘"}).json()
        self.assertEqual(res["route"], "login")
        self.assertTrue(res["login_required"])
        self.assertEqual(PickleStub.calls, [])

    def test_remaining_credits_route_and_semester_distinction(self):
        question = "남은 수강 학점 얼마나 남았어?"
        with patch("app.chat.search") as search:
            guest = self.client.post("/api/chat", json={"message": question}).json()
            self.assertEqual(guest["route"], "login")
            self.assertTrue(guest["login_required"])
            search.assert_not_called()
        self.login(self.client)
        with patch("app.chat.search") as search:
            result = self.client.post("/api/chat", json={"message": question}).json()
            self.assertEqual(result["route"], "graduation")
            self.assertIn("남은 총 학점: 27학점", result["answer"])
            self.assertIn("학기별 수강신청 가능 학점은 확인하지 않습니다", result["answer"])
            search.assert_not_called()
        for question in ("학점이 얼마나 남았어?", "남아있는 졸업 학점 알려줘"):
            with self.subTest(question=question):
                result = self.client.post("/api/chat", json={"message": question}).json()
                self.assertEqual(result["route"], "graduation")
        with patch("app.chat.search") as search, patch("app.chat.invoke_student_tool") as tool:
            result = self.client.post("/api/chat", json={"message": "이번 학기 수강신청 가능한 학점이 얼마나 남았어?"}).json()
            self.assertEqual(result["route"], "semester_credits_unavailable")
            search.assert_not_called()
            tool.assert_not_called()

    def test_short_credit_question_uses_personal_record(self):
        question = '학점 알려줘'
        with patch('app.chat.search') as search:
            guest = self.client.post('/api/chat', json={'message': question}).json()
            self.assertEqual(guest['route'], 'login')
            search.assert_not_called()
        self.login(self.client)
        with patch('app.chat.search') as search:
            result = self.client.post('/api/chat', json={'message': question}).json()
            self.assertEqual(result['route'], 'student_query')
            self.assertIn('99', result['answer'])
            self.assertIn('SUM', result['sql'])
            self.assertNotIn('이수 내역:', result['answer'])
            search.assert_not_called()
        with patch('app.chat.search', return_value=[]), patch('app.chat.crawl_academic_notices', return_value=[]):
            result = self.client.post('/api/chat', json={'message':'졸업 기준 학점 알려줘'}).json()
            self.assertEqual(result['route'], 'not_found')

    def test_elliptical_course_question_before_and_after_login(self):
        question = '지금 내가 들은 것은?'
        with patch('app.chat.general_response') as general, patch('app.chat.search') as search:
            result = self.client.post('/api/chat', json={'message': question}).json()
            self.assertEqual(result['route'], 'login')
            self.assertTrue(result['login_required'])
            general.assert_not_called()
            search.assert_not_called()
        self.login(self.client)
        with patch('app.chat.general_response') as general:
            result = self.client.post('/api/chat', json={'message': question}).json()
            self.assertEqual(result['route'], 'student_query')
            self.assertIn('김민준', result['answer'])
            self.assertIn('경영학원론', result['answer'])
            general.assert_not_called()
        other = TestClient(app)
        self.login(other, 'student2')
        result = other.post('/api/chat', json={'message': question}).json()
        self.assertEqual(result['route'], 'student_query')
        self.assertIn('이서연', result['answer'])
        self.assertNotIn('김민준', result['answer'])

    def test_student_tool_failure_does_not_fall_back_to_public_search(self):
        self.login(self.client)
        with patch('app.chat.invoke_personal_query', side_effect=RuntimeError('unavailable')), patch('app.chat.search') as search:
            result = self.client.post('/api/chat', json={'message':'학점 알려줘'}).json()
            self.assertEqual(result['route'], 'tool_error')
            self.assertIn('개인 조회 도구', result['answer'])
            search.assert_not_called()

    def test_profile_question_uses_generated_sql_without_extra_courses(self):
        self.login(self.client)
        result = self.client.post('/api/chat', json={'message':'내 개인 정보 알려줘'}).json()
        self.assertEqual(result['route'], 'student_query')
        self.assertIn('김민준', result['answer'])
        self.assertIn('경영학과', result['answer'])
        self.assertNotIn('경영학원론', result['answer'])
        self.assertIn('student_profile', result['sql'])
        payload = json.dumps(PickleStub.calls[-1]['body'], ensure_ascii=False)
        self.assertNotIn('김민준', payload)
        self.assertNotIn('99학점', payload)

    def test_personal_english_score_requires_login_and_compares(self):
        for message in ('영어 점수는 얼마나 남았어?', '내 토익 점수 졸업요건 충족했어?'):
            with self.subTest(message=message), patch('app.chat.general_response') as general, patch('app.chat.invoke_student_tool') as tool:
                result = self.client.post('/api/chat', json={'message': message}).json()
                self.assertEqual(result['route'], 'login')
                general.assert_not_called()
                tool.assert_not_called()
        self.login(self.client)
        result = self.client.post('/api/chat', json={'message':'영어 점수는 얼마나 남았어?'}).json()
        self.assertEqual(result['route'], 'graduation')
        self.assertIn('750 / 800점 · 미충족 · 부족 50점', result['answer'])
        self.assertNotIn('총 취득 학점', result['answer'])
        self.assertNotIn('전공필수', result['answer'])
        self.assertEqual(len(result['sources']), 1)
        other = TestClient(app)
        self.login(other, 'student2')
        result = other.post('/api/chat', json={'message':'내 토익 점수 졸업요건 충족했어?'}).json()
        self.assertIn('830 / 800점 · 충족 · 부족 0점', result['answer'])
        self.assertNotIn('750 / 800', result['answer'])

    def test_english_score_unknown_if_missing_expired_or_pending(self):
        with database.connect() as db:
            db.execute('UPDATE student_english_scores SET approval_status=? WHERE student_id=1', ('pending',))
        try:
            self.assertEqual(database.graduation(1)['english']['status'], 'unknown')
            with database.connect() as db:
                db.execute('UPDATE student_english_scores SET approval_status=?,valid_until=? WHERE student_id=1', ('approved', '2000-01-01'))
            self.assertEqual(database.graduation(1)['english']['status'], 'unknown')
            with database.connect() as db:
                db.execute('DELETE FROM english_requirements')
            self.assertEqual(database.graduation(1)['english']['status'], 'unknown')
        finally:
            with database.connect() as db:
                db.execute('UPDATE student_english_scores SET approval_status=?,valid_until=? WHERE student_id=1', ('approved', '2028-07-31'))
                db.execute('INSERT OR IGNORE INTO english_requirements VALUES (?,?,?,?)', ('business-2021-demo', 'TOEIC', 800, '테스트 기준'))

    def test_graduation_questions_route_supported_and_excluded_items(self):
        supported = ('전공필수 몇 개 남았어?', '내 전공필수 과목 뭐 남았어?', '졸업요건 충족했어?')
        for question in supported:
            with self.subTest(guest=question):
                self.assertEqual(self.client.post('/api/chat', json={'message':question}).json()['route'], 'login')
        self.login(self.client)
        for question in supported:
            with self.subTest(student=question):
                result = self.client.post('/api/chat', json={'message':question}).json()
                self.assertEqual(result['route'], 'graduation')
                self.assertIn('최종 졸업 판정이 아닌', result['answer'])
        for question, item in (('내 교양 몇 학점 남았어?', '교양'), ('내 평점이 졸업 기준을 충족해?', '평점'), ('내 부전공 몇 개 남았어?', '전공')):
            with self.subTest(excluded=question), patch('app.chat.invoke_student_tool') as tool:
                result = self.client.post('/api/chat', json={'message':question}).json()
                self.assertEqual(result['route'], 'graduation_item_unavailable')
                self.assertIn(item, result['answer'])
                tool.assert_not_called()
        result = self.client.post('/api/chat', json={'message':'내 영어 점수와 남은 졸업학점 알려줘'}).json()
        self.assertEqual(result['route'], 'graduation')
        self.assertIn('남은 총 학점: 27학점', result['answer'])
        self.assertIn('TOEIC', result['answer'])
        self.assertNotIn('미이수 과목', result['answer'])
        result = self.client.post('/api/chat', json={'message':'내 교양과 전공필수 얼마나 남았어?'}).json()
        self.assertEqual(result['route'], 'graduation')
        self.assertIn('교양 세부요건', result['answer'])
        self.assertIn('전공필수', result['answer'])
        self.assertNotIn('TOEIC', result['answer'])
        with patch('app.chat.search', return_value=[]), patch('app.chat.crawl_academic_notices', return_value=[]), patch('app.chat.invoke_student_tool') as tool:
            result = self.client.post('/api/chat', json={'message':'졸업필수 과목 알려줘'}).json()
            self.assertEqual(result['route'], 'not_found')
            tool.assert_not_called()

    def test_remaining_graduation_question_uses_personal_comparison(self):
        questions = ('졸업을 하기 위해서 남은게 뭐가 있어?', '졸업하려면 뭐가 부족해?', '졸업을 위해 아직 필요한 것은?')
        for question in questions:
            with self.subTest(guest=question), patch('app.chat.search') as search:
                result = self.client.post('/api/chat', json={'message':question}).json()
                self.assertEqual(result['route'], 'login')
                search.assert_not_called()
        self.login(self.client)
        for question in questions:
            with self.subTest(student=question), patch('app.chat.search') as search:
                result = self.client.post('/api/chat', json={'message':question}).json()
                self.assertEqual(result['route'], 'graduation')
                self.assertIn('남은 총 학점: 27학점', result['answer'])
                self.assertIn('관리회계', result['answer'])
                self.assertIn('750 / 800점', result['answer'])
                search.assert_not_called()
        with patch('app.chat.search', return_value=[]), patch('app.chat.crawl_academic_notices', return_value=[]), patch('app.chat.invoke_student_tool') as tool:
            result = self.client.post('/api/chat', json={'message':'조기졸업 신청 서류 남은 일정 알려줘'}).json()
            self.assertEqual(result['route'], 'not_found')
            tool.assert_not_called()

    def test_real_http_tool_call_and_student_isolation(self):
        self.login(self.client)
        result = self.client.post("/api/chat", json={"message":"내 졸업요건 확인해줘"}).json()
        self.assertEqual(result["route"], "graduation")
        self.assertIn("99 / 126학점", result["answer"])
        self.assertIn("27학점", result["answer"])
        self.assertIn("전공기초: 12 / 12학점 (남은 0학점)", result["answer"])
        self.assertIn("전공필수: 18 / 27학점 (남은 9학점)", result["answer"])
        self.assertIn("관리회계", result["answer"])
        self.assertNotIn("영어 성적 충족", result["answer"])
        request = PickleStub.calls[-1]
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertTrue(request["body"]["tools"])
        self.assertNotIn("김민준", json.dumps(request["body"], ensure_ascii=False))
        self.assertNotIn("99", json.dumps(request["body"], ensure_ascii=False))

        other = TestClient(app)
        self.login(other, "student2")
        second = other.post("/api/chat", json={"message":"내 이수 과목과 학점 알려줘"}).json()
        self.assertEqual(second["route"], "student_query")
        self.assertIn("이서연", second["answer"])
        self.assertNotIn("김민준", second["answer"])
        self.assertIn("3", second["answer"])

    def test_public_search_then_fallback_and_failure(self):
        with patch("app.chat.search", return_value=[]), patch("app.chat.crawl_academic_notices", return_value=[{"title":"휴학 안내","text":"휴학 절차를 확인합니다.","source":"학교 공지","url":"https://biz.pusan.ac.kr/bbs/biz/1091/1/artclView.do","period":"crawled"}]) as crawl, patch("app.chat.score_candidates", side_effect=lambda q,d:d):
            result = self.client.post("/api/chat", json={"message":"휴학 절차 알려줘"}).json()
            self.assertEqual(result["route"], "crawl")
            crawl.assert_called_once()
        with patch("app.chat.search", return_value=[]), patch("app.chat.crawl_academic_notices", return_value=[]):
            result = self.client.post("/api/chat", json={"message":"휴학 절차 알려줘"}).json()
            self.assertEqual(result["route"], "not_found")
            self.assertEqual(result["sources"], [])

    def test_unrelated_and_cross_student(self):
        self.login(self.client)
        res = self.client.post("/api/chat", json={"message":"다른 학생 성적 알려줘"}).json()
        self.assertEqual(res["route"], "denied")
        with patch("app.chat.search") as search, patch("app.chat.general_response", return_value={"answer":"일반 대화 응답", "sources":[], "route":"general_chat"}) as general:
            res = self.client.post("/api/chat", json={"message":"양자물리 역사를 알려줘"}).json()
            self.assertEqual(res["route"], "general_chat")
            general.assert_called_once_with("양자물리 역사를 알려줘")
            search.assert_not_called()

    def test_greeting_and_general_chat_failure(self):
        with patch("app.chat.general_response") as general:
            result = self.client.post("/api/chat", json={"message":"안녕"}).json()
            self.assertEqual(result["route"], "greeting")
            self.assertIn("안녕하세요", result["answer"])
            general.assert_not_called()
        with patch("app.chat.general_response", side_effect=RuntimeError("offline")):
            result = self.client.post("/api/chat", json={"message":"오늘 기분이 좋아"}).json()
            self.assertEqual(result["route"], "chat_unavailable")
            self.assertIn("연결하지 못했습니다", result["answer"])

    def test_general_chat_uses_http_model_without_academic_search(self):
        with patch("app.chat.search") as search:
            result = self.client.post("/api/chat", json={"message":"기분 전환 방법을 알려줘"}).json()
            self.assertEqual(result["route"], "general_chat")
            self.assertEqual(result["answer"], "일반 대화 응답입니다.")
            search.assert_not_called()
        request = PickleStub.calls[-1]
        self.assertEqual(request["path"], "/v1/chat/completions")
        self.assertEqual(request["body"]["messages"][-1]["content"], "기분 전환 방법을 알려줘")

    def test_general_web_tool_results_and_failure(self):
        from langchain_core.messages import AIMessage
        from app.chat import general_response
        call = AIMessage(content='', tool_calls=[{'name': 'public_web_search', 'args': {'query': '부산대학교 경영학과 공지'}, 'id': 'call_web', 'type': 'tool_call'}])
        class Model:
            def bind_tools(self, *args, **kwargs):
                return self
            def invoke(self, messages):
                return call if isinstance(messages[-1], tuple) else AIMessage(content='검색 결과입니다.')
        results = [{'title':'공식 공지', 'url':'https://biz.pusan.ac.kr/', 'snippet':'안내 내용'}]
        with patch('app.chat.tool_model', return_value=Model()), patch('app.chat.search_web', return_value=results):
            result = general_response('경영학과 공지 알려줘')
            self.assertEqual(result['route'], 'web_search')
            self.assertEqual(result['sources'][0]['url'], results[0]['url'])
            fresh = general_response('오늘 경영학과 공지 알려줘')
            self.assertIn('게시일이나 현재 상태를 확인할 수 없으므로', fresh['answer'])
            self.assertIn('안내 내용', fresh['answer'])
        with patch('app.chat.tool_model', return_value=Model()), patch('app.chat.search_web', side_effect=OSError('offline')):
            result = general_response('오늘 경영학과 공지 알려줘')
            self.assertEqual(result['route'], 'web_search_unavailable')
            self.assertEqual(result['sources'], [])

    def test_recent_department_notice_requires_web_search(self):
        with patch('app.chat.general_response', return_value={'answer':'검색 결과', 'sources':[], 'route':'web_search'}) as general, patch('app.chat.search') as vector:
            result = self.client.post('/api/chat', json={'message':'오늘자 경영학과 공지 알려줘'}).json()
            self.assertEqual(result['route'], 'web_search')
            general.assert_called_once_with('오늘자 경영학과 공지 알려줘', force_search=True)
            vector.assert_not_called()

    def test_weather_asks_for_location_then_uses_web(self):
        with patch('app.chat.general_response') as general:
            result = self.client.post('/api/chat', json={'message':'오늘 날씨 알려줘'}).json()
            self.assertEqual(result['route'], 'weather_location_required')
            self.assertIn('어느 지역', result['answer'])
            general.assert_not_called()
        with patch('app.chat.general_response', return_value={'answer':'검색 결과', 'sources':[], 'route':'web_search'}) as general:
            result = self.client.post('/api/chat', json={'message':'오늘 날씨 알려줘 부산'}).json()
            self.assertEqual(result['route'], 'web_search')
            general.assert_called_once_with('오늘 날씨 알려줘 부산', force_search=True)

    def test_academic_aliases_and_specific_course_names(self):
        from app.retrieval import academic_query
        self.assertTrue(academic_query("경영통계학 1학년 분반은?"))
        self.assertTrue(safe_match("경영통계학 1학년 분반은?", {"title":"수강 안내 / 경영통계학·회계학원리", "text":"", "topic":""}))
        self.assertFalse(safe_match("경영통계학 1학년 분반은?", {"title":"수강 안내 / 휴학 기간", "text":"", "topic":""}))
        self.assertTrue(safe_match("전공필수 과목은 무엇인가요?", {"title":"경영학과 졸업학점과 전공 필수과목 공통 데모 기준", "text":"", "topic":"졸업"}))
        self.assertTrue(safe_match("전공 필수 과목은 무엇인가요?", {"title":"경영학과 졸업학점과 전공 필수과목 공통 데모 기준", "text":"", "topic":"졸업"}))

    def test_relevance_rejects_incidental_keywords(self):
        from app.retrieval import primary_topic
        from app.chat import personal_intent
        self.assertEqual(primary_topic('휴학 사유가 끝나면 어떻게 해야 하나요?'), '복학')
        self.assertEqual(primary_topic('전과하려면 1학년 수료가 필요한가요?'), '전과')
        self.assertIsNone(personal_intent('성적평점평균이 어느 정도면 졸업할 수 있나요?'))
        query = "경영학과 졸업학점은 몇 학점인가요?"
        self.assertFalse(safe_match(query, {"period":"general", "topic":"장학", "title":"장학금 일반 안내", "text":"이수학점 기준"}))
        self.assertTrue(safe_match(query, {"period":"general", "topic":"졸업", "title":"수료학점", "text":"졸업 기준"}))
        self.assertFalse(safe_match(query, {"period":"general", "topic":"졸업", "title":"졸업 본사정 안내", "text":"학점 확인"}))
        self.assertFalse(safe_match("휴학 절차 알려줘", {"period":"general", "topic":"복학", "title":"복학 안내", "text":"휴학 기간이 끝난 학생"}))
        self.assertTrue(safe_match("졸업 안내", {"period":"2026-08", "topic":"졸업", "title":"졸업 안내", "text":"예시"}))
        self.assertFalse(safe_match('경영학과 전공기초 필수과목 목록', {'topic':'졸업', 'title':'학사과정 수료학점', 'text':'경영학과 졸업 총 126학점'}))
        self.assertTrue(safe_match('경영학과 전공기초 필수과목 목록', {'topic':'졸업', 'title':'공통 데모 기준', 'text':'전공기초 경영학원론'}))

    def test_same_graduation_rule_independent_of_curriculum(self):
        with database.connect() as db:
            db.execute("UPDATE students SET curriculum=? WHERE id=2", ("다른 연도 예시",))
        try:
            result = database.graduation(2)
            self.assertEqual(result["curriculum"], "공통 데모 기준")
            self.assertEqual(result["required_credits"], 126)
        finally:
            with database.connect() as db:
                db.execute("UPDATE students SET curriculum=? WHERE id=2", ("2021",))

    def test_no_conflicting_cohort_credit_tables_are_indexed(self):
        docs = documents()
        self.assertTrue(any(d["id"] == "biz-major-2021" and "126학점" in d["text"] for d in docs))
        self.assertFalse(any("2011학년도 교육과정 (2011~2012학번)" in d["text"] for d in docs))

    def test_spider_starts_and_rejects_external_links(self):
        spider = AcademicSpider(topic="수강")
        async def collect():
            return [request async for request in spider.start()]
        requests = asyncio.run(collect())
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].url, "https://biz.pusan.ac.kr/biz/8941/subview.do")
        html = '<a href="/bbs/biz/1091/123/artclView.do">수강 안내</a><a href="https://evil.example/bbs/biz/1091/456/artclView.do">수강 안내</a>'
        response = HtmlResponse(url=requests[0].url, body=html.encode(), encoding="utf-8", request=Request(requests[0].url))
        parsed = list(spider.parse(response))
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0].url, "https://biz.pusan.ac.kr/bbs/biz/1091/123/artclView.do")

    def test_invalid_login_logout_and_origin(self):
        self.assertEqual(self.client.post("/api/login", json={"username":"student","password":"wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/api/login", json={"username":"student","password":"demo1234"}, headers={"Origin":"https://evil.example"}).status_code, 403)
        self.login(self.client)
        self.client.post("/api/logout", json={})
        self.assertTrue(self.client.post("/api/chat", json={"message":"내 학점 알려줘"}).json()["login_required"])


if __name__ == "__main__":
    unittest.main()
