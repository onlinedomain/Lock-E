import os
import sqlite3
from random import randint
from math import radians, sin, cos, asin, sqrt
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, jsonify, request, redirect, render_template, session, abort
import traceback # Traceback gives more detailed error messages with database difficulties

RESERVATION_MINUTES = 0.2 # (DEFAULT 30) Time before reservation expiration. Has to be the same than in the Worker.py
PENALTY_HOURS = 0.01 # (DEFAULT 24) Time used in the formula (PENALTY_HOURS * (penalty_score - 1)) to compute user penalty time

#%% ///////////////////////// Flask server configuration ////////////////////////
app = Flask(__name__, static_folder='static', template_folder='Templates', static_url_path='')

app.secret_key = "to modify before publishing and put it in an env variable" # Key to create cookies for users sessions

app.config.update(SESSION_COOKIE_SAMESITE="lax") # CSRF protection (BONUS)



#%% /////////////////////////////////////////////////////////////////////////////
#%% /////////////// Basic functions used everywhere in the code /////////////////
#%% /////////////////////////////////////////////////////////////////////////////
def get_db():
    FOLDER = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(FOLDER, 'lock_e_database.db')
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def is_admin_user():
    user_id = session.get("user_id")
    if not user_id:
        return False
    db = get_db()
    user = db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return bool(user and user["is_admin"])

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))



#%% /////////////////////////////////////////////////////////////////////////////
#%% ///////////////////////////// Main page route ///////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////
@app.route('/')
def default():

    if session.get("user_id"):
        
        if is_admin_user() :
            return render_template("index.html")
    
        return render_template("index.html")
    
    return render_template("new_user.html")



#%% /////////////////////////////////////////////////////////////////////////////
#%% //////////////////////// Account related routes /////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////
@app.route("/register", methods=["GET", "POST"])
def register():
    
    """
    This route can receive 2 requests :
        
        GET :
            If the user is already loged-in,
                redirects to the main view
            If not, displays the register page
        
        POST :
            Insert username, email and hashed password into the 
            database and gives a cookie to the user's browser to
            keep him loged-in for the next requests
            
            If email is already in the database, display an error 
            message on the page and ask for different inputs
    """
    
    if request.method == "POST":
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        
        db = get_db()
        try:
            db.execute("""INSERT INTO users (name, email, password_hash) 
                       VALUES (?,?,?)""", (username, email, generate_password_hash(password)))
            db.commit()
            session["user_id"] = db.execute("""SELECT id
                                               FROM users 
                                               WHERE email = ?""", (email,)).fetchone()['id']
            # We could also use here : session["user_id"] = cursor.lastrowid
            db.close()
            
            return redirect('/')
        
        except sqlite3.IntegrityError:
            db.close()
            return render_template("register.html", error="This email is already used", 
                                   user=username)
        
        finally:
            db.close()  
        
    if session.get("user_id"):
        return redirect('/')
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    
    """
    This route can receive 2 requests :
        
        GET :
            If the user is already loged-in,
                redirects to the main view
            If not, displays the login page
        
        POST :
            Verify username and password, if user exists and password
            is right : logs the user in and gives the browser a cookie
            
            If username or password is incorrect, displays an error message 
            and ask for different inputs
    """
    
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect('/')

        return render_template("login.html", error="Incorrect email or password.", email=email)

    if session.get("user_id"):
        return redirect('/')
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")



#%% /////////////////////////////////////////////////////////////////////////////
#%% /////////////////////////////// Locker view /////////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////
@app.route("/locker/<int:locker_id>")
def locker_page(locker_id):
    if not session.get("user_id"):
        return redirect("/login")

    db = get_db()
    try:
        locker = db.execute(
            "SELECT * FROM lockers WHERE id = ?", (locker_id,)
        ).fetchone()
        if locker is None:
            abort(404)

        rows = db.execute(
            "SELECT size, COUNT(*) AS n FROM compartments "
            "WHERE locker_id = ? AND status = 'empty' GROUP BY size",
            (locker_id,),
        ).fetchall()
    finally:
        db.close()

    free = {1: 0, 2: 0, 3: 0}
    for r in rows:
        free[r["size"]] = r["n"]

    return render_template("locker.html", locker=locker, free=free)



