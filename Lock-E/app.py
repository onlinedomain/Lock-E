import os
import sqlite3
from flask import Flask, jsonify, request, redirect, render_template, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='public', static_url_path='')

# Key to create cookies for users sessions
app.secret_key = "to modify before publishing and create an env variable"

app.config.update(SESSION_COOKIE_SAMESITE="lax") # CSRF protection

DOSSIER = os.path.dirname(os.path.abspath(__file__))
CHEMIN_DB = os.path.join(DOSSIER, 'lock-e-database.db')

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
            return render_template("admin.html")
    
        return render_template("index.html")
    
    return render_template("overview.html")


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


if __name__ == "__main__":
    app.run(port=3000, debug=False)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    