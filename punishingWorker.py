import sqlite3
import os
import time
from datetime import datetime, timedelta, timezone

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')

RESERVATION_MINUTES = 0.2


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=1)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def auto_expire_reservations():
    limit = (datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_MINUTES)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")

    db = get_db()
    try:
        check = db.execute("""
            SELECT id, compartment_id, created_at, user_id
            FROM reservations
            WHERE status = 'active' AND created_at <= ?
        """, (limit,)).fetchall()

        for reservation in check:
            db.execute("UPDATE reservations SET status = 'failed' WHERE id = ?",
                       (reservation["id"],))
            db.execute("UPDATE compartments SET status = 'empty' WHERE id = ?",
                       (reservation["compartment_id"],))
            db.execute("UPDATE users SET penalty_score = penalty_score + 1 WHERE id = ?",
                       (reservation["user_id"],))

        db.commit()
        lockAccount(reservation["user_id"], db)
        if check:
            print(f"{len(check)} reservation(s) expired")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def lockAccount(user_id, db):
    row = db.execute("SELECT penalty_score FROM users WHERE id = ?",
                     (user_id,)).fetchone()
    if row is None:
        print("Problem occured while seaking user penalty_score")
        return None

    user_penalty_score = row["penalty_score"]

    # Compute the date until the user's account will be locked
    hours = 24 * (user_penalty_score - 1)
    deadline_date = (datetime.now(timezone.utc) + timedelta(hours=hours)
                     ).strftime("%Y-%m-%dT%H:%M:%SZ")

    db.execute("UPDATE users SET is_locked = 1, locked_deadline = ? WHERE id = ?",
               (deadline_date, user_id))
    db.commit()






while True:
    try:
        auto_expire_reservations()
    except Exception as e:
        print("worker error:", e)
    time.sleep(10)