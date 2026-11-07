import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.personal_sql import query_snapshot, sanitize_question, validate_sql
from app.seed import seed


class PersonalSqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.env = patch.dict(os.environ, {'ACADEMIC_DB_PATH':str(Path(cls.tmp.name) / 'personal-test.db')})
        cls.env.start()
        seed()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        cls.tmp.cleanup()

    def test_profile_course_filter_aggregate_and_student_isolation(self):
        first = query_snapshot(1, 'SELECT name, department, admission_year FROM student_profile')
        self.assertEqual(first['rows'][0], ('김민준', '경영학과', 2023))
        second = query_snapshot(2, 'SELECT name, department FROM student_profile')
        self.assertEqual(second['rows'][0][0], '이서연')
        hidden = query_snapshot(2, "SELECT name FROM student_profile WHERE name = '김민준'")
        self.assertEqual(hidden['rows'], [])
        courses = query_snapshot(1, "SELECT name FROM recognized_courses WHERE category = '전공필수'")
        self.assertEqual(len(courses['rows']), 6)
        self.assertEqual(query_snapshot(1, 'SELECT SUM(earned_credits) FROM recognized_courses')['rows'][0][0], 99)

    def test_rejects_writes_other_tables_and_unsafe_functions(self):
        for sql in ('DELETE FROM student_profile', 'PRAGMA table_list', 'SELECT * FROM accounts', 'SELECT * FROM main.student_profile', 'SELECT * FROM student_profile; DELETE FROM student_profile', 'SELECT * FROM student_profile UNION SELECT * FROM student_profile', 'WITH x AS (SELECT * FROM student_profile) SELECT * FROM x'):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_sql(sql)
        for sql in ("SELECT load_extension('x') FROM student_profile", 'SELECT sqlite_version() FROM student_profile'):
            with self.subTest(sql=sql), self.assertRaises(Exception):
                query_snapshot(1, sql)

    def test_redacts_obvious_identifiers_before_model(self):
        self.assertNotIn('김민준', sanitize_question('김민준의 기록', {'name':'김민준'}))
        self.assertNotIn('010-1234-5678', sanitize_question('내 전화번호 010-1234-5678', {}))
        with self.assertRaises(ValueError):
            sanitize_question('내 비밀번호 1234', {})


if __name__ == '__main__':
    unittest.main()
