import sqlite3
import os
import time
from datetime import datetime, timedelta, timezone
import traceback

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')

RESERVATION_MINUTES = 0.2
PENALTY_HOURS = 0.01


def get_db():
    db = sqlite3.connect(DB_PATH, timeout=1)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db


def autoExpireReservations():
    limit = (datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_MINUTES)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")

    session_user_id = None
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
            db.execute("UPDATE users SET penalty_score = penalty_score + 1, streak = 0 WHERE id = ?",
                       (reservation["user_id"],))
            lockAccount(reservation["user_id"], db)

        db.commit()
        if check:
            print(f"{len(check)} reservation(s) expired")
    except Exception:
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()


def lockAccount(user_id, db):
    row = db.execute("SELECT penalty_score FROM users WHERE id = ?",
                     (user_id,)).fetchone()
    if row is None:
        print("Problem occured while searching for user penalty_score")
        return None

    user_penalty_score = row["penalty_score"]
    if user_penalty_score > 1:
        # Compute the date until the user's account will be locked
        hours = PENALTY_HOURS * (user_penalty_score - 1)
        deadline_date = (datetime.now(timezone.utc) + timedelta(hours=hours)
                        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        db.execute("UPDATE users SET is_locked = 1, locked_deadline = ? WHERE id = ?",
                (deadline_date, user_id))
        db.commit()


def unlockUsersAccount():
    date_now = (datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db = get_db()

    try:
        db.execute(
            "UPDATE users SET is_locked = 0, locked_deadline = NULL "
            "WHERE is_locked = 1 AND locked_deadline <= ?",
            (date_now,),
        )
        db.commit()
    except Exception:
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

while True:
    try:
        autoExpireReservations()
        unlockUsersAccount()
    except Exception as e:
        print("worker error:", e)
    time.sleep(10)