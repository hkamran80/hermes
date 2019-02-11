#!/usr/bin/env python3

u"""
The MIT License (MIT)
Copyright (c) 2018 Louis Abraham <louis.abraham@yahoo.fr>

\x1B[34m\033[F\033[F

ffpass can import and export passwords from Firefox Quantum.

\x1B[0m\033[1m\033[F\033[F

example of usage:

    ffpass export --to passwords.csv
    
    ffpass import --from passwords.csv

\033[0m\033[1;32m\033[F\033[F

If you found this code useful, add a star on <https://github.com/louisabraham/ffpass>!

\033[0m\033[F\033[F
"""

from __future__ import with_statement
from __future__ import division
from __future__ import absolute_import
import sys
from base64 import b64decode, b64encode
from hashlib import sha1
import hmac
import argparse
import json
from pathlib import Path
import csv
import secrets
from getpass import getpass
from uuid import uuid4
from datetime import datetime
import ConfigParser
from urlparse import urlparse
import sqlite3
import os.path

from pyasn1.codec.der.decoder import decode as der_decode
from pyasn1.codec.der.encoder import encode as der_encode
from pyasn1.type.univ import Sequence, OctetString, ObjectIdentifier
from Crypto.Cipher import DES3
from io import open


MAGIC1 = "\xf8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"
MAGIC2 = (1, 2, 840, 113549, 3, 7)


class NoDatabase(Exception):
    pass


class WrongPassword(Exception):
    pass


def getKey(directory, masterPassword=u""):
    dbfile = directory + "/key4.db"
    if not dbfile.exists():
        raise NoDatabase()
    # firefox 58.0.2 / NSS 3.35 with key4.db in SQLite
    conn = sqlite3.connect(dbfile.as_posix())
    c = conn.cursor()
    # first check password
    c.execute(u"SELECT item1,item2 FROM metadata WHERE id = 'password';")
    row = c.next()
    globalSalt = row[0]  # item1
    item2 = row[1]
    decodedItem2, _ = der_decode(item2)
    entrySalt = decodedItem2[0][1][0].asOctets()
    cipherT = decodedItem2[1].asOctets()
    clearText = decrypt3DES(
        globalSalt, masterPassword, entrySalt, cipherT
    )  # usual Mozilla PBE
    if clearText != "password-check\x02\x02":
        raise WrongPassword()
    #if args.verbose:
    #    print("password checked", file=sys.stderr)
    # decrypt 3des key to decrypt "logins.json" content
    c.execute(u"SELECT a11,a102 FROM nssPrivate;")
    for row in c:
        if row[1] == MAGIC1:
            break
    a11 = row[0]  # CKA_VALUE
    assert row[1] == MAGIC1  # CKA_ID
    decodedA11, _ = der_decode(a11)
    entrySalt = decodedA11[0][1][0].asOctets()
    cipherT = decodedA11[1].asOctets()
    key = decrypt3DES(globalSalt, masterPassword, entrySalt, cipherT)
    #if args.verbose:
    #    print("3deskey", key.hex(), file=sys.stderr)
    return key[:24]


def PKCS7pad(b):
    l = (-len(b) - 1) % 8 + 1
    return b + str([l] * l)


def PKCS7unpad(b):
    return b[: -b[-1]]


def decrypt3DES(globalSalt, masterPassword, entrySalt, encryptedData):
    hp = sha1(globalSalt + masterPassword.encode()).digest()
    pes = entrySalt + "\x00" * (20 - len(entrySalt))
    chp = sha1(hp + entrySalt).digest()
    k1 = hmac.new(chp, pes + entrySalt, sha1).digest()
    tk = hmac.new(chp, pes, sha1).digest()
    k2 = hmac.new(chp, tk + entrySalt, sha1).digest()
    k = k1 + k2
    iv = k[-8:]
    key = k[:24]
    #if args.verbose:
    #    print("key=" + key.hex(), "iv=" + iv.hex(), file=sys.stderr)
    return DES3.new(key, DES3.MODE_CBC, iv).decrypt(encryptedData)


def decodeLoginData(key, data):
    # first base64 decoding, then ASN1DERdecode
    asn1data, _ = der_decode(b64decode(data))
    assert asn1data[0].asOctets() == MAGIC1
    assert asn1data[1][0].asTuple() == MAGIC2
    iv = asn1data[1][1].asOctets()
    ciphertext = asn1data[2].asOctets()
    des = DES3.new(key, DES3.MODE_CBC, iv)
    return PKCS7unpad(des.decrypt(ciphertext)).decode()


def encodeLoginData(key, data):
    iv = secrets.token_bytes(8)
    des = DES3.new(key, DES3.MODE_CBC, iv)
    ciphertext = des.encrypt(PKCS7pad(data.encode()))
    asn1data = Sequence()
    asn1data[0] = OctetString(MAGIC1)
    asn1data[1] = Sequence()
    asn1data[1][0] = ObjectIdentifier(MAGIC2)
    asn1data[1][1] = OctetString(iv)
    asn1data[2] = OctetString(ciphertext)
    return b64encode(der_encode(asn1data)).decode()


def getJsonLogins(directory):
    with open(directory / u"logins.json", u"r") as loginf:
        jsonLogins = json.load(loginf)
    return jsonLogins


def dumpJsonLogins(directory, jsonLogins):
    with open(directory / u"logins.json", u"w") as loginf:
        json.dump(jsonLogins, loginf, separators=u",:")


def exportLogins(key, jsonLogins):
    if u"logins" not in jsonLogins:
        print >>sys.stderr, u"error: no 'logins' key in logins.json"
        return []
    logins = []
    for row in jsonLogins[u"logins"]:
        encUsername = row[u"encryptedUsername"]
        encPassword = row[u"encryptedPassword"]
        logins.append(
            (
                row[u"hostname"],
                decodeLoginData(key, encUsername),
                decodeLoginData(key, encPassword),
            )
        )
    return logins


def readCSV(from_file):
    logins = []
    reader = csv.DictReader(from_file)
    for row in reader:
        logins.append((rawURL(row[u"url"]), row[u"username"], row[u"password"]))
    return logins


def rawURL(url):
    p = urlparse(url)
    return url.decode("ascii")


def addNewLogins(key, jsonLogins, logins):
    nextId = jsonLogins[u"nextId"]
    timestamp = int(datetime.now().timestamp() * 1000)
    for i, (url, username, password) in enumerate(logins, nextId):
        entry = {
            u"id": i,
            u"hostname": url,
            u"httpRealm": None,
            u"formSubmitURL": u"",
            u"usernameField": u"",
            u"passwordField": u"",
            u"encryptedUsername": encodeLoginData(key, username),
            u"encryptedPassword": encodeLoginData(key, password),
            u"guid": u"{%s}" % uuid4(),
            u"encType": 1,
            u"timeCreated": timestamp,
            u"timeLastUsed": timestamp,
            u"timePasswordChanged": timestamp,
            u"timesUsed": 0,
        }
        jsonLogins[u"logins"].append(entry)
    jsonLogins[u"nextId"] = i + 1


def guessDir():
    dirs = {
        u"darwin": u"~/Library/Application Support/Firefox",
        u"linux": u"~/.mozilla/firefox",
        u"win32": os.path.expandvars(ur"%LOCALAPPDATA%\Mozilla\Firefox"),
        u"cygwin": os.path.expandvars(ur"%LOCALAPPDATA%\Mozilla\Firefox"),
    }
    if sys.platform in dirs:
        path = Path(dirs[sys.platform]).expanduser()
        config = ConfigParser.ConfigParser()
        config.read(path / u"profiles.ini")
        if len(config.sections()) == 2:
            profile = config[config.sections()[1]]
            ans = path / profile[u"Path"]
            #if args.verbose:
            #    print("Using profile:", ans, file=sys.stderr)
            return ans
        else:
            print >>sys.stderr, u"More than one profile exists"
            #if args.verbose:
            #    print("There is more than one profile", file=sys.stderr)
    #elif args.verbose:
    #    print(
    #        "Automatic profile selection not supported for platform",
    #        sys.platform,
    #        file=sys.stderr,
    #    )


def askpass(directory):
    password = u""
    while True:
        try:
            key = getKey(directory, password)
        except WrongPassword:
            password = getpass(u"Firefox Master Password:")
        else:
            break
    return key


def main_export(args):
    try:
        key = askpass(args)
    except NoDatabase:
        # if the database is empty, we are done!
        return
    jsonLogins = getJsonLogins(args)
    logins = exportLogins(key, jsonLogins)
    writer = csv.writer(open(u"firefox.csv", u"w"))
    writer.writerow([u"URL", u"Username", u"Password"])
    writer.writerows(logins)


def makeParser(required_dir):
    if __name__ == u"__main__":
        parser = argparse.ArgumentParser(
            prog=u"ffpass",
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        subparsers = parser.add_subparsers(dest=u"mode")
        subparsers.required = True

        parser_export = subparsers.add_parser(
            u"export", description=u"outputs a CSV with header `url,username,password`"
        )

        for sub in subparsers.choices.values():
            sub.add_argument(
                u"-d",
                u"--directory",
                u"--dir",
                type=Path,
                required=required_dir,
                default=None,
                help=u"Firefox profile directory",
            )
            sub.add_argument(u"-v", u"--verbose", action=u"store_true")

        #parser_export.set_defaults(func=main_export)
        main_export(guessDir())
        return parser
    else:
        main_export(guessDir())

def main():
    global args
    args = makeParser(False).parse_args()
    guessed_dir = guessDir()
    if args.directory is None:
        if guessed_dir is None:
            args = makeParser(True).parse_args()
        else:
            args.directory = guessed_dir
    args.directory = args.directory.expanduser()
    try:
        print
    except NoDatabase:
        print >>sys.stderr, u"Firefox password database is empty. Please create it from Firefox."

if __name__ == u"__main__":
    main()