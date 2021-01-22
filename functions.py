import re
import os
import subprocess
import config

ALLOWED_EXTENSION = {'txt'}

# Vérifie que le mot de passe est correct en terme de sécurité
# 8 charactère, 1 maj, 1 min, 1 numérique et un symbole minimum
def isPasswordStrong(password):
    lengthError = len(password) < 8
    digitError = re.search(r"\d", password) is None
    uppercaseError = re.search(r"[A-Z]", password) is None
    lowercaseError = re.search(r"[a-z]", password) is None
    symbolError = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    return not (lengthError or digitError or uppercaseError or lowercaseError or symbolError)

# Retourne la liste des URL blacklisté
def getBlacklistURL():
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/blacklist.lst', 'r')
        content = file.read()
        file.close()
        urls = re.findall(r"\"(.+)\" static", content)
        return urls
    except IOError:
        print("Erreur")
        return []

# Vérifie que le nom de fichier donné est bien un .txt
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

# Ajoute a la blacklist une liste de nom de domaine
def addListToBlacklist(path):
    try:
        file = open(path, 'r')
        blacklist = open(config.unbound_folder + '/unbound.conf.d/blacklist.lst', 'a')
        urls = file.readlines()

        for url in urls:
            blacklist.write("local-zone: \"" + url.strip() + "\" static\n")
        blacklist.close()
        file.close()

        os.system("sudo service unbound restart")
        return "Les URLs ont bien été ajouté à la blacklist", ""
    except IOError:
        return "", "Impossible d'écrire les nouvelles URL dans la blacklist"

# Rajoute 1 URL à la blacklist
def addURLtoBlacklist(url):
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/blacklist.lst', 'a')
        file.write("local-zone: \"" + url + "\" static\n")
        file.close()
        os.system("sudo service unbound restart")

        return "L'URL '" + url + "' à bien été ajouté à la blacklist", ""
    except IOError:
        return "", "Erreur lors de l'ajout de '" + url + "' à la blacklist"

# Supprime une URL de la blacklist
def deleteURL(url):
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/blacklist.lst', 'r')
        lines = file.readlines()
        file.close()

        file = open(config.unbound_folder + '/unbound.conf.d/blacklist.lst', 'w')
        for line in lines:
            if(line.strip() != "local-zone: \"" + url + "\" static"):
                file.write(line)

        os.system("sudo service unbound restart")
        return "L'URL '" + url + "' à bien été supprimé", ""
    except IOError:
        return "", "Impossible de supprimer l'URL '" + url + "'"

def getServiceStatus():
    return True if os.system("sudo systemctl is-active --quiet unbound") == 0 else False

def handleParametersArgument(arg):
    status = getServiceStatus()
    if(arg == 'startUnbound' and not status):
        os.system("sudo service unbound start")
    elif(arg == 'restartUnbound' and status):
        os.system("sudo service unbound restart")
    elif(arg == 'stopUnbound' and status):
        os.system("sudo service unbound stop")
    else:
        print("Bad method / Wrong method called")

def getBlacklistCount():
    try:
        with open(config.unbound_folder + "/unbound.conf.d/blacklist.lst") as blacklistfile:
            return sum(1 for _ in blacklistfile)
    except IOError:
        print("The file 'blacklist.lst' in /unbound.conf.d/ does not exist")
        return 0

def getUnboundStats():
    stats = str(subprocess.check_output(['sudo', 'unbound-control', 'stats']))

    # Parse l'uptime et le met en format HH:MM:SS
    uptime = round(float(re.findall(r"time\.up=(\d+.\d+)", stats)[0]))
    m, s = divmod(uptime, 60)
    h, m = divmod(m, 60)
    uptime = '{:d}:{:02d}:{:02d}'.format(h, m, s)

    # Parse le nombre de requêtes   
    number_query = re.findall(r"num\.query\.type\.A=(\d+)", stats)[0]

    # Parse le nombre de requêtes bloqué (NXDomain)
    number_blocked = re.findall(r"num\.answer\.rcode\.NXDOMAIN=(\d+)", stats)[0]

    return uptime, number_query, number_blocked