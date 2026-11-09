import os
import sqlite3

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')

db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')

db.executescript('''
    CREATE TABLE users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        is_admin      INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
        name          TEXT NOT NULL,
        penalty_score INTEGER NOT NULL DEFAULT 0,
        streak        INTEGER NOT NULL DEFAULT 0,
        email         TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );
    
    CREATE TABLE lockers (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        latitude      REAL NOT NULL CHECK (latitude BETWEEN -90 AND 90),
        longitude     REAL NOT NULL CHECK (longitude BETWEEN -180 AND 180),
        location_name TEXT NOT NULL,
        provider      TEXT NOT NULL CHECK (provider IN ('mondial_relay', 'vinted_go', 'pickup'))
    );
    
    CREATE TABLE compartments (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        locker_id INTEGER NOT NULL REFERENCES locker(id),
        size      INTEGER NOT NULL CHECK (size IN (1, 2, 3)),
        status    TEXT NOT NULL DEFAULT 'empty' CHECK (status IN ('empty', 'full', 'reserved')),
        number    INTEGER NOT NULL
    );
    
    CREATE TABLE reservations (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        compartment_id INTEGER NOT NULL REFERENCES compartment(id),
        created_at     TEXT NOT NULL CHECK (expires_at GLOB '????-??-??T??:??:??Z'),
        status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'failed', 'success'))
    );     
        
    CREATE UNIQUE INDEX one_active_per_compartment
    ON reservations(compartment_id) WHERE status = 'active';
''')

db.commit()
db.close()
print('Database created at :', DB_PATH)






