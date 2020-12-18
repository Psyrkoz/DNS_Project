from flask import Flask,render_template,request,redirect, flash, abort, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import exc
from flask_wtf.csrf import CSRFProtect
from user import UserModel, db,login
from is_safe_url import is_safe_url
import datetime
import os

app = Flask(__name__, template_folder="templates")

@app.before_first_request
def init():
    db.create_all()
    x = db.engine.execute("SELECT * FROM users")
    account = [n for n in x]
    if(len(account) == 0):
        print("Creating base account [admin:admin] -> You should consider changing it!")
        session["message"] = "Le compte admin:admin a été crée. Vous devriez changer le mot de passe!"
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
    return render_template("login.html")

@app.route('/home', methods=['GET'])
@login_required
def home():
    session['message'] = ""
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('connexion'))

@app.route('/account')
@login_required
def account():
    return render_template('account.html')

if(__name__ == '__main__'):

    ### Initialise l'application
    app.secret_key = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://{}:{}@{}:{}/{}".format('root', '', 'localhost', 3306, 'dnsproject')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.permanent_session_lifetime = datetime.timedelta(minutes=60)
    
    ### Initialise les components (DB, Login, CSRF)
    db.init_app(app)
    login.init_app(app)
    login.login_view = 'connexion'
    csrf = CSRFProtect()
    csrf.init_app(app)

    app.run(debug=True, port=5000)