# Projekt CalCard

## Ziele

Es war das Ziel, die Kalender- und Adress-Daten aus Nextcloud möglichst transparent zu sichern.
Ich entschied mich für eine Klartext Sicherung:
jeder Kalender und das Adressbuch sind je eine Text-Datei.
Jede Sicherung erzeugt eine Unterordner mit Datum und Zeit, der diese Dateien enthält.
(was noch fehlt ist ein Aufräumen alter Sicherungen...)


## Der Anfang: calcardbackup.py

2024 entstand `calcardbackup.py`. Es wurde mit Hilfe des Linux Dienstprogramms `cadaver` verfasst. 
`cadaver` ist als externes Programm nur durch passende rc-Files zu steuern und recht umständlich zu bedienen. Aber es funktioniert nach einigen Experimenten doch zuverlässig  bis 10.2026. 
`calcardbackup.py` wird durch die env-Datei `.env.rg` gesteuert, die im Quellcode fest voorgegeben ist. 
Diese env-Datei enthält einen Filter-Begriff, so dass nur die Kalender gesichert werden, die diesen Teil-String enthalten.

Dann stieß ich auf: `webdavclient3`...


## Zweite Auflage: nccalcardbackup.py

Dieses Programm kommt ganz ohne externe Programm-Aufrufe aus und stützt sich auf das Modul `webdavclient3`.
Damit ist die Programmierung wesentlich einfacher und übersichtlicher.
Dadurch, dass die steuernde env-Datei per Kommandozeilen-Parameter übergeben werden muss, kann `nccalcardbackup`  auch für verschiedene User eingesetzt werden.
Dazu wurde der Filter dahingehend geändert, das er eine negative Filterwirkung hat. 
Der Filter SKIPCALFILTER=... in der env-Datei enthält eine Komma-separierte Liste von Kalender-Namen, die nicht gesichert werden sollen.
z.B. "SKIPCALFILTER=Persönlich,all-generated--deck--board-1".

### Aufruf:
    ``` 
    python3 nccalcardbackup.py env-datei [test={true/false}]
    ```
in einem passenden Environment.

Die Angabe der env-Datei ist obligatorisch!
Mit dem Kommandozeilen-Parameter "test={true/false}" kann ein Test-Modus eingeschaltet werden, in dem eine Reihe von Debug-Nachrichten ausgegeben werden.
Damit läßt sich auch in einem ersten Testlauf feststellen, welche Kalender mit welchen Namen (und URL) überhaupt verfügbar sind. 

### Zum Environment:

Das Envirnment muss die Module `dotenv` und `webdavclient3` enthalten.

rg, 2026-10-04




