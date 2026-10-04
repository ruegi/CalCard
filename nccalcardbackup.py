#!/usr/bin/python3
"""
# Backup der Nextcloud Kalender
#
# rg, ab 2026-10-03
# aus calcardbackup.py heraus entwickelt
# Unterschied: der webdav-Zugang wird durch das Modul 'webdavclient3' ermöglicht
#
Erläuterungen:
Die Kalender-Ordner sind WebDAV Ordner, jeder Kalender ist ein eigener Ordner mit den einzelnen Terminen
als separate *.ics-Dateien
Diese werden zu einer Datei vereinigt mit dem Kalender-Nmen als ics-Datei in einem Ordner im 'save_dir'
mit Datum und Uhrzeit der Sicherung als Namen.

Notwendige Parametrisierung:
Parameter können über eine .env-Datei im StartOrdner hergestellt werden

Inhalte der env-Datei:
---------------------------------------------------------------------
HOST="https://my.nextcloud.de/"
BASEURL="https://my.nextcloud.de/remote.php/dav/"
TEMPDIR="/myuser/calcard/tmp/"
SAVEDIR="/myuser/calcard/"
USER="myuser"
PASSWORD="my_wonderfull_password"
SKIPCALFILTER="ics-importiert"
---------------------------------------------------------------------

VERSIONEN:
2026-10-03      0.1 Erste funktionsfähige Version

"""

# test = True
test = False

from webdav3.client import Client
from webdav3.exceptions import WebDavException

import glob
import os
import sys
import shutil
from pathlib import Path

from dotenv import dotenv_values
import datetime

envDatei = None

VERSION = "0.1"


def printLst(lst, header="["):
    if not header == "[":
        header = header + " ["
    print(header)
    for x in lst:
        print("  ", x)
    print("]")


def getDirInhalt(client, ordner, isDir=True):
    # gibt den Inhalt eines Odrdners als dict-Liste zurück
    # Parameter:
    # client:   der WebDavClient
    # ordner:   der zu durchsuchende Ordner
    # optional
    # isDir=True/False  je nachdem, ob ordner oder Dateien gesucht werden
    global test
    global relbaseurl

    liste = []
    if ordner.startswith("/"):
        mybaseurl = ordner[1:]
    else:
        mybaseurl = ordner
    try:
        l1 = client.list(ordner, get_info=True)
    except WebDavException as err:
        if test:
            print(f"WebDAV Error: {err}")
        return liste
    for inh in l1:
        if inh["name"] is None:
            continue
        pfad_prefix = relbaseurl + mybaseurl
        relpfad = inh["path"].removeprefix(pfad_prefix)
        if test:
            print(f"{pfad_prefix=}, {relpfad=}")
        if "app-generated" in relpfad:
            continue
        liste.append({"name": inh["name"], "url": relpfad, "path": inh["path"]})
    return liste


def inhalte_sammeln(client, ordner, maske="*"):
    # die einzelnen Inhalte der Adressen oder der Termine
    # liegen als separate Dateien in einem Unterordner.
    # Diese Dateien werden hier in eine Temp-Ordner heruntergeladen und
    # ihre Inhalte dann in einem einzigen Text-String gesammelt zurück
    # gegeben
    # Parms:
    #   client: die WebDav Client
    #   ordner: der zu lesende Unterordner
    #   maske=...: ein String der zu berücksichtigenden Datei_Endungen
    #               (z.B. maske="*.ics" für Kalender; default="*")
    global temp_dir, save_dir

    mytemp = temp_dir + "sammel/"
    if os.path.exists(mytemp):
        shutil.rmtree(mytemp)
    Path(mytemp).mkdir(parents=True, exist_ok=True)

    client.webdav.disable_check = (
        True  # siehe https://github.com/ezhov-evgeny/webdav-client-python-3/issues/114
    )
    inhalt = ""
    try:
        client.download_sync(remote_path=ordner, local_path=mytemp)
    except WebDavException as err:
        if test:
            print(f"WebDAV Download Error: {err}")
        return inhalt

    if maske == "":
        maske = "*"

    dateien = glob.glob(mytemp + maske)
    fst = True
    for dat in dateien:
        buf = Path(dat).read_text(encoding="utf8")
        if fst:
            inhalt = buf
            fst = False
        else:
            inhalt = inhalt + "\n\n" + buf

    if os.path.exists(mytemp):
        shutil.rmtree(mytemp)
    return inhalt


def formatiere_zeile(fmt, l=50):
    # fügt 'n' Punkte zu fmt hinzu, damit die Zeile 'l' Zeichen lang ist
    x = len(fmt)
    anz = l - x - 2
    return fmt + " " + "." * anz + " "


def leseDictWert(dict: dict, arg: str, default=""):
    # liest aus dem Dictionary dict den Wert mit dem Argument arg und gibt ihn zurück
    # kann es den nicht finden, wird der default-Wert zurückgegeben.
    # Ist der Default-Wert leer, wird eine Fehlermeldung erzeugt un das Programm stoppt
    try:
        wert = dict[arg]
    except:
        if default:
            wert = default
        else:
            print(f"FEHLER: In der Env-Datei fehlt ein Wert für [{arg}]!")
            help()
            exit(3)
    return wert


