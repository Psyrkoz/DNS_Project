import re
import os
import subprocess
import config
import pwd
import grp

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

# Retourne la liste des URL blacklisté d'une blacklist spécifique
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

# Supprime la blacklist [blakclistName] (.lst inclu dans le nom)
# Vérifie au préalable que le fichier spécifié se situe dans [config.unbound_folder + "/unbound.conf.d/"]
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

# Vide entièrement le fichier de blacklist [blacklistName]
# Une vérification que le fichier spécifié se situe dans [config.unbound_folder + "/unbound.conf.d/"] est faite au préalable
def emptyBlacklist(blacklistName):
    if os.path.isfile(config.unbound_folder + "/unbound.conf.d/" + blacklistName):
        try:
            open(config.unbound_folder + "/unbound.conf.d/" + blacklistName, 'w')
        except IOError:
            print("Erreur lors du vidage de '" + config.unbound_folder + "/unbound.conf.d/" + blacklistName + "'")
    else:
        print("Le fichier '" + config.unbound_folder + "/unbound.conf.d/" + blacklistName + "' n'existe pas...")
    

# Ajoute a la blacklist une liste de nom de domaine contenu dans le fichier situé dans [path]
# Le fichier situé dans dans [path] est supprimé directement après
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

# Vérifie l'état du service unbound
# os.system("sudo systemctl is-active --quiet unbound") retourne 0 si le service est lancé
def getServiceStatus():
    return True if os.system("sudo systemctl is-active --quiet unbound") == 0 else False


# Permet de gérer l'appui de bouton gérant le service unbound dans /parameters
def handleParametersArgument(arg):
    status = getServiceStatus()
    if(arg == 'startUnbound' and not status):
        os.system("sudo service unbound start")
    elif(arg == 'restartUnbound' and status):
        os.system("sudo service unbound restart")
    elif(arg == 'stopUnbound' and status):
        os.system("sudo service unbound stop")
    else:
        print("Mauvaise méthode appelé")

# Retourne le nombre d'url dans les différentes blacklists en cours d'utilisation
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
        print("Impossible de lire un des fichiers de blacklist...")
        return 0

# Retourne les statistiques de unbound
# Retourne:
#   - L'uptime du service
#   - Le nombre de requêtes faites
#   - Le nombre de requêtes bloquées
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

# Vérifie l'utilisation des blacklists
# Dans le dossier /unbound.conf.d/ se situe (avec l'extension .lst) les fichiers de blacklist
# Si la blacklist se situe dans la zone d'include du fichier "default.conf", alors la valeur associé a la blacklist sera True, False sinon
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
        print("Impossible d'ouvrir le fichier '" + config.unbound_folder + "/unbound.conf.d/default.conf")

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


# Crée le fichier [name].lst dans le répertoire unbound.conf.d
# Retourne un message d'erreur si il est impossible de créer le fichier
# Seul des caractères alphabétique sont autorisés
def createBlacklist(name):
    if os.path.isfile(config.unbound_folder + "/unbound.conf.d/" + name + ".lst"):
        return "Une blacklist avec le même nom existe déjà"
    else:
        if name.isalpha():
            try:
                open(config.unbound_folder + "/unbound.conf.d/" + name + ".lst", 'x')
                return ""
            except IOError:
                return "Une erreur non attendu est survenu..."
        else:
            return "Le nom de la blacklist ne peut que contenir des lettres"

