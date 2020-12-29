from flask import Flask,render_template,request,redirect, flash, abort, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import exc
from flask_sessionstore import Session
from flask_wtf.csrf import CSRFProtect
from user import UserModel, db,login
from is_safe_url import is_safe_url
import datetime
import functions
import os

app = Flask(__name__, template_folder="templates")

# Init la DB et recherche les users déjà présent. Si aucun présent on crée le compte admin:admin et ont met un message pour dire de le changer
@app.before_first_request
def init():
    s = Session(app)
    db.create_all() 
    x = db.engine.execute("SELECT * FROM users")
    account = [n for n in x]
    
    if(len(account) == 0):
        print("Creating base account [admin:admin] -> You should consider changing it!")
        session["success_message"] = "Le compte admin:admin a été crée. Vous devriez changer le mot de passe (et vite)!"
        user = UserModel(username="admin")
        user.set_password("admin")
        db.session.add(user)
        db.session.commit()

@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    else:
        return redirect(url_for('connexion'))

@app.route("/connexion", methods=['GET', 'POST'])
def connexion():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if(request.method == "POST"):
        username = request.form['username']
        user = UserModel.query.filter_by(username = username).first()
        if(user is not None and user.check_password(request.form['password'])):
            login_user(user)
            return redirect(url_for('home'))
        else:
            session['error_message'] = 'Vérifier les identifiants de connexions'
    return render_template("login.html")

@app.route('/home', methods=['GET'])
@login_required
def home():
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('connexion'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == "GET":
        return render_template('account.html')
    else:
        username = current_user.username
        user = UserModel.query.filter_by(username=username).first()
        if(user is not None and user.check_password(request.form['current_password'])):
            if(request.form['new_password'] == request.form['new_password_confirm']):
                if(functions.isPasswordStrong(request.form['new_password'])):
                    user.set_password(request.form['new_password'])
                    db.session.commit()
                    session['success_message'] = 'Votre mot de passe à bien été modifié'
                else:
                    session['error_message'] = 'Le mot de passe doit contenir au moins 1 lettre majuscule et minuscule, 1 chiffres et 1 symbole'
            else:
                session['error_message'] = 'Les deux mots de passe ne sont pas identiques'
        else:
            session['error_message'] = 'Le mot de passe actuel n\'est pas le bon'
        return render_template('account.html')

@app.route('/blacklist', methods=['GET', 'POST'])
@login_required
def blacklist():
    if request.method == "POST":
        print(request.form['url'])

    blacklistURL = functions.getBlacklistURL()
    return render_template('blacklist.html', urls=blacklistURL)


# Après chaque requête ont enlève les messages dans la session pour éviter d'afficher des messages non voulu
@app.after_request
def resetMessage(response):
    session['success_message'] = ""
    session['error_message'] = ""
    return response

if(__name__ == '__main__'):
    ### Initialise l'application
    app.secret_key = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://{}:{}@{}:{}/{}".format('root', '', 'localhost', 3306, 'dnsproject')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_SQLALCHEMY_TABLE'] = "sessions"
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['PERMANENT_SESSION_LIFETIME'] = 30*60 # 30 minutes

    ### Initialise les components (DB, Login, CSRF)
    db.init_app(app)
    login.init_app(app)
    login.login_view = 'connexion'
    csrf = CSRFProtect()
    csrf.init_app(app)

    app.run(debug=True, port=5000)