import re
import os

def isPasswordStrong(password):
    lengthError = len(password) < 8
    digitError = re.search(r"\d", password) is None
    uppercaseError = re.search(r"[A-Z]", password) is None
    lowercaseError = re.search(r"[a-z]", password) is None
    symbolError = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None

    return not (lengthError or digitError or uppercaseError or lowercaseError or symbolError)

def getBlacklistURL():
    try:
        file = open('/etc/unbound/unbound.conf.d/blacklist.lst', 'r')
        content = file.read()
        urls = re.findall(r"\"(.+)\" static")
        print(urls)
    except IOError:
        return []

    return []