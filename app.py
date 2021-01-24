from flask import Flask,render_template,request,redirect, flash, abort, url_for, session
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import exc
from flask_sessionstore import Session
from flask_wtf.csrf import CSRFProtect
from user import UserModel, db,login
from is_safe_url import is_safe_url
from sys import platform
from werkzeug.utils import secure_filename
import datetime
import functions
import os
import config
import argparse

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
        return redirect(url_for('parameters'))
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
            return redirect(url_for('parameters'))
        else:
            session['error_message'] = 'Vérifier les identifiants de connexions'

    status = functions.getServiceStatus()
    if(status):
        uptime, number_query, query_blocked = functions.getUnboundStats()
        return render_template("login.html", status=status, number_query=number_query, query_blocked=query_blocked)
    else:
        return render_template("login.html", status=status)

@app.route('/home', methods=['GET'])
@login_required
def home():
    servicesStatus = functions.getServiceStatus()
    return render_template('home.html', status = servicesStatus)

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
            # Changement de nom de compte
            if(request.form['username'] != user.get_username()):
                if(UserModel.query.filter_by(username=request.form['username']).first() == None): # Aucun autre user a ce username -> On peut le changer
                    user.set_username(request.form['username'])
                    db.session.commit()
                    session['success_message'] = 'Le nom de compte a bien été modifié'
                else:
                    session['error_message'] = "Le nom de compte est déjà pris par un autre utilisateur"

            # Changement de password
            if(request.form['new_password'] != ''):
                if(request.form['new_password'] == request.form['new_password_confirm']):
                    if(functions.isPasswordStrong(request.form['new_password'])):
                        user.set_password(request.form['new_password'])
                        db.session.commit()
                        session['success_message'] += 'Votre mot de passe à bien été modifié'
                    else:
                        session['error_message'] += 'Le mot de passe doit contenir au moins 1 lettre majuscule et minuscule, 1 chiffres et 1 symbole'
                else:
                    session['error_message'] = 'Les deux mots de passe ne sont pas identiques'
        else:
            session['error_message'] = 'Le mot de passe actuel n\'est pas le bon'
        return render_template('account.html')

@app.route('/blacklist/<string:blacklistName>', methods=['GET', 'POST'])
@login_required
def blacklist(blacklistName):
    if request.method == "POST":
        session['success_message'], session['error_message'] = functions.addURLtoBlacklist(blacklistName, request.form['url'])

    blacklistURL = functions.getBlacklistURL(blacklistName)
    return render_template('blacklist.html', blacklistName=blacklistName, urls=blacklistURL)

@app.route('/blacklist/<string:blacklistName>/delete')
@login_required
def deleteBlacklist(blacklistName):
    functions.deleteBlacklist(blacklistName)
    return redirect('/parameters')

@app.route('/blacklist/<string:blacklistName>/delete/<string:url>')
@login_required
def delete(blacklistName, url):
    session['success_message'], session['error_message'] = functions.deleteURL(blacklistName, url)
    return render_template('blacklist.html', urls=functions.getBlacklistURL(blacklistName))

@app.route('/blacklist/<string:blacklistName>/add_list', methods=['POST'])
@login_required
def blacklist_addList(blacklistName):
    if request.method == "POST":
        if 'file' not in request.files:
            session['error_message'] = "Vous devez spécifier un fichier"

        file = request.files['file']
        if file.filename == '':
            session['error_message'] = "Vous devez spécifier un fichier"
        
        if file and functions.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            session['success_message'], session['error_message'] = functions.addListToBlacklist(blacklistName, path)
            os.remove(path)
        else:
            session['error_message'] = "Il faut choisir un fichier .txt"

    return render_template('blacklist.html', urls=functions.getBlacklistURL(blacklistName))

@app.route('/backlist/<string:blacklistName>/empty')
@login_required
def emptyBlacklist(blacklistName):
    functions.emptyBlacklist(blacklistName)
    return redirect("/blacklist/" + blacklistName)

@app.route('/blacklist/create', methods=['GET', 'POST'])
@login_required
def create_blacklist():
    if (request.method == "POST"):
        session['error_message'] = functions.createBlacklist(request.form.get('name'))
        if session['error_message'] != '':
            return render_template('blacklist_create.html')
        else:
            return redirect('/parameters')
        
    return render_template('blacklist_create.html')

### Gère les pages /parameters

@app.route('/parameters', methods=['GET'])
@login_required
def parameters():
    servicesStatus = functions.getServiceStatus()
    blacklistFiles = functions.getBlacklistFilesAndUsage()
    if(servicesStatus):
        blackListCount = functions.getBlacklistCount()
        uptime, number_query, query_blocked = functions.getUnboundStats()
        return render_template('parameters.html', status=servicesStatus, blacklistFiles=blacklistFiles, blacklistcount=blackListCount, uptime=uptime, number_query=number_query, query_blocked=query_blocked)
    else:
        return render_template('parameters.html', status=servicesStatus, blacklistFiles=blacklistFiles)

@app.route('/parameters', methods=['POST'])
@login_required
def changeParameters():
    newBlacklistFilesUsages = dict(zip(request.form.getlist('blacklistName[]'), request.form.getlist('blacklistUsage[]')))
    functions.setNewBlacklistUsages(newBlacklistFilesUsages)
    return redirect('/parameters')
    

@app.route('/parameters/<string:method>')
@login_required
def parametersMethods(method):
    functions.handleParametersArgument(method)
    return redirect('/parameters')

@app.route('/log', methods=['GET'])
@login_required
def view_log():
    logs = functions.getLogs()
    return render_template('log.html', logs=logs)

@app.route('/log/empty', methods=['GET'])
@login_required
def empty_logs():
    functions.empty_logs()    
    return redirect('/log')

# Après chaque requête ont enlève les messages dans la session pour éviter d'afficher des messages non voulu
@app.after_request
def resetMessage(response):
    session['success_message'] = ""
    session['error_message'] = ""
    return response

def startApp():
    ### Initialise l'application
    app.secret_key = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://{}:{}@{}:{}/{}".format(config.database_user, config.database_password, config.database_url, config.database_port, config.database_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_SQLALCHEMY_TABLE'] = "sessions"
    app.config['SESSION_SQLALCHEMY'] = db
    app.config['PERMANENT_SESSION_LIFETIME'] = 30*60 # 30 minutes
    app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.abspath(__file__)) + "/uploads/"

    ### Initialise les components (DB, Login, CSRF)
    db.init_app(app)
    login.init_app(app)
    login.login_view = 'connexion'
    csrf = CSRFProtect()
    csrf.init_app(app)
    app.run(debug=False, port=config.application_port, ssl_context=('cert.pem', 'key.pem'))

if(__name__ == '__main__'):
    parser = argparse.ArgumentParser(description="Permet de gérer unbound")
    parser.add_argument('--reset-config', action="store_true", help="Permet de remettre a zero les fichiers de configurations du dossier unbound (unbound.conf & default.conf) - Supprime tout les fichiers .lst de unbound.conf.d ainsi que le fichier de log")
    args = parser.parse_args()
    if platform == "linux" or platform == "linux2":
        if(os.geteuid() != 0):
            print("This app should be runned as root")
        else:
            # Verifie que unbound est lancé
            if(args.reset_config):
                functions.resetConfig()
                os.system("sudo service unbound restart")

            functions.check_unbound_configuration()
            service = os.system("sudo systemctl is-active --quiet unbound")
            if(service == 0): # 0 = started, 768 = stopped
                startApp()
            else:
                print("Unbound service is stopped or does not exist...")
                startApp()
    else:
        print("This app should be runned on Linux")