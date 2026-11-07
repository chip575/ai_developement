-- DataGrip: PostgreSQL localhost:55432 / academic_chat 데이터베이스를 선택합니다.
-- 예시 데이터만 들어 있으며 성적과 계정 정보는 실제 학생 자료가 아닙니다.

-- 데이터베이스 테이블 목록
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;

-- 과목 기준 (분반 중복 제거된 73개 과목)
SELECT code, name, category, credits, source_grade, source_semester
FROM courses
ORDER BY source_grade, source_semester, code;

-- 가상 학생의 이수 내역
SELECT s.name, c.code, c.name AS course_name, r.category, r.academic_year,
       r.semester, r.grade, r.earned_credits, r.status
FROM course_records r
JOIN students s ON s.id = r.student_id
JOIN courses c ON c.code = r.course_code
WHERE s.id = 1
ORDER BY r.academic_year, r.semester, c.code;

-- 교육과정별 필수과목
SELECT g.curriculum, g.total_credits, c.code, c.name, r.category
FROM required_courses r
JOIN graduation_rules g ON g.id = r.rule_id
JOIN courses c ON c.code = r.course_code
ORDER BY r.category, c.name;

-- 가상 학생의 영어 성적과 공통 데모 기준
SELECT s.name, e.exam_type, e.score, e.taken_on, e.valid_until, e.approval_status,
       r.minimum_score, r.source
FROM student_english_scores e
JOIN students s ON s.id = e.student_id
LEFT JOIN english_requirements r ON r.rule_id = 'business-2021-demo' AND r.exam_type = e.exam_type
ORDER BY s.id, e.taken_on DESC;
