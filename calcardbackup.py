#!/usr/bin/python3
"""
# Backup der Nextcloud Kalender
#
# rg, ab 2024-11-12
#
Erläuterungen:
Die Kalender-Ordner sind WebDAV Ordner, jeder Kalender ist ein eigener Ordner mit den einzelnen Terminen
als separate *.ics-Dateien
Diese werden zue einer Datei vereinigt mit dem Kalender-Nmen als ics-Datei in einem ordner im 'save_dir'
mit Datum und Uhrzeit der Sicherung als Namen.
WebDAV wird mit dem Programm 'cadaver' unter Linux angezapt, das einige eigenheiten hat:
- es braucht im aktuellen Ordner eien '.netrc'-datei, die die URL, und das Login enthält
- dazu braucht es eine 'cadaverrc'-Datei, in der die durchzuführnden Aufträge enthält.

lokale Ordner:
    startpath   der Ordner, in dem das Programm gestartet wurde
    userhome    Home-Dir des Users (= ~)
    save_dir    darin wird der Ordner der Sicherung erzeugt und gefüllt
    temp_dir    darin werden die ics- und vcf-Dateien aus den WebDav-Ordner gespeichert,
                um dann im save_dir zusammengefasst zu werden
WebDav Ordner
    BASEURL     Basis-Ordner für WebDAV Kalender & Adressbücher
                (z.B. https://my.nextcloud.de/remote.php/dav)
                Die richtige Kalender-Adresse leitet sich davon ab!

Notwendige Parametrisierung:
Parameter können über eine .env-Datei im StartOrdner hergestellt werden

Inhalte:
---------------------------------------------------------------------
BASEURL="https://my.nextcloud.de/remote.php/dav"
CALBASEURL="https://my.nextcloud.de/remote.php/dav/calendars/<myuser>"
CARDBASEURL="https://my.nextcloud.de/remote.php/dav/addressbooks/users/<myuser>/kontakte/"
TEMPDIR="/myuser/calcard/tmp/"
SAVEDIR="/myuser/calcard"
USER="myuser"
PASSWORD="my_wonderfull_password"
FILTER="ics-importiert"
---------------------------------------------------------------------

VERSIONEN:
2024-11-16      0.2 Verallgemeinerung der ersten funktionsfähigen Version
2024-11-17      0.3 Feinschliff
2025-01-24      0.4 Die .env Datei verallgemeinert # Aufräumen der Sicherungen eingefügt

"""

# test = True
test = False

from subprocess import Popen, PIPE, TimeoutExpired, run
from time import sleep
import glob
import os
import sys
import shutil
from pathlib import Path

# from dotenv import load_dotenv
from dotenv import dotenv_values
import datetime

envDatei = None

VERSION = "0.4"

# alt V 0.3
# load_dotenv()
# baseurl = os.getenv("BASEURL")
# temp_dir = os.getenv("TEMPDIR")
# save_dir = os.getenv("SAVEDIR")
# user_name = os.getenv("USER")
# passw = os.getenv("PASSWORD")
# filter_cal = os.getenv("FILTER")

# neu
config = dotenv_values(".env.rg")
baseurl = config["BASEURL"]
temp_dir = config["TEMPDIR"]
save_dir = config["SAVEDIR"]
user_name = config["USER"]
passw = config["PASSWORD"]
filter_cal = config["FILTER"]

calbaseurl = baseurl + "/calendars/" + user_name
cardbaseurl = baseurl + "/addressbooks/users/" + user_name + "/contacts"

if test:
    print(f"{baseurl=}")
    print(f"{temp_dir=}")
    print(f"{save_dir=}")
    print(f"{user_name=}")
    print(f"{calbaseurl=}")
    print(f"{cardbaseurl=}")

userhome = Path.home()
startpath = os.getcwd()
curr_dir = startpath

cadaverrc_name = os.path.join(userhome, ".cadaverrc")
netrc_name = os.path.join(userhome, ".netrc")

netrc = (
    f"machine {baseurl}",
    "default",
    f'login "{user_name}"',
    f'password "{passw}"',
)

readlstrc = (
    "open {url}",
    "ls",
    "exit",
)

getcalrc = ("open {url}", f"mget *.ics", "exit")

getcardrc = ("open {url}", f"mget *.vcf", "exit")


def rc_schreiben(url, zeilen: str, name=None):
    global cadaverrc_name, netrc_name, curr_dir
    if name is None:
        name = cadaverrc_name
    with open(name, mode="w") as f:
        for zle in zeilen:
            if "{url}" in zle:
                zle = zle.replace("{url}", f"{url}")
            print(zle, file=f)


