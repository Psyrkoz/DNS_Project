from flask import Flask,render_template,request,redirect, flash, abort, url_for
from flask_login import login_required, current_user, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
from user import UserModel,db,login
from is_safe_url import is_safe_url
import datetime

app = Flask(__name__, template_folder="templates")

@app.before_first_request
def create_db():
    db.create_all()
    user = UserModel(username="Psyrkoz")
    user.set_password("test")
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
        print('Posted some data')
        username = request.form['username']
        user = UserModel.query.filter_by(username = username).first()
        if(user is not None and user.check_password(request.form['password'])):
            login_user(user)
            return redirect(url_for('home'))
    return render_template("login.html")

@app.route('/home', methods=['GET'])
@login_required
def home():
    return render_template('home.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('connexion'))

if(__name__ == '__main__'):
    db.init_app(app)
    login.init_app(app)
    login.login_view = 'connexion'
    csrf = CSRFProtect()
    csrf.init_app(app)

    app.config['SECRET_KEY'] = "goodluckcrackingthatyouass"
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://{}:{}@{}:{}/{}".format('root', '', 'localhost', 3306, 'dnsproject')
    app.config['SESSION_SQLALCHEMY_TABLE'] = 'sessions'
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.permanent_session_lifetime = datetime.timedelta(minutes=30)
    app.run(debug=True, port=5000)