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
def getBlacklistURL(blacklistName):
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/' + blacklistName, 'r')
        content = file.read()
        file.close()
        urls = re.findall(r"\"(.+)\" static", content)
        return urls
    except IOError:
        print("Erreur")
        return []

def deleteBlacklist(blacklistName):
    if blacklistName in os.listdir(config.unbound_folder + "/unbound.conf.d/"):
        namesAndUsage = getBlacklistFilesAndUsage()
        if blacklistName in namesAndUsage.keys() and namesAndUsage[blacklistName]:
            newBlacklistUsage = {}
            for name, usages in namesAndUsage.items():
                if name != blacklistName:
                    newBlacklistUsage[name] = "1" if usages else False 
            setNewBlacklistUsages(newBlacklistUsage)
            os.system("sudo service unbound restart")
        os.remove(config.unbound_folder + "/unbound.conf.d/" + blacklistName)
        

# Vérifie que le nom de fichier donné est bien un .txt
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSION

# Ajoute a la blacklist une liste de nom de domaine
def addListToBlacklist(blacklistName, path):
    try:
        file = open(path, 'r')
        blacklist = open(config.unbound_folder + '/unbound.conf.d/' + blacklistName, 'a')
        urls = file.readlines()

        for url in urls:
            blacklist.write("local-zone: \"" + url.strip() + "\" static\n")
        blacklist.close()
        file.close()

        os.system("sudo service unbound restart")
        return "Les URLs ont bien été ajouté à la blacklist '" + blacklistName +   "'", ""
    except IOError:
        return "", "Impossible d'écrire les nouvelles URL dans la blacklist '" + blacklistName + "'"

# Rajoute 1 URL à la blacklist
def addURLtoBlacklist(blacklistName, url):
    print("Adding " + url + "to" + blacklistName)
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/' + blacklistName, 'a')
        file.write("local-zone: \"" + url + "\" static\n")
        file.close()
        os.system("sudo service unbound restart")

        return "L'URL '" + url + "' à bien été ajouté à la blacklist", ""
    except IOError:
        return "", "Erreur lors de l'ajout de '" + url + "' à la blacklist"

# Supprime une URL de la blacklist
def deleteURL(blacklistName, url):
    try:
        file = open(config.unbound_folder + '/unbound.conf.d/' + blacklistName, 'r')
        lines = file.readlines()
        file.close()

        file = open(config.unbound_folder + '/unbound.conf.d/' + blacklistName, 'w')
        for line in lines:
            if(line.strip() != "local-zone: \"" + url + "\" static"):
                file.write(line)

        os.system("sudo service unbound restart")
        return "L'URL '" + url + "' à bien été supprimé de la blacklist '" + blacklistName + "'", ""
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
    namesAndUsage = getBlacklistFilesAndUsage()
    try:
        somme = 0
        for name, usage in namesAndUsage.items():
            if usage:
                with open(config.unbound_folder + "/unbound.conf.d/" + name) as blacklistfile:
                    somme += sum(1 for _ in blacklistfile)
        return somme
    except IOError:
        print("The file 'blacklist.lst' in /unbound.conf.d/ does not exist")
        return 0

def getUnboundStats():
    stats = str(subprocess.check_output(['sudo', 'unbound-control', 'stats']))

    # Parse l'uptime et le met en format HH:MM:SS
    try:
        uptime = round(float(re.findall(r"time\.up=(\d+.\d+)", stats)[0]))
        m, s = divmod(uptime, 60)
        h, m = divmod(m, 60)
        uptime = '{:d} heure(s) {:02d} minute(s) {:02d} seconde(s)'.format(h, m, s)

        # Parse le nombre de requêtes   
        number_query = re.findall(r"num\.query\.type\.A=(\d+)", stats)[0]

        # Parse le nombre de requêtes bloqué (NXDomain)
        number_blocked = re.findall(r"num\.answer\.rcode\.NXDOMAIN=(\d+)", stats)[0]

        return uptime, number_query, number_blocked
    except IndexError:
        return "/", "/", "/"

def getBlacklistFilesAndUsage():
    blacklistInUse = []
    try:
        with open(config.unbound_folder + "/unbound.conf.d/default.conf", 'r') as f:
            content = f.read()
            blacklistInUse = re.findall(r'include: "' + config.unbound_folder + r'/unbound.conf.d/(.+\.lst)', content)

        blacklist_files = {}
        for f in os.listdir(config.unbound_folder + "/unbound.conf.d"):
            if f.endswith(".lst"):
                blacklist_files[f] = True if f in blacklistInUse else False
        
        return blacklist_files
    except IOError:
        print("Unable to open default.conf in unbound folder...")

# Rajoute (ou enleve) des blacklists de la liste d'include de default.conf
def setNewBlacklistUsages(newBlacklistUsage):
    content = None
    with open(config.unbound_folder + "/unbound.conf.d/default.conf", 'r') as f:
        content = f.readlines()
    
    insertIndex = 0
    for line in content:
        if "include:" in line:
            content[content.index(line)] = ""
        elif 'do-tcp' in line:
            insertIndex = content.index(line) + 1

    for blacklistName, usage in newBlacklistUsage.items():
            if(usage == "1"):
                content.insert(insertIndex, "\tinclude: \"" + config.unbound_folder + "/unbound.conf.d/" + blacklistName +"\"\n")

    with open(config.unbound_folder + "/unbound.conf.d/default.conf", "w") as f:    
        for line in content:
            f.write(line)

    os.system("sudo service unbound restart")

    

    