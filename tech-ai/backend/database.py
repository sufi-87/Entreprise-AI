import os
import json
from contextlib import contextmanager

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/tech_ai')

try:
    import psycopg
    from psycopg.rows import dict_row
    from pgvector.psycopg import register_vector
    PSYCOPG_AVAILABLE = True
except Exception:
    psycopg = None
    dict_row = None
    register_vector = None
    PSYCOPG_AVAILABLE = False

_DB_READY = False
_DB_DISABLED_REASON = None


def is_db_enabled() -> bool:
    return PSYCOPG_AVAILABLE


@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    register_vector(conn)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    global _DB_READY, _DB_DISABLED_REASON
    if _DB_READY or not PSYCOPG_AVAILABLE:
        if not PSYCOPG_AVAILABLE:
            _DB_DISABLED_REASON = 'psycopg/pgvector not installed'
        return
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id BIGSERIAL PRIMARY KEY,
                        plant TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        filetype TEXT,
                        file_path TEXT NOT NULL,
                        size_bytes BIGINT DEFAULT 0,
                        upload_date BIGINT NOT NULL,
                        UNIQUE(plant, filename)
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS chunks (
                        id BIGSERIAL PRIMARY KEY,
                        chunk_id TEXT NOT NULL,
                        plant TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        filetype TEXT,
                        text TEXT NOT NULL,
                        source_type TEXT DEFAULT 'text',
                        page_num INTEGER,
                        extra JSONB DEFAULT '{}'::jsonb,
                        embedding vector(384),
                        UNIQUE(chunk_id, plant)
                    );
                ''')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_chunks_plant_filename ON chunks(plant, filename);')
                cur.execute('CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        id BIGSERIAL PRIMARY KEY,
                        timestamp BIGINT NOT NULL,
                        plant TEXT,
                        filename TEXT,
                        action TEXT,
                        status TEXT,
                        latency_ms INTEGER DEFAULT 0
                    );
                ''')
        _DB_READY = True
        _DB_DISABLED_REASON = None
    except Exception as e:
        _DB_DISABLED_REASON = str(e)


def get_db_status():
    init_db()
    return {'enabled': PSYCOPG_AVAILABLE and _DB_READY, 'reason': _DB_DISABLED_REASON, 'url': DATABASE_URL}


def upsert_document(plant, filename, filetype, file_path, size_bytes, upload_date):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('''
            INSERT INTO documents(plant, filename, filetype, file_path, size_bytes, upload_date)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (plant, filename) DO UPDATE SET
                filetype = EXCLUDED.filetype,
                file_path = EXCLUDED.file_path,
                size_bytes = EXCLUDED.size_bytes,
                upload_date = EXCLUDED.upload_date;
        ''', (plant, filename, filetype, file_path, size_bytes, upload_date))


def list_documents(plant=None):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        if plant:
            cur.execute('SELECT plant, filename, filetype, size_bytes, upload_date, file_path FROM documents WHERE plant=%s ORDER BY upload_date DESC', (plant,))
        else:
            cur.execute('SELECT plant, filename, filetype, size_bytes, upload_date, file_path FROM documents ORDER BY upload_date DESC')
        rows = cur.fetchall()
    docs = []
    for r in rows:
        docs.append({
            'plant': r['plant'],
            'filename': r['filename'],
            'type': (r.get('filetype') or '').upper(),
            'size_bytes': r['size_bytes'],
            'upload_date': r['upload_date'],
            'file_path': r['file_path'],
        })
    return docs


def delete_document_record(plant, filename):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('DELETE FROM documents WHERE plant=%s AND filename=%s', (plant, filename))
        cur.execute('DELETE FROM chunks WHERE plant=%s AND filename=%s', (plant, filename))


def insert_chunks(chunks):
    init_db()
    if not chunks:
        return
    with get_conn() as conn, conn.cursor() as cur:
        for c in chunks:
            emb = c.get('embedding')
            cur.execute('''
                INSERT INTO chunks(chunk_id, plant, filename, filetype, text, source_type, page_num, extra, embedding)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (chunk_id, plant) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    filetype = EXCLUDED.filetype,
                    text = EXCLUDED.text,
                    source_type = EXCLUDED.source_type,
                    page_num = EXCLUDED.page_num,
                    extra = EXCLUDED.extra,
                    embedding = EXCLUDED.embedding;
            ''', (
                c['chunk_id'], c['plant'], c['filename'], c.get('filetype'), c['text'], c.get('source_type', 'text'), c.get('page_num'), json.dumps(c.get('extra') or {}), emb
            ))


def fetch_chunks_for_plant(plant):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT chunk_id, plant, filename, filetype, text, source_type, page_num, extra FROM chunks WHERE plant=%s ORDER BY id', (plant,))
        return cur.fetchall()


def search_chunks_by_vector(plants, embedding, top_k=6):
    init_db()
    if not plants:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('''
            SELECT chunk_id, plant, filename, filetype, text, source_type, page_num, extra,
                   1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE plant = ANY(%s) AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        ''', (embedding, plants, embedding, top_k))
        return cur.fetchall()


def count_documents():
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS c FROM documents')
        return cur.fetchone()['c']


def count_chunks():
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT COUNT(*) AS c FROM chunks')
        return cur.fetchone()['c']


def stats_by_plant():
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT plant, COUNT(*) AS c FROM documents GROUP BY plant')
        rows = cur.fetchall()
    return {r['plant']: r['c'] for r in rows}


def append_log_db(log_entry):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('INSERT INTO logs(timestamp, plant, filename, action, status, latency_ms) VALUES (%s,%s,%s,%s,%s,%s)',
                    (log_entry['timestamp'], log_entry['plant'], log_entry['filename'], log_entry['action'], log_entry['status'], log_entry['latency_ms']))


def get_logs_db(limit=100):
    init_db()
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT timestamp, plant, filename, action, status, latency_ms FROM logs ORDER BY timestamp DESC LIMIT %s', (limit,))
        return cur.fetchall()