def help():
    print("Aufruf:")
    print("nccalcardbackup.py env-Datei [test=True]")
    print("Die env-Datei ist zwingend erforderlich!")
    print("test={False/True} ist optional, default=False")
    print("Aufbau der env-Datei:")
    print("""BASEURL="https://my.nextcloud.de/remote.php/dav/"
CALBASEURL="https://my.nextcloud.de/remote.php/dav/calendars/<myuser>/"
CARDBASEURL="https://my.nextcloud.de/remote.php/dav/addressbooks/users/<myuser>/kontakte/"
TEMPDIR="/myuser/calcard/tmp/"
SAVEDIR="/myuser/calcard/"
USER="myuser"
PASSWORD="my_wonderfull_password"
SKIPCALFILTER="ics-importiert,Persönlich"  
""")
    print("Bedeutungen:")
    print("BASEURL: Die URL beim WebDav-Login")
    print("CALBASEURL: Die URL der Kalender")
    print("CARDBASEURL: Die URL der Adressen")
    print("TEMPDIR: ein Arbeitsverzeichnis")
    print(
        "SAVEDIR: ein Ordner, in dem die Sicherungen unter einem Zeistempel-Ordner abgelegt werden"
    )
    print("USER: der Benutzer für das WebDav-Login")
    print("PASSWORD: das Kennwort des Benutze für das WebDav-Login")
    print(
        "SKIPCALFILTER: eine Komma separierte Liste von Kalender-Namen, die übersprungen werden sollen"
    )


# ------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------
# Schritt 0: Vorbereitungen; tmp & ArbeitsDir anlegen; tmp ggf. löschen
head = (
    f"\n== NcCalCardBackup ========================== Version {VERSION} - RüGi ======="
)
headlen = len(head)
print(head)
envDatei = ".env.rg"  # default für den Anfang

l = len(sys.argv)
if l > 3:
    print("Problem: Mehr als 2 Parameter sind nicht vorgesehen!")
    print(help())
    exit(0)
elif l > 1:
    for i in range(1, len(sys.argv)):
        parm = sys.argv[i]
        p = parm.lower()
        if p.startswith("test="):
            if p[5:] == "true":
                test = True
        else:
            envDatei = sys.argv[i]

else:  # einen Ausweg schaffen, wenn kein Parm angegeben wurde
    envDatei = ".env.rg"

if not os.path.exists(envDatei):
    print(
        "Init-Fehler: Bitte eine '.env'-Datei anlegen (-> Doku) und deren\nName als Parameter übergeben!"
    )
    exit(1)
if test:
    print(f"{envDatei=}")
config = dotenv_values(envDatei)
host = leseDictWert(config, "HOST")
baseurl = leseDictWert(config, "BASEURL")
temp_dir = leseDictWert(config, "TEMPDIR")
save_dir = leseDictWert(config, "SAVEDIR", default="~/nccalcardbackup")
user_name = leseDictWert(config, "USER")
passw = leseDictWert(config, "PASSWORD")
skipFilter = leseDictWert(config, "SKIPCALFILTER").split(",")

relbaseurl = baseurl.removeprefix(host)
calbaseurl = "/calendars/" + user_name + "/"
cardbaseurl = "/addressbooks/users/" + user_name + "/contacts/"

zeitpunkt = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
save_dir = save_dir + zeitpunkt + "/"

if test:
    print(f"{host=}")
    print(f"{baseurl=}")
    print(f"{relbaseurl=}")
    print(f"{temp_dir=}")
    print(f"{save_dir=}")
    print(f"{user_name=}")
    print(f"{calbaseurl=}")
    print(f"{cardbaseurl=}")
    print(f"{skipFilter=}")
userhome = Path.home()
startpath = os.getcwd()
curr_dir = startpath

if os.path.exists(temp_dir):
    shutil.rmtree(temp_dir)
Path(temp_dir).mkdir(parents=True, exist_ok=True)

Path(save_dir).mkdir(parents=True, exist_ok=True)

options = {
    "webdav_hostname": baseurl,
    "webdav_login": user_name,
    "webdav_password": passw,
}
client = Client(options)

print("--------- Kalender-Backup ------------------------------------------")

# Schritt 1: eine Liste der Kalender besorgen
kal_liste = getDirInhalt(client, ordner=calbaseurl, isDir=True)
if test:
    printLst(kal_liste)

# Schritt 2: jeden Kalender sichern
for kal_dic in kal_liste:
    # Filter anwenden
    fmt = f"Bearbeite Kalender [{kal_dic["name"]}] "
    print(formatiere_zeile(fmt, l=55), end="", flush=True)
    if kal_dic["name"] in skipFilter:
        print(f"skipped.")
        continue
    kal_datei = save_dir + kal_dic["url"][:-1] + ".ics"

    kalpfad = kal_dic["path"].removeprefix(relbaseurl)
    kal = inhalte_sammeln(client, kalpfad, maske="*.ics")
    if kal > "":
        with open(kal_datei, "w") as kal_f:
            print(kal, file=kal_f)
        print("gesichert!")
    else:
        print("NICHT erfolgreich :-(")

print("\n--------- Adressen-Backup ------------------------------------------")

fmt = f"Bearbeite [AdressBook.vcf] "
print(formatiere_zeile(fmt, l=55), end="", flush=True)

adr_datei = save_dir + "adressen.vcf"

# adrpfad = kal_dic["path"].removeprefix(relbaseurl)
adrpfad = cardbaseurl
adr = inhalte_sammeln(client, adrpfad, maske="*.vcf")
if adr > "":
    with open(adr_datei, "w") as adr_f:
        print(adr, file=adr_f)
    print("gesichert!")
else:
    print("NICHT erfolgreich :-(")


# aufräumen
if not test:
    for file in glob.glob(temp_dir + "*"):
        os.remove(file)

# Abschlussarbeiten

shutil.rmtree(temp_dir)

endline = "== Done " + "=" * (headlen - 8)
print(endline)
