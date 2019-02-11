#*/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
from __future__ import absolute_import
import os
import re
import sys
import sqlite3
import csv
import json
import argparse
import binascii
import hashlib
import base64
import subprocess
from io import open

try:
    import win32crypt
except:
    pass

def get_SafeStorageKey():
    ssk_file = u"/".join(__file__.split(u"/")[:-1]) + u"/get_ssk.sh"
    ssk_cmd = subprocess.Popen([u"sh", ssk_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    ssk = ssk_cmd[0].decode(u"ascii").replace(u"\n", u"").replace(u"\"", u"")

    return ssk.encode(u"ascii")

def decrypt(encrypted_password, iv, key=None):
    hex_key = binascii.hexlify(key)
    hex_password = base64.b64encode(encrypted_password[3:])

    print (iv, hex_key, hex_password)

    dc_file = u"/".join(__file__.split(u"/")[:-1]) + u"/decrypt_pwd.sh"

    try:
        decrypted_pass = subprocess.Popen([u"sh", dc_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except Exception, e:
        decrypted_pass = e

    return decrypted_pass

def main():
    info_list = []
    path = get_path()
    if type(path) == type([]):
        profiles = {}
        for p in sorted(path):
            if not os.path.isdir(p):
                continue
            db_path = p + u"/Login Data"
            try:
                connection = sqlite3.connect(db_path)

                c = connection.cursor()
                v = c.execute(u"SELECT action_url, username_value, password_value FROM logins")
                value = v.fetchall()

                for origin_url, username, password in value:
                    if os.name == u"nt":
                        password = win32crypt.CryptUnprotectData(password, None, None, None, 0)[1]

                    if password:
                        info_list.append({
                            u"origin_url": origin_url,
                            u"username": username,
                            u"password": password
                        })
            except sqlite3.OperationalError, e:
                e = unicode(e)
                if (e == u"database is locked"):
                    print u"[*] Make sure Google Chrome is not running in the background"
                elif (e == u"no such table: logins"):
                    print u"[*] Something is wrong with the database name"
                elif (e == u"unable to open database file"):
                    print u"[*] Something is wrong with the database path"
                else:
                    print e

                sys.exit(0)

            profiles[re.search(ur"Profile \d", p).group()] = info_list

        return profiles
    else:
        try:
            connection = sqlite3.connect(path + u"Login Data")

            c = connection.cursor()
            v = c.execute(u"SELECT action_url, username_value, password_value FROM logins")
            value = v.fetchall()

            for origin_url, username, password in value:
                if os.name == u"nt":
                    password = win32crypt.CryptUnprotectData(
                        password, None, None, None, 0)[1]
                
                if password:
                    info_list.append({
                        u"origin_url": origin_url,
                        u"username": username,
                        u"password": password
                    })

        except sqlite3.OperationalError, e:
            e = unicode(e)
            if (e == u"database is locked"):
                print u"[*] Make sure Google Chrome is not running in the background"
            elif (e == u"no such table: logins"):
                print u"[*] Something wrong with the database name"
            elif (e == u"unable to open database file"):
                print u"[*] Something wrong with the database path"
            else:
                print e
            sys.exit(0)

        return info_list


def get_path():
    if os.name == u"nt":
        PathName = os.getenv(u"localappdata") + \
            u"\\Google\\Chrome\\User Data\\Default\\"
    elif os.name == u"posix":
        PathName = os.getenv(u"HOME")
        if sys.platform == u"darwin":
            if not os.path.isdir(PathName + u"/Library/Application Support/Google/Chrome/Default/"):
                #profiles = []
                #for f in os.listdir(PathName + "/Library/Application Support/Google/Chrome/"):
                #    if "Profile " in f:
                #        profiles.append(PathName + "/Library/Application Support/Google/Chrome/" + f)

                if os.path.isdir(PathName + u"/Library/Application Support/Google/Chrome/Profile 1"):
                    PathName = PathName + u"/Library/Application Support/Google/Chrome/Profile 1/"
            else:
                PathName += u"/Library/Application Support/Google/Chrome/Default/"
        else:
            PathName += u"/.config/google-chrome/Default/"

    if type(PathName) != type([]):
        if not os.path.isdir(PathName):
            sys.exit(u"[*] Google Chrome profiles do not exist")

    return PathName

def output_csv(info, export_loc=os.getcwdu(), _print=True):
    ssk = get_SafeStorageKey()

    iv = u''.join((u'20',) * 16)
    key = hashlib.pbkdf2_hmac(u'sha1', ssk, 'saltysalt', 1003)[:16]

    if type(info) == type({}):
        for p in info:
            v = info[p]
            try:
                with open(u"chrome_{}.csv".format(p.replace(u" ", u"").lower()), u"wb") as csv_file:
                    csv_file.write(u"Origin URL,Username,Password,IV,Key \n".encode(u"utf-8"))
                    for data in v:
                        sv_file.write((u"{}, {}, {}, {}, {} \n".format(data[u"origin_url"], data[u"username"], data[u"password"], iv, key).encode(u"utf-8")))

                if _print:
                    print (u"Data written to chrome_{}.csv".format(p.replace(u" ", u"").lower()))
            except EnvironmentError:
                print u"EnvironmentError: Unable to write the data!"
    else:
        try:
            with open(u"chrome.csv", u"wb") as csv_file:
                csv_file.write(u"URL,Username,Password,IV,Key \n".encode(u"utf-8"))
                for data in info:
                    csv_file.write((u"{}, {}, {}, {}, {} \n".format(data[u"origin_url"], data[u"username"], data[u"password"], iv, key).encode(u"utf-8")))
            if _print:
                print u"Data written to chrome.csv"
        except EnvironmentError:
            print u"EnvironmentError: cannot write data"

if __name__ == u"__main__":
    parser = argparse.ArgumentParser(
        description=u"Retrieve Google Chrome Passwords")
    parser.add_argument(u"-o", u"--output",
                        help=u"Output passwords to CSV format")
    parser.add_argument(
        u"-d", u"--dump", help=u"Dump passwords to stdout", action=u"store_true")

    args = parser.parse_args()
    if args.dump:
        for data in main():
            print data
    if args.output:
        output_csv(main())
    else:
        parser.print_help()