import os
import random
import sqlite3

FOLDER = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')   # doit être le même nom que dans app.py
TXT_PATH = os.path.join(FOLDER, 'coordonnees_des_casiers.txt')

random.seed(42)

PROVIDERS = ['mondial_relay', 'vinted_go', 'pickup']
TOTAL_LOCKERS = 156
NB_FULL_LOCKERS = 2
SIZES = [1] * 7 + [2] * 8 + [3] * 5   # 20 compartiments : 7 S, 8 M, 5 B

# ville : (nombre de lockers à générer, [(quartier, latitude, longitude), ...])
CITIES = {
    "Daegu": (28, [
        ("Dongseongno", 35.8686, 128.5953), ("Daegu Station", 35.8760, 128.5960),
        ("Banwoldang", 35.8645, 128.5940), ("Suseong Lake", 35.8280, 128.6150),
        ("Kyungpook Natl Univ.", 35.8888, 128.6103), ("Dongdaegu Station", 35.8795, 128.6285),
        ("Duryu", 35.8570, 128.5650), ("Chilgok", 35.9010, 128.5570),
    ]),
    "Seoul": (40, [
        ("Gangnam", 37.4979, 127.0276), ("Hongdae", 37.5563, 126.9236),
        ("Myeongdong", 37.5636, 126.9822), ("Jamsil", 37.5133, 127.1002),
        ("Yeouido", 37.5219, 126.9245), ("Sinchon", 37.5598, 126.9425),
        ("Konkuk Univ.", 37.5404, 127.0793), ("Seoul Station", 37.5547, 126.9707),
        ("Itaewon", 37.5345, 126.9946), ("Nowon", 37.6554, 127.0614),
    ]),
    "Busan": (22, [
        ("Seomyeon", 35.1578, 129.0600), ("Haeundae", 35.1631, 129.1635),
        ("Nampo", 35.0970, 129.0297), ("Busan Station", 35.1150, 129.0403),
        ("Pusan Natl Univ.", 35.2342, 129.0794), ("Gwangalli", 35.1532, 129.1186),
    ]),
    "Incheon": (14, [
        ("Bupyeong", 37.4896, 126.7230), ("Songdo", 37.3820, 126.6570),
        ("Incheon Station", 37.4760, 126.6170), ("Guwol", 37.4490, 126.7010),
    ]),
    "Daejeon": (12, [
        ("Daejeon Station", 36.3326, 127.4342), ("Dunsan", 36.3510, 127.3850),
        ("KAIST", 36.3725, 127.3600), ("Yuseong", 36.3622, 127.3560),
    ]),
    "Gwangju": (10, [
        ("Chungjang-ro", 35.1495, 126.9170), ("Sangmu", 35.1530, 126.8490),
        ("Chonnam Natl Univ.", 35.1760, 126.9070),
    ]),
    "Suwon": (8, [
        ("Suwon Station", 37.2660, 127.0000), ("Gwanggyo", 37.2890, 127.0510),
        ("Ajou Univ.", 37.2830, 127.0440),
    ]),
    "Ulsan": (6, [
        ("Samsan", 35.5400, 129.3340), ("Ulsan Univ.", 35.5430, 129.2560),
    ]),
    "Seongnam": (4, [
        ("Pangyo", 37.3947, 127.1112), ("Seongnam Station", 37.4380, 127.1370),
    ]),
    "Jeju": (4, [
        ("Jeju City Hall", 33.4996, 126.5312), ("Seogwipo", 33.2541, 126.5600),
    ]),
}

db = sqlite3.connect(DB_PATH)
db.execute('PRAGMA foreign_keys = ON')

db.execute("DELETE FROM reservations")
db.execute("DELETE FROM compartments")
db.execute("DELETE FROM lockers")
db.execute("DELETE FROM sqlite_sequence WHERE name IN ('lockers', 'compartments', 'reservations')")

lockers = []

# ---------- 1. Lockers du fichier texte (format : Longitude, Latitude, Nom) ----------
with open(TXT_PATH, encoding="utf-8") as f:
    next(f)  # ligne d'en-tête
    for line in f:
        if not line.strip():
            continue
        lng, lat, name = [part.strip() for part in line.split(",", 2)]
        lockers.append((float(lat), float(lng), name, random.choice(PROVIDERS)))

nb_from_file = len(lockers)

# ---------- 2. Lockers générés ----------
for city, (count, spots) in CITIES.items():
    for i in range(count):
        area, lat, lng = spots[i % len(spots)]
        lat += random.uniform(-0.006, 0.006)
        lng += random.uniform(-0.006, 0.006)
        name = f"{city} - {area} ({i // len(spots) + 1})"
        lockers.append((round(lat, 6), round(lng, 6), name, random.choice(PROVIDERS)))

assert len(lockers) == TOTAL_LOCKERS, f"{len(lockers)} lockers au lieu de {TOTAL_LOCKERS}"

db.executemany(
    "INSERT INTO lockers (latitude, longitude, location_name, provider) VALUES (?,?,?,?)",
    lockers,
)

# ---------- 3. Compartiments ----------
locker_ids = [r[0] for r in db.execute("SELECT id FROM lockers ORDER BY id")]
full_lockers = set(random.sample(locker_ids, NB_FULL_LOCKERS))   # ces lockers n'ont plus rien de libre

compartments = []
for locker_id in locker_ids:
    statuses = [random.choice(['empty', 'full']) for _ in SIZES]

    if locker_id in full_lockers:
        statuses = ['full'] * len(SIZES)
    elif 'empty' not in statuses:
        statuses[random.randrange(len(SIZES))] = 'empty'   # garantit qu'il n'y a que 2 lockers pleins

    for number, (size, status) in enumerate(zip(SIZES, statuses), start=1):
        compartments.append((locker_id, size, status, number))

db.executemany(
    "INSERT INTO compartments (locker_id, size, status, number) VALUES (?,?,?,?)",
    compartments,
)

db.commit()
db.close()
print(f"{nb_from_file} lockers du fichier + {TOTAL_LOCKERS - nb_from_file} générés = {TOTAL_LOCKERS}")
print(f"{len(compartments)} compartiments. Lockers pleins (ids) : {sorted(full_lockers)}")