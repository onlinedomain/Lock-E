import os
import sqlite3
from flask import Flask, jsonify, request, redirect, render_template, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from math import radians, sin, cos, asin, sqrt

app = Flask(__name__, static_folder='static', static_url_path='')

# Key to create cookies for users sessions
app.secret_key = "to modify before publishing and create an env variable"

app.config.update(SESSION_COOKIE_SAMESITE="lax") # CSRF protection

DOSSIER = os.path.dirname(os.path.abspath(__file__))
CHEMIN_DB = os.path.join(DOSSIER, 'lock_e_database.db')

#%% ///////////////////////////////////////////////////////////////////////////

def get_db():
    db = sqlite3.connect(CHEMIN_DB)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

#%% ///////////////////////////////////////////////////////////////////////////

def is_admin_user():
    user_id = session.get("user_id")
    if not user_id:
        return False
    db = get_db()
    user = db.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return bool(user and user["is_admin"])

#%% ///////////////////////////////////////////////////////////////////////////

@app.route('/')
def default():

    if session.get("user_id"):
        
        if is_admin_user() :
            return render_template("index.html")
    
        return render_template("index.html")
    
    return render_template("login.html")


#%% ///////////////////////////////////////////////////////////////////////////
# /////////////////////////Account related routes//////////////////////////////
# /////////////////////////////////////////////////////////////////////////////

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
            # We coule also use here : session["user_id"] = cursor.lastrowid
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

#%% ///////////////////////////////////////////////////////////////////////////

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

#%% ///////////////////////////////////////////////////////////////////////////

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

#%% ///////////////////////////////////////////////////////////////////////////

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))

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

#%% ///////////////////////////////////////////////////////////////////////////

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



if __name__ == "__main__":
    app.run(port=3000, debug=False)
    
    

    
    
    
    
    
    
    
    
    
    
    
    
    