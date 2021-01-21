import re
import os

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
        file = open('/etc/unbound/unbound.conf.d/blacklist.lst', 'r')
        content = file.read()
        file.close()
        urls = re.findall(r"\"(.+)\" static", content)
        return urls
    except IOError:
        print("WTF BBQ")
        return []

# Vérifie que le nom de fichier donné est bien un .txt
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

# Ajoute a la blacklist une liste de nom de domaine
def addListToBlacklist(path):
    try:
        file = open(path, 'r')
        blacklist = open('/etc/unbound/unbound.conf.d/blacklist.lst', 'a')
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
        file = open('/etc/unbound/unbound.conf.d/blacklist.lst', 'a')
        file.write("local-zone: \"" + url + "\" static\n")
        file.close()
        os.system("sudo service unbound restart")

        return "L'URL '" + url + "' à bien été ajouté à la blacklist", ""
    except IOError:
        return "", "Erreur lors de l'ajout de '" + url + "' à la blacklist"

# Supprime une URL de la blacklist
def deleteURL(url):
    try:
        file = open("/etc/unbound/unbound.conf.d/blacklist.lst", 'r')
        lines = file.readlines()
        file.close()

        file = open("/etc/unbound/unbound.conf.d/blacklist.lst", 'w')
        for line in lines:
            if(line.strip() != "local-zone: \"" + url + "\" static"):
                file.write(line)

        os.system("sudo service unbound restart")
        return "L'URL '" + url + "' à bien été supprimé", ""
    except IOError:
        return "", "Impossible de supprimer l'URL '" + url + "'"