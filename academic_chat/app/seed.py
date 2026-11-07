"""Import the supplied course catalog and create two fictional student accounts."""
import json
from pathlib import Path

import openpyxl

from .config import DATA
from .database import connect, hash_password, init_db

REQUIRED_CODES = [
    "DB1600346", "DB1600357", "DB1600351", "DB1600358",
    "DB3000711", "DB3000928", "DB3400701", "DB3000932", "DB3000933",
    "DB3000924", "DB3100231", "DB3000927", "DB3000934",
]
COMPLETED_CODES = REQUIRED_CODES[:10]
SOURCE = "경영학과 2026-2 수강제도 안내(사용자 제공 요약); 적용 교육과정 원문 확인 필요"


def seed():
    init_db()
    book = openpyxl.load_workbook(DATA / "sources" / "course_catalog.xlsx", data_only=True, read_only=True)
    sheet = book["SQL 통합데이터"]
    headers = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True))
    cols = {name: headers.index(name) for name in ("학년", "학기", "구분", "교과목 번호", "교과목명", "학점")}
    courses = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        code = row[cols["교과목 번호"]]
        if not code:
            continue
        item = (str(code).strip(), str(row[cols["교과목명"]]).strip(), row[cols["구분"]], row[cols["학점"]], row[cols["학년"]], row[cols["학기"]])
        if item[0] in courses and courses[item[0]] != item:
            raise ValueError(f"과목 정보 충돌: {item[0]}")
        courses[item[0]] = item
    missing = set(REQUIRED_CODES) - courses.keys()
    if missing:
        raise ValueError(f"필수 과목 누락: {sorted(missing)}")

    with connect() as db:
        db.executemany("INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?,?)", courses.values())
        db.execute("INSERT OR IGNORE INTO students VALUES (1,?,?,?,?)", ("김민준", "경영학과", 2023, "2021"))
        db.execute("INSERT OR IGNORE INTO students VALUES (2,?,?,?,?)", ("이서연", "경영학과", 2024, "2021"))
        for login_id, user_id in (("student", 1), ("student2", 2)):
            if not db.execute("SELECT 1 FROM accounts WHERE login_id=?", (login_id,)).fetchone():
                db.execute("INSERT INTO accounts(login_id,password_hash,student_id) VALUES (?,?,?)", (login_id, hash_password("demo1234"), user_id))
        db.execute("INSERT OR IGNORE INTO graduation_rules VALUES (?,?,?,?,?)", ("business-2021-demo", "경영학과", "2021", 126, SOURCE))
        db.execute("INSERT OR IGNORE INTO english_requirements(rule_id,exam_type,minimum_score,source) VALUES (?,?,?,?)", ("business-2021-demo", "TOEIC", 800, "사용자 제공 2026년 8월 졸업 공지의 2023학년도 신입학 TOEIC 기준을 모든 데모 학생에 적용"))
        db.executemany("INSERT OR IGNORE INTO student_english_scores(student_id,exam_type,score,taken_on,valid_until,approval_status) VALUES (?,?,?,?,?,?)", [(1, "TOEIC", 750, "2026-08-01", "2028-07-31", "approved"), (2, "TOEIC", 830, "2026-08-01", "2028-07-31", "approved")])
        for code in REQUIRED_CODES:
            db.execute("INSERT OR IGNORE INTO required_courses VALUES (?,?,?)", ("business-2021-demo", code, courses[code][2]))
        electives = [c[0] for c in courses.values() if c[2] == "전공선택"][:23]
        for idx, code in enumerate(COMPLETED_CODES + electives):
            c = courses[code]
            db.execute("INSERT OR IGNORE INTO course_records(student_id,course_code,academic_year,semester,category,grade,earned_credits,status) VALUES (?,?,?,?,?,?,?,?)", (1, code, 2023 + idx // 12, 1 + (idx // 6) % 2, c[2], "A0", c[3], "이수"))
        db.execute("INSERT OR IGNORE INTO course_records(student_id,course_code,academic_year,semester,category,grade,earned_credits,status) VALUES (?,?,?,?,?,?,?,?)", (2, "DB1600346", 2024, 1, "전공기초", "B0", 3, "이수"))
    print(json.dumps({"courses": len(courses), "fictional_students": 2, "fixture_student_credits": 99}, ensure_ascii=False))


if __name__ == "__main__":
    seed()
