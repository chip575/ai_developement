"""Run model-proposed SELECTs only against a private per-request snapshot."""
from __future__ import annotations

import re
import sqlite3
import time

import sqlglot
from sqlglot import exp

from . import database

SCHEMA = """SQLite 읽기 전용 테이블: student_profile(name TEXT, department TEXT, admission_year INTEGER, curriculum TEXT), course_records(course_code TEXT, name TEXT, category TEXT, academic_year INTEGER, semester INTEGER, grade TEXT, earned_credits REAL, status TEXT), recognized_courses(course_code TEXT, name TEXT, category TEXT, academic_year INTEGER, semester INTEGER, grade TEXT, earned_credits REAL, status TEXT), english_scores(exam_type TEXT, score INTEGER, taken_on TEXT, valid_until TEXT, approval_status TEXT).
모든 테이블에는 로그인한 한 학생의 데이터만 있습니다. 이 데모는 전공 과목만 포함하며 교양이나 부전공은 확인할 수 없습니다. 취득 학점 합계와 이수 완료 과목은 recognized_courses만 사용하세요. course_records는 미이수 및 재수강 기록도 포함합니다. 이수 상태의 정확한 값은 '이수'이며 '완료'가 아닙니다. category는 '전공기초', '전공필수', '전공선택'입니다. 영어 성적 approval_status는 'approved', 'pending', 'rejected'입니다. SQL의 문자열은 반드시 작은따옴표로 감싸세요. 성적 기록이나 미승인 영어 점수는 공식 졸업 판정이 아닙니다. student_profile에는 학번·학년·연락처가 없습니다. JOIN에는 student_id가 필요하지 않습니다. SQL은 SQLite SELECT 한 문장만 허용됩니다. SELECT, WHERE, GROUP BY, HAVING, ORDER BY, LIMIT 및 COUNT, SUM, AVG, MIN, MAX, ROUND, LOWER, UPPER, COALESCE를 사용할 수 있습니다. 알 수 없는 데이터나 공식 GPA는 추측하지 마세요."""
TABLES = {'student_profile', 'course_records', 'recognized_courses', 'english_scores'}
FUNCTIONS = {'count', 'sum', 'avg', 'min', 'max', 'round', 'lower', 'upper', 'coalesce', 'like'}
MAX_ROWS = 50


def sanitize_question(question: str, user: dict) -> str:
    if re.search(r'비밀번호|password|api[_ -]?key|주민등록', question, re.I):
        raise ValueError('비밀번호 등 민감한 정보는 질문에서 제외해 주세요.')
    question = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[이메일]', question)
    question = re.sub(r'(?<![A-Za-z0-9])(?:01[016789][- ]?\d{3,4}[- ]?\d{4}|\d{8,})(?!\d)', '[번호]', question)
    name = user.get('name')
    return question.replace(name, '[본인]') if name else question


def validate_sql(sql: str) -> str:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 3000:
        raise ValueError('SQL 길이 또는 내용이 올바르지 않습니다.')
    try:
        statements = sqlglot.parse(sql, read='sqlite')
    except Exception as exc:
        raise ValueError('SQL 구문을 확인할 수 없습니다.') from exc
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise ValueError('단일 SELECT 문만 허용됩니다.')
    tree = statements[0]
    if tree.args.get('with_') or any(isinstance(node, (exp.Union, exp.Intersect, exp.Except)) for node in tree.walk()):
        raise ValueError('CTE와 집합 연산은 현재 지원하지 않습니다.')
    tables = list(tree.find_all(exp.Table))
    if not tables or any(t.name.lower() not in TABLES or t.db or t.catalog for t in tables):
        raise ValueError('허용된 본인 조회 테이블만 사용할 수 있습니다.')
    # Execute the validated SQLGlot rendering, never the original unparsed text.
    return tree.sql(dialect='sqlite', comments=False)


def query_snapshot(user_id: int, sql: str) -> dict:
    normalized = validate_sql(sql)
    record = database.my_record(user_id)
    with database.connect() as db:
        scores = db.execute('SELECT exam_type,score,taken_on,valid_until,approval_status FROM student_english_scores WHERE student_id=? ORDER BY taken_on DESC LIMIT 5001', (user_id,)).fetchall()
    if len(record['records']) > 5000 or len(scores) > 5000:
        raise ValueError('조회할 기록이 너무 많습니다. 범위를 줄여 주세요.')
    conn = sqlite3.connect(':memory:')
    try:
        conn.executescript('''
        CREATE TABLE student_profile(name TEXT, department TEXT, admission_year INTEGER, curriculum TEXT);
        CREATE TABLE course_records(course_code TEXT, name TEXT, category TEXT, academic_year INTEGER, semester INTEGER, grade TEXT, earned_credits REAL, status TEXT);
        CREATE TABLE recognized_courses(course_code TEXT, name TEXT, category TEXT, academic_year INTEGER, semester INTEGER, grade TEXT, earned_credits REAL, status TEXT);
        CREATE TABLE english_scores(exam_type TEXT, score INTEGER, taken_on TEXT, valid_until TEXT, approval_status TEXT);
        ''')
        profile = record['student']
        conn.execute('INSERT INTO student_profile VALUES (?,?,?,?)', (profile['name'], profile['department'], profile['admission_year'], profile['curriculum']))
        keys = ('course_code', 'name', 'category', 'academic_year', 'semester', 'grade', 'earned_credits', 'status')
        for table, rows in (('course_records', record['records']), ('recognized_courses', record['recognized'])):
            conn.executemany(f'INSERT INTO {table} VALUES (?,?,?,?,?,?,?,?)', [tuple(row[k] for k in keys) for row in rows])
        conn.executemany('INSERT INTO english_scores VALUES (?,?,?,?,?)', [tuple(row[k] for k in ('exam_type','score','taken_on','valid_until','approval_status')) for row in scores])
        conn.execute('PRAGMA query_only=ON')

        def authorize(action, arg1, arg2, dbname, source):
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ and dbname == 'main' and arg1 in TABLES:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in FUNCTIONS:
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY

        conn.set_authorizer(authorize)
        start = time.monotonic()
        conn.set_progress_handler(lambda: int(time.monotonic() - start > 1.0), 1000)
        cursor = conn.execute(f'SELECT * FROM ({normalized}) LIMIT {MAX_ROWS + 1}')
        rows = cursor.fetchall()
        return {'sql': normalized, 'columns': [d[0] for d in cursor.description], 'rows': rows[:MAX_ROWS], 'truncated': len(rows) > MAX_ROWS}
    finally:
        conn.close()
