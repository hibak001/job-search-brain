import sqlite3
from pathlib import Path

DB_PATH = Path("db/job_search_brain.sqlite3")
SCHEMA_PATH = Path("db/schema.sql")


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    with get_connection() as conn:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema)
        conn.commit()

from datetime import datetime


def add_document(doc_type: str, filename: str, file_path: str) -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO documents (doc_type, filename, file_path, uploaded_at)
            VALUES (?, ?, ?, ?)
            """,
            (doc_type, filename, file_path, now),
        )
        conn.commit()
        return cur.lastrowid


def list_resumes():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, filename, file_path, uploaded_at FROM documents WHERE doc_type='resume' ORDER BY id DESC"
        )
        rows = cur.fetchall()
    return rows

from datetime import datetime

def add_job(company: str, role: str, date_applied: str, status: str) -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO jobs (company, role, date_applied, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (company, role, date_applied, status, now),
        )
        conn.commit()
        return cur.lastrowid


def add_application(job_id: int, resume_document_id: int) -> int:
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO applications (job_id, resume_document_id)
            VALUES (?, ?)
            """,
            (job_id, resume_document_id),
        )
        conn.commit()
        return cur.lastrowid


def list_jobs():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, company, role, date_applied, status, created_at FROM jobs ORDER BY id DESC"
        )
        return cur.fetchall()


def get_resume_for_job(company: str, role: str):
    """
    Returns (resume_filename, resume_file_path) for the most recent matching job,
    or None if not found.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.filename, d.file_path
            FROM jobs j
            JOIN applications a ON a.job_id = j.id
            JOIN documents d ON d.id = a.resume_document_id
            WHERE LOWER(j.company) = LOWER(?)
              AND LOWER(j.role) = LOWER(?)
            ORDER BY j.id DESC
            LIMIT 1
            """,
            (company.strip(), role.strip()),
        )
        return cur.fetchone()
