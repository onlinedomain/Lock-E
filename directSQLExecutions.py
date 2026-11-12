import os
import sqlite3

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db') 

db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')

db.execute("UPDATE users SET is_locked = 0, locked_deadline = NULL, penalty_score = 0 WHERE name = 'Marius'")

db.commit()
db.close()