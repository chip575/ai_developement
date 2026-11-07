"""Run the application tests in a disposable isolated PostgreSQL schema."""
import os
import subprocess
import sys
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg import sql


def main():
    url = os.environ.get('TEST_POSTGRES_URL')
    if not url:
        raise RuntimeError('TEST_POSTGRES_URL을 설정하세요.')
    schema = 'academic_test_' + uuid.uuid4().hex
    parsed = urlsplit(url)
    params = dict(parse_qsl(parsed.query))
    params['options'] = f'-csearch_path={schema}'
    test_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), parsed.fragment))
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        try:
            env = os.environ.copy()
            env['DATABASE_URL'] = test_url
            result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env=env, check=False)
        finally:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