# Vérifie que le fichier "default.conf" soit présent dans le dossier /unbound.conf.d/
# Si non présent, la fonction crée le fichier avec les valeurs par défaut
# Réecris le fichier unbound.conf pour inclure tout les fichiers .conf situé dans /unbound.conf.d/
def check_unbound_configuration():
    default_conf_exist = os.path.isfile(config.unbound_folder + "/unbound.conf.d/default.conf")
    try:
        with open(config.unbound_folder + "/unbound.conf", 'w') as f:
            f.write('include: "' + config.unbound_folder + '/unbound.conf.d/*.conf"')
    except IOError:
        print("Impossible de remplacer le contenu de '" + config.unbound_folder + "/unbound.conf'")
    
    if not default_conf_exist:
        try:
            lines = ['server:\n', '\tchroot: ""\n', '\tverbosity: 1\n', '\tlogfile: "' + config.unbound_log_file + '"\n', '\tlog-time-ascii: yes\n', '\tlog-queries: yes\n', '\tlog-replies: yes\n', '\n', '\tstatistics-interval: 0\n', '\textended-statistics: yes\n', '\tstatistics-cumulative: yes\n', '\tinterface: 0.0.0.0\n', '\t\n', '\taccess-control: 127.0.0.0/8 allow\n', '\taccess-control: 192.168.0.0/24 allow\n', '\taccess-control: 192.168.1.0/24 allow\n', '\tport: 53\n', '\tdo-ip6: no\n', '\tdo-ip4: yes\n', '\tdo-udp: yes\n', '\tdo-tcp: yes\n', '\n', '\n', 'remote-control:\n', '\n', '\tcontrol-enable: yes\n', '\tcontrol-use-cert: no\n', '\n', 'forward-zone:\n', '\tname: "."\n', '\tforward-addr: 8.8.8.8\n', '\n']
            with open(config.unbound_folder + "/unbound.conf.d/default.conf", 'w') as f:
                f.writelines(lines)
        except IOError:
            print("Impossible d'écrire les valeurs par défaut dans '" + config.unbound_folder+  "/unbound.conf.d/default.conf'")

def resetConfig():
    # Réécris le fichier unbound.conf
    try:
        with open(config.unbound_folder + "/unbound.conf", 'w') as f:
            f.write('include: "' + config.unbound_folder + '/unbound.conf.d/*.conf"')
    except IOError:
        print("Impossible de remplacer le contenu de '" + config.unbound_folder + "/unbound.conf'")
    
    
    # Supprime (si existe) le fichier default.conf et le ré écris
    default_conf_exist = os.path.isfile(config.unbound_folder + "/unbound.conf.d/default.conf")
    if default_conf_exist:
        os.remove(config.unbound_folder + "/unbound.conf.d/default.conf")
    try:
        lines = ['server:\n', '\tchroot: ""\n', '\tverbosity: 1\n', '\tlogfile: "' + config.unbound_log_file + '"\n', '\tlog-time-ascii: yes\n', '\tlog-queries: yes\n', '\tlog-replies: yes\n', '\n', '\tstatistics-interval: 0\n', '\textended-statistics: yes\n', '\tstatistics-cumulative: yes\n', '\tinterface: 0.0.0.0\n', '\t\n', '\taccess-control: 127.0.0.0/8 allow\n', '\taccess-control: 192.168.0.0/24 allow\n', '\taccess-control: 192.168.1.0/24 allow\n', '\tport: 53\n', '\tdo-ip6: no\n', '\tdo-ip4: yes\n', '\tdo-udp: yes\n', '\tdo-tcp: yes\n', '\n', '\n', 'remote-control:\n', '\n', '\tcontrol-enable: yes\n', '\tcontrol-use-cert: no\n', '\n', 'forward-zone:\n', '\tname: "."\n', '\tforward-addr: 8.8.8.8\n', '\n']
        with open(config.unbound_folder + "/unbound.conf.d/default.conf", 'w') as f:
            f.writelines(lines)
    except IOError:
            print("Impossible d'écrire les valeurs par défaut dans '" + config.unbound_folder+  "/unbound.conf.d/default.conf'")

    # Supprime tout les fichiers .lst (nos blacklist)
    for f in os.listdir(config.unbound_folder + "/unbound.conf.d"):
        if f.endswith(".lst"):
            os.remove(config.unbound_folder + "/unbound.conf.d/" + f)
    
    # Supprime le fichier de log (si existe) et le recrée (et met unbound en tant que owner)
    log_file_exist = os.path.isfile(config.unbound_log_file)
    if(log_file_exist):
        os.remove(config.unbound_log_file)
    try:
        f = open(config.unbound_log_file, 'w')
        f.close()
        unbound_uid = pwd.getpwnam('unbound').pw_uid
        unbound_gid = grp.getgrnam('unbound').gr_gid
        os.chown(config.unbound_log_file, unbound_uid, unbound_gid)
    except IOError:
        print("Erreur lors de la re création du logfile")
    except KeyError:
        print("L'utilisateur 'unbound' n'existe pas... Avez-vous installé unbound?")

def getLogs():
    try:
        with open(config.unbound_log_file, 'r') as f:
            return ''.join(f.readlines()[::-1])
    except IOError:
        return "Erreur lors de la lecture du fichier de log"

def empty_logs():
    try:
        open(config.unbound_log_file, 'w')
        return "Fichier de log vidé"
    except IOError:
        return "Erreur lors du vidage du fichier de log"