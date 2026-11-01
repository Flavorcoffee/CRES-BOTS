import sqlite3
from contextlib import closing
import os
import json

DB_PATH = "beder.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
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
            data_json TEXT, 
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def save_full_loan(user_id, app_number, data_dict):
    with closing(_connect()) as conn:
        # Convert the dictionary of answers to a JSON string
        data_str = json.dumps(data_dict, ensure_ascii=False)
        conn.execute(
            "INSERT INTO loan_applications (user_id, app_number, data_json) VALUES (?, ?, ?)",
            (user_id, app_number, data_str)
        )
        conn.commit()
