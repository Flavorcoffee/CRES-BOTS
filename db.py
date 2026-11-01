import sqlite3
from contextlib import closing
import os

# Render Persistent Disk path
DB_PATH = "/data/beder.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    # Ensure the /data directory exists if running locally
    if os.path.dirname(DB_PATH):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    with closing(_connect()) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'applicant',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS loan_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_number TEXT UNIQUE,
            user_id INTEGER,
            bank_name TEXT,
            loan_amount REAL,
            prep_fee REAL,
            consultant_fee REAL,
            duration_months INTEGER,
            loan_type TEXT,
            status TEXT DEFAULT 'pending',
            lien_free INTEGER DEFAULT 0,
            insurance_agreed INTEGER DEFAULT 0,
            attachments_count INTEGER DEFAULT 0,
            accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS loan_documents (
            loan_id INTEGER,
            doc_name TEXT,
            is_provided INTEGER DEFAULT 0,
            PRIMARY KEY (loan_id, doc_name)
        );
        """)
        conn.commit()

def get_user(uid):
    with closing(_connect()) as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_id=?", (uid,)).fetchone()

def upsert_user(uid, username, full_name):
    with closing(_connect()) as conn:
        conn.execute(
            "INSERT INTO users (telegram_id, username, full_name) VALUES (?,?,?) "
            "ON CONFLICT(telegram_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name",
            (uid, username, full_name))
        conn.commit()
