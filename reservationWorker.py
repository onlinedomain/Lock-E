import sqlite3
import os
import time
from datetime import datetime, timedelta, timezone

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')

RESERVATION_MINUTES = 30


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=10)  # attend si la base est verrouillée par Flask
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def expire_reservations():
    limit = (datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_MINUTES)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")

    db = get_db()
    try:
        check = db.execute("""
            SELECT id, compartment_id, created_at
            FROM reservations
            WHERE status = 'active' AND created_at <= ?
        """, (limit,)).fetchall()

        for reservation in check:
            db.execute("UPDATE reservations SET status = 'failed' WHERE id = ?",
                       (reservation["id"],))
            db.execute("UPDATE compartments SET status = 'empty' WHERE id = ?",
                       (reservation["compartment_id"],))

        db.commit()
        if check:
            print(f"{len(check)} reservation(s) expired")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


while True:
    try:
        expire_reservations()
    except Exception as e:
        print("worker error:", e)  # le worker ne s'arrête pas sur une erreur
    time.sleep(60)