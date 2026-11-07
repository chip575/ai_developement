"""Initialize a fresh demo database and empty search index before serving."""
import uvicorn

from .database import connect, init_db
from .index_docs import build_index
from .retrieval import collection
from .seed import seed


def main():
    init_db()
    with connect() as db:
        empty = not db.execute('SELECT 1 FROM students LIMIT 1').fetchone() and not db.execute('SELECT 1 FROM courses LIMIT 1').fetchone()
    if empty:
        seed()
    if collection().count() == 0:
        print(f'Indexed {build_index()} academic document chunks.', flush=True)
    uvicorn.run('app.main:app', host='0.0.0.0', port=8765)


if __name__ == '__main__':
    main()