def run_cadaver(url: str) -> list:
    if url is None:
        return (None, None)
    p = Popen(
        ["/usr/bin/cadaver", url],
        shell=True,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        text=True,
    )
    out, err = p.communicate()
    return (out, err)


def zusammenfassen(kname: str, cal=True):
    # fasst die Termine in einer einzigen Datei zusammen
    # kname ist der Name der Ausgabedatei
    # cal = True für Kalender, cal=False für Adressen
    global temp_dir, save_dir

    if cal:
        ext = "*.ics"
    else:
        ext = "*.vcf"
    if test:
        print(f"Erzeuge Ausgabe {kname=}")
    with open(kname, "w") as nach:  # open der Ausgabe-Datei
        suchmuster = temp_dir + ext
        if test:
            print(f"Zusammenfassen, suche nach {suchmuster=}")
        for datei in glob.glob(suchmuster):
            if test:
                print(f"Verarbeite Eingabe {datei=}")
            with open(datei, "r") as von:  # open der Download-Datei
                for line in von.readlines():
                    print(line, file=nach, end="")
            print("\n", file=nach)


def chgDir(dirName: str):
    # Neuanlage der .netrc und ggf. Verzeichniswechsel
    global curr_dir

    if dirName != curr_dir:
        os.chdir(dirName)
    curr_dir = dirName
    rc_schreiben(baseurl, netrc, name=netrc_name)  # initiales anlegen der .netrc Datei


# ------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------
# Schritt 0: Vorbereitungen; tmp & ArbeitsDir anlegen; tmp ggf. löschen

if len(sys.argv) > 1:
    envDatei = sys.argv[1]
else:  # einen Ausweg schaffen, wenn kein Parm angegeben wurde
    envDatei = ".env"

if not os.path.exists(envDatei):
    envDatei = None

if not envDatei:
    print(
        "Init-Fehler: Bitte eine '.env'-Datei anlegen (-> Doku) und deren\nName als Parameter übergeben!"
    )
    exit(1)

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
Path(temp_dir).mkdir(parents=True, exist_ok=True)

zeitpunkt = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
chgDir(temp_dir)
# print(f"{curr_dir=}")

head = (
    f"\n==CalCardBackup============================== Version {VERSION} - RüGi ======="
)
headlen = len(head)
print(head)

# Schritt 1: eine Liste der Kalender besorgen
print("--------- Kalender-Backup-----------------------")

rc_schreiben(calbaseurl, readlstrc)
out, err = run_cadaver(calbaseurl)
if out is None:
    print(f"FEHLER!: run_cadaver liefert leere Ausgabe!")
    exit(3)
ics = out.split("\n")
if test:
    print(out)

kalender = []
for z in ics:
    if z.startswith("Coll:"):
        sp = z.split()
        kalender.append(sp[1])


# Schritt 2: jeden Kalender downloaden und zusammenfassen
chgDir(temp_dir)

# jede Sicherung bekommt einen eigenen Ordner mit Zeitstempel, in dem die ics-Dateien liegen
cal_dir = save_dir + "/" + zeitpunkt
Path(cal_dir).mkdir(parents=True, exist_ok=True)
if test:
    print(f"Backup-Dir {cal_dir=} erzeugt!")

for cal in kalender:
    print(f"Kalender [{cal}] ...", end="", flush=True)
    if filter_cal in cal:
        url = calbaseurl + "/" + cal
        rc_schreiben(url, getcalrc)
        out, err = run_cadaver(url)
        zusammenfassen(cal_dir + "/" + cal + ".ics")
        # aufräumen
        for file in glob.glob(temp_dir + "*"):
            os.remove(file)
            pass
        print(" gesichert!")
    else:
        print(" übersprungen!")

print("\n--------- Adressen-Backup-----------------------")

file = cal_dir + "/AdressBook.vcf"
print(f"Kalender [AdressBook.vcf] ...", end="", flush=True)
rc_schreiben(cardbaseurl, getcardrc)
out, err = run_cadaver(cardbaseurl)
zusammenfassen(file, cal=False)
print(" OK!")

# aufräumen
if not test:
    for file in glob.glob(temp_dir + "*"):
        os.remove(file)
        pass

# Abschlussarbeiten

os.chdir(startpath)
curr_dir = startpath
shutil.rmtree(temp_dir)

if os.path.exists(cadaverrc_name):
    if not test:
        os.remove(cadaverrc_name)

if os.path.exists(netrc_name):
    if not test:
        os.remove(netrc_name)

endline = "== Done " + "=" * (headlen - 8)
print(endline)
