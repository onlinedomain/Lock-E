import os
import sqlite3

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db') 

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')


#%% Create the database architecture -----------------------------------

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
        locker_id INTEGER NOT NULL REFERENCES lockers(id),
        size      INTEGER NOT NULL CHECK (size IN (1, 2, 3)),
        status    TEXT NOT NULL DEFAULT 'empty' CHECK (status IN ('empty', 'full', 'reserved')),
        number    INTEGER NOT NULL
    );

    CREATE TABLE reservations (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL REFERENCES users(id),
        compartment_id INTEGER NOT NULL REFERENCES compartments(id),
        created_at     TEXT NOT NULL CHECK (created_at GLOB '????-??-??T??:??:??Z'),
        status         TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'failed', 'success')),
        code           INTEGER NOT NULL
    );

    CREATE UNIQUE INDEX one_active_per_compartment
    ON reservations(compartment_id) WHERE status = 'active';
''')
db.commit()


#%% Create some lockers and compartments in the database -----------------------------------

db.execute("""
INSERT INTO lockers (latitude, longitude, location_name, provider) VALUES
  (35.8528, 128.4905, 'Keimyung Univ. - Main Gate',            'pickup'),
  (35.8567, 128.4870, 'Keimyung Univ. - Engineering Hall',     'mondial_relay'),
  (35.8686, 128.5953, 'Dongseongno - Downtown',                'vinted_go'),
  (35.8760, 128.5960, 'Daegu Station',                         'mondial_relay'),
  (35.8645, 128.5940, 'Banwoldang Station',                    'pickup'),
  (35.8297, 128.5326, 'Dalseo-gu Office',                      'pickup'),
  (35.8280, 128.6150, 'Suseong Lake',                          'vinted_go'),
  (35.8590, 128.6300, 'Beomeo Station',                        'mondial_relay'),
  (35.8795, 128.6285, 'Dongdaegu Station',                     'pickup'),
  (35.8888, 128.6103, 'Kyungpook National Univ. - North Gate', 'vinted_go'),
  (35.9010, 128.5570, 'Chilgok - Shopping Center',             'mondial_relay'),
  (35.8570, 128.5650, 'Duryu Station',                         'vinted_go'),
  (35.8350, 128.5740, 'Daemyeong Station',                     'pickup');
""")
db.commit()

#%% Compartiments : (locker_id, size, status, number) ------------------------
# size : 1 = Small, 2 = Medium, 3 = Big
# Pour chaque locker : numéros 1-6 = Small, 7-12 = Medium, 13-16 = Big

db.execute("""
INSERT INTO compartments (locker_id, size, status, number) VALUES

  -- Locker 1 : Keimyung Main Gate (mixte)
  (1, 1, 'empty',    1),
  (1, 1, 'full',     2),
  (1, 1, 'empty',    3),
  (1, 1, 'reserved', 4),
  (1, 1, 'full',     5),
  (1, 1, 'empty',    6),
  (1, 2, 'empty',    7),
  (1, 2, 'full',     8),
  (1, 2, 'full',     9),
  (1, 2, 'empty',   10),
  (1, 2, 'reserved',11),
  (1, 2, 'full',    12),
  (1, 3, 'empty',   13),
  (1, 3, 'full',    14),
  (1, 3, 'reserved',15),
  (1, 3, 'empty',   16),

  -- Locker 2 : Keimyung Engineering Hall (presque plein)
  (2, 1, 'full',     1),
  (2, 1, 'full',     2),
  (2, 1, 'full',     3),
  (2, 1, 'empty',    4),
  (2, 1, 'full',     5),
  (2, 1, 'full',     6),
  (2, 2, 'full',     7),
  (2, 2, 'reserved', 8),
  (2, 2, 'full',     9),
  (2, 2, 'full',    10),
  (2, 2, 'full',    11),
  (2, 2, 'empty',   12),
  (2, 3, 'full',    13),
  (2, 3, 'full',    14),
  (2, 3, 'reserved',15),
  (2, 3, 'full',    16),

  -- Locker 3 : Dongseongno (beaucoup de places)
  (3, 1, 'empty',    1),
  (3, 1, 'empty',    2),
  (3, 1, 'empty',    3),
  (3, 1, 'full',     4),
  (3, 1, 'empty',    5),
  (3, 1, 'reserved', 6),
  (3, 2, 'empty',    7),
  (3, 2, 'empty',    8),
  (3, 2, 'full',     9),
  (3, 2, 'empty',   10),
  (3, 2, 'empty',   11),
  (3, 2, 'reserved',12),
  (3, 3, 'empty',   13),
  (3, 3, 'empty',   14),
  (3, 3, 'full',    15),
  (3, 3, 'empty',   16),

  -- Locker 4 : Daegu Station (PLEIN)
  (4, 1, 'full',     1),
  (4, 1, 'full',     2),
  (4, 1, 'full',     3),
  (4, 1, 'reserved', 4),
  (4, 1, 'full',     5),
  (4, 1, 'full',     6),
  (4, 2, 'full',     7),
  (4, 2, 'full',     8),
  (4, 2, 'reserved', 9),
  (4, 2, 'full',    10),
  (4, 2, 'full',    11),
  (4, 2, 'full',    12),
  (4, 3, 'full',    13),
  (4, 3, 'reserved',14),
  (4, 3, 'full',    15),
  (4, 3, 'full',    16),

  -- Locker 5 : Banwoldang Station (mixte)
  (5, 1, 'full',     1),
  (5, 1, 'empty',    2),
  (5, 1, 'full',     3),
  (5, 1, 'full',     4),
  (5, 1, 'empty',    5),
  (5, 1, 'reserved', 6),
  (5, 2, 'empty',    7),
  (5, 2, 'full',     8),
  (5, 2, 'reserved', 9),
  (5, 2, 'full',    10),
  (5, 2, 'full',    11),
  (5, 2, 'empty',   12),
  (5, 3, 'full',    13),
  (5, 3, 'reserved',14),
  (5, 3, 'full',    15),
  (5, 3, 'full',    16),

  -- Locker 6 : Dalseo-gu Office (beaucoup de places)
  (6, 1, 'empty',    1),
  (6, 1, 'empty',    2),
  (6, 1, 'empty',    3),
  (6, 1, 'empty',    4),
  (6, 1, 'full',     5),
  (6, 1, 'empty',    6),
  (6, 2, 'empty',    7),
  (6, 2, 'empty',    8),
  (6, 2, 'reserved', 9),
  (6, 2, 'empty',   10),
  (6, 2, 'full',    11),
  (6, 2, 'empty',   12),
  (6, 3, 'empty',   13),
  (6, 3, 'empty',   14),
  (6, 3, 'empty',   15),
  (6, 3, 'reserved',16),

  -- Locker 7 : Suseong Lake (mixte)
  (7, 1, 'empty',    1),
  (7, 1, 'full',     2),
  (7, 1, 'reserved', 3),
  (7, 1, 'full',     4),
  (7, 1, 'empty',    5),
  (7, 1, 'full',     6),
  (7, 2, 'full',     7),
  (7, 2, 'full',     8),
  (7, 2, 'empty',    9),
  (7, 2, 'reserved',10),
  (7, 2, 'full',    11),
  (7, 2, 'full',    12),
  (7, 3, 'reserved',13),
  (7, 3, 'empty',   14),
  (7, 3, 'full',    15),
  (7, 3, 'full',    16),

  -- Locker 8 : Beomeo Station (petits casiers pleins, grands libres)
  (8, 1, 'full',     1),
  (8, 1, 'full',     2),
  (8, 1, 'full',     3),
  (8, 1, 'full',     4),
  (8, 1, 'reserved', 5),
  (8, 1, 'full',     6),
  (8, 2, 'full',     7),
  (8, 2, 'reserved', 8),
  (8, 2, 'full',     9),
  (8, 2, 'empty',   10),
  (8, 2, 'full',    11),
  (8, 2, 'full',    12),
  (8, 3, 'empty',   13),
  (8, 3, 'empty',   14),
  (8, 3, 'empty',   15),
  (8, 3, 'full',    16),

  -- Locker 9 : Dongdaegu Station (PLEIN)
  (9, 1, 'full',     1),
  (9, 1, 'full',     2),
  (9, 1, 'reserved', 3),
  (9, 1, 'full',     4),
  (9, 1, 'full',     5),
  (9, 1, 'full',     6),
  (9, 2, 'full',     7),
  (9, 2, 'full',     8),
  (9, 2, 'full',     9),
  (9, 2, 'reserved',10),
  (9, 2, 'full',    11),
  (9, 2, 'full',    12),
  (9, 3, 'reserved',13),
  (9, 3, 'full',    14),
  (9, 3, 'full',    15),
  (9, 3, 'full',    16),

  -- Locker 10 : Kyungpook National Univ. (mixte)
  (10, 1, 'empty',    1),
  (10, 1, 'empty',    2),
  (10, 1, 'full',     3),
  (10, 1, 'full',     4),
  (10, 1, 'reserved', 5),
  (10, 1, 'empty',    6),
  (10, 2, 'full',     7),
  (10, 2, 'empty',    8),
  (10, 2, 'full',     9),
  (10, 2, 'full',    10),
  (10, 2, 'empty',   11),
  (10, 2, 'reserved',12),
  (10, 3, 'full',    13),
  (10, 3, 'empty',   14),
  (10, 3, 'full',    15),
  (10, 3, 'reserved',16),

  -- Locker 11 : Chilgok Shopping Center (beaucoup de places)
  (11, 1, 'empty',    1),
  (11, 1, 'empty',    2),
  (11, 1, 'empty',    3),
  (11, 1, 'reserved', 4),
  (11, 1, 'empty',    5),
  (11, 1, 'empty',    6),
  (11, 2, 'empty',    7),
  (11, 2, 'full',     8),
  (11, 2, 'empty',    9),
  (11, 2, 'empty',   10),
  (11, 2, 'empty',   11),
  (11, 2, 'full',    12),
  (11, 3, 'empty',   13),
  (11, 3, 'empty',   14),
  (11, 3, 'reserved',15),
  (11, 3, 'empty',   16),

  -- Locker 12 : Duryu Station (presque plein : 1 seul petit casier libre)
  (12, 1, 'full',     1),
  (12, 1, 'full',     2),
  (12, 1, 'empty',    3),
  (12, 1, 'full',     4),
  (12, 1, 'reserved', 5),
  (12, 1, 'full',     6),
  (12, 2, 'full',     7),
  (12, 2, 'full',     8),
  (12, 2, 'reserved', 9),
  (12, 2, 'full',    10),
  (12, 2, 'full',    11),
  (12, 2, 'full',    12),
  (12, 3, 'full',    13),
  (12, 3, 'reserved',14),
  (12, 3, 'full',    15),
  (12, 3, 'full',    16),

  -- Locker 13 : Daemyeong Station (PLEIN)
  (13, 1, 'full',     1),
  (13, 1, 'reserved', 2),
  (13, 1, 'full',     3),
  (13, 1, 'full',     4),
  (13, 1, 'full',     5),
  (13, 1, 'reserved', 6),
  (13, 2, 'full',     7),
  (13, 2, 'full',     8),
  (13, 2, 'full',     9),
  (13, 2, 'full',    10),
  (13, 2, 'reserved',11),
  (13, 2, 'full',    12),
  (13, 3, 'full',    13),
  (13, 3, 'full',    14),
  (13, 3, 'full',    15),
  (13, 3, 'reserved',16);
""")
db.commit()

db.close()
print("13 lockers et 208 compartiments insérés dans :", DB_PATH)
db.close()
print('Database created at :', DB_PATH)


