#%% /////////////////////////////////////////////////////////////////////////////
#%% ////////////////////////// Secondary functions //////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////
def checkReservationAvailability(locker_id, size, user_id):
    db = get_db()
    unlockUsersAccount()

    try:
        # Checks if the user has an active penalty
        user_locked = db.execute("SELECT is_locked FROM users WHERE id = ?",
                                 (session.get("user_id"),)).fetchone()["is_locked"]
        if user_locked : return [False,False]

        # Checks if the compartment is still available in case someone reserved it at the same time
        compartment_available = db.execute("""SELECT c.id 
                                    FROM compartments c 
                                    WHERE c.locker_id = ? AND c.size = ? AND c.status = 'empty' """,
                                    (locker_id, size)).fetchone()
        
        # Checks if the user already has an actve reservation
        active_reservation = db.execute("""SELECT * FROM reservations WHERE user_id = ? AND status='active' """, 
                                       (user_id,)).fetchone()

    finally:
        db.close()
    
    if compartment_available and not active_reservation:
        return [compartment_available["id"], False]
    return [False, active_reservation]

def getAccountUnlockedDate(user_id):
    db = get_db()
    try:
        deadline_date = db.execute(
            "SELECT locked_deadline FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        db.close()

    if deadline_date is None or deadline_date["locked_deadline"] is None:
        return None

    deadline = datetime.strptime(deadline_date["locked_deadline"], "%Y-%m-%dT%H:%M:%SZ")
    return deadline.strftime("%H:%M, %Y/%m/%d")

def autoExpireReservations():
    limit = (datetime.now(timezone.utc) - timedelta(minutes=RESERVATION_MINUTES)
             ).strftime("%Y-%m-%dT%H:%M:%SZ")

    db = get_db()
    try:
        check = db.execute("""
            SELECT id, compartment_id, user_id
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


#%% /////////////////////////////////////////////////////////////////////////////
#%% /////////////////////// Reservation related routes //////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////
@app.route("/cancel-reservations") 
def cancel_reservations():
    if not session.get("user_id"):
        return jsonify(error="unauthorized"), 401

    try:
        autoExpireReservations()
    except Exception:
        traceback.print_exc()
        return jsonify(error="could not expire reservations"), 500

    return jsonify(ok=True)

@app.route("/simulate-deposit")
def simulateDeposit():
    if not session.get("user_id"):
        return render_template("errors/401.html"), 401
    
    db = get_db()
    reservation = db.execute("SELECT id, compartment_id FROM reservations WHERE status = 'active' AND user_id = ?",
                             (session["user_id"],)).fetchone()
    
    if reservation is None :
        db.close()
        return jsonify(error="You have no active reservation"), 404
    else:
        try:
            db.execute("UPDATE reservations SET status = 'success' WHERE id = ?",
                       (reservation["id"],))
            db.execute("UPDATE compartments SET status = 'full' WHERE id = ?",
                       (reservation["compartment_id"],))

            if db.execute("SELECT streak FROM users WHERE id = ?", (session["user_id"],)).fetchone()["streak"] < 7:
                db.execute("UPDATE users SET streak = streak + 1 WHERE id = ?",
                        (session["user_id"],))
            else:
                db.execute("UPDATE users SET streak = 0, penalty_score = 0 WHERE id = ?",
                            (session["user_id"],))
            
            db.commit()
            return jsonify(message="The deposit has been successful")
        except sqlite3.IntegrityError:
            return jsonify(error="Couldn't modify the statuses"), 500
        finally:
            db.close()

@app.route("/reserve-compartment")
def reserve_compartment():
    if not session.get("user_id"):
        return jsonify(error="You must be logged in."), 401

    locker_id = request.args.get("locker_id", type=int)
    size = request.args.get("size", type=int)
    if locker_id is None or size not in (1, 2, 3):
        return jsonify(error="Invalid request."), 400

    compartmentAvailable = checkReservationAvailability(locker_id, size, session["user_id"])
    if not compartmentAvailable[0] and not compartmentAvailable[1]:
        date = getAccountUnlockedDate(session.get("user_id"))
        return jsonify(error=f"Your account is locked until {date}" if date else "Your account is locked."), 403
    
    if not compartmentAvailable[0]:
        return jsonify(error="You can have only 1 reservation at the time"), 409

    db = get_db()
    try:
        code = f"{randint(1000, 9999):04d}"
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        db.execute(
            "INSERT INTO reservations (user_id, compartment_id, created_at, code) VALUES (?,?,?,?)",
            (session["user_id"], compartmentAvailable[0], created_at, code),
        )
        db.execute("UPDATE compartments SET status = 'reserved' WHERE id = ?", (compartmentAvailable[0],))
        db.commit()
    except sqlite3.IntegrityError:
        traceback.print_exc()
        db.rollback()
        return jsonify(error="Someone just took this compartment, try another one"), 409
    except Exception:
        traceback.print_exc()
        db.rollback()
        return jsonify(error="Something went wrong, please try again"), 500
    finally:
        db.close()

    return jsonify(message="Compartment reserved!"), 201



#%% /////////////////////////////////////////////////////////////////////////////
#%% ////////////////////////////// API routes ///////////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////     
@app.route("/api/get-lockers-info")
def getlockers():
    if not session.get("user_id"):
        return jsonify(error="unauthorized"), 401

    try:
        user_lat = float(request.args["lat"])
        user_lon = float(request.args["lon"])
    except (KeyError, ValueError):
        return jsonify(error="lat and lon query parameters are required"), 400

    db = get_db()
    try:
        rows = db.execute("""
            SELECT l.id, l.location_name, l.provider, l.latitude, l.longitude,
                   COALESCE(SUM(c.status = 'empty' AND c.size = 1), 0) AS small_left,
                   COALESCE(SUM(c.status = 'empty' AND c.size = 2), 0) AS medium_left,
                   COALESCE(SUM(c.status = 'empty' AND c.size = 3), 0) AS big_left
            FROM lockers l
            LEFT JOIN compartments c ON c.locker_id = l.id
            GROUP BY l.id
        """).fetchall()
    finally:
        db.close()

    lockers = [
        {
            "locker_id": r["id"],
            "locker_location_name": r["location_name"],
            "locker_brand": r["provider"],
            "locker_latitude": r["latitude"],
            "locker_longitude": r["longitude"],
            "distance_to_user_km": round(
                haversine_km(user_lat, user_lon, r["latitude"], r["longitude"]), 2
            ),
            "small_compartments_left": r["small_left"],
            "medium_compartments_left": r["medium_left"],
            "big_compartments_left": r["big_left"],
        }
        for r in rows
    ]
    lockers.sort(key=lambda l: l["distance_to_user_km"])

    return jsonify(lockers)

@app.route("/api/get-reservation-info")
def getReservationInfo():
    if not session.get("user_id"):
        return jsonify(error="unauthorized"), 401

    db = get_db()
    try:
        row = db.execute("""
            SELECT r.id, r.code, r.created_at,
                   c.number, c.size, l.location_name
            FROM reservations r
            JOIN compartments c ON c.id = r.compartment_id
            JOIN lockers l ON l.id = c.locker_id
            WHERE r.user_id = ? AND r.status = 'active'
            ORDER BY r.created_at DESC
            LIMIT 1
        """, (session["user_id"],)).fetchone()
    finally:
        db.close()

    if row is None:
        return jsonify({})

    created = datetime.strptime(row["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    expires = created + timedelta(minutes=RESERVATION_MINUTES)
    seconds_left = int((expires - datetime.now(timezone.utc)).total_seconds())

    if seconds_left <= 0:
        return jsonify({}) 

    return jsonify(
        reservation_id=row["id"],
        code=row["code"],
        created_at=row["created_at"],
        locker_name=row["location_name"],
        compartment_number=row["number"],
        size=row["size"],
        seconds_left=seconds_left,
    )

@app.route("/api/get-user-information")
def getUserInfo():
    unlockUsersAccount()
    if not session.get("user_id") : 
        return jsonify(error="unauthorized"), 401
    
    db = get_db()
    try:
        user_info = db.execute("SELECT penalty_score, locked_deadline, name, email, streak FROM users WHERE id = ?",
                           (session.get("user_id"),)).fetchone()

    except sqlite3.IntegrityError:
        traceback.print_exc()
        return jsonify(error="Impossible to recover the user information from de database"), 500
    finally:
        db.close()

    if user_info is None:
        return jsonify(error="unknown user"), 401
    
    return jsonify(dict(user_info))



#%% /////////////////////////////////////////////////////////////////////////////
#%% //////////////////////////// Errors handling ////////////////////////////////
#%% /////////////////////////////////////////////////////////////////////////////  
@app.errorhandler(401)
def unauthorized(error):
    return render_template("errors/401.html"), 401

@app.errorhandler(403)
def forbidden(error):
    return render_template("errors/403.html"), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("errors/404.html"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template("errors/500.html"), 500



#%% /////////////////////////////////////////////////////////////////////////////   
if __name__ == "__main__":
    app.run(port=3000, debug=False)    