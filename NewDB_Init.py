import os
import random
import sqlite3

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')

random.seed(42)  

PROVIDERS = ['mondial_relay', 'vinted_go', 'pickup']  

db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')

db.execute("DELETE FROM reservations")
db.execute("DELETE FROM compartments")
db.execute("DELETE FROM lockers")
db.execute("DELETE FROM sqlite_sequence WHERE name IN ('lockers', 'compartments', 'reservations')")






db.commit()
db.close()