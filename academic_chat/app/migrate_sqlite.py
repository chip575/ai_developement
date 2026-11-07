"""Copy the existing local SQLite demo into an empty PostgreSQL database once."""
import sqlite3
from pathlib import Path

from .config import db_path, setting
from .database import connect, init_db

TABLES = ('students', 'accounts', 'courses', 'graduation_rules', 'required_courses', 'english_requirements', 'course_records', 'student_english_scores')
IDENTITY_TABLES = ('students', 'accounts', 'course_records', 'student_english_scores')


def migrate():
    if not setting('DATABASE_URL'):
        raise RuntimeError('DATABASE_URL에 PostgreSQL 연결 주소를 지정하세요.')
    source = Path(db_path()).resolve()
    if not source.is_file():
        raise FileNotFoundError('기존 SQLite DB가 없습니다. 새 DB는 seed 명령을 사용하세요.')
    init_db()
    sqlite = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    sqlite.row_factory = sqlite3.Row
    try:
        with connect() as pg:
            for table in TABLES:
                if pg.execute(f'SELECT COUNT(*) AS n FROM {table}').fetchone()['n']:
                    raise RuntimeError('대상 PostgreSQL에 데이터가 있어 복사를 중단합니다. 기존 데이터를 덮어쓰지 않습니다.')
            for table in TABLES:
                rows = sqlite.execute(f'SELECT * FROM {table}').fetchall()
                if rows:
                    columns = rows[0].keys()
                    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
                    pg.executemany(sql, [tuple(row) for row in rows])
                print(f'{table}: {len(rows)} rows')
            for table in IDENTITY_TABLES:
                pg.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1), COUNT(*) > 0) FROM {table}")
        print('기존 로그인 세션은 복사하지 않았습니다. 다시 로그인하세요.')
    finally:
        sqlite.close()


if __name__ == '__main__':
    migrate()
