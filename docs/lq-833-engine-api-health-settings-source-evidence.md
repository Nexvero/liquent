# LQ-833 — Engine API Health Settings Source Evidence

## Mappingevidenz

Die exakte Gruppe erzeugt die vollständige Authority. Jeder der neun fehlenden
Schlüssel sowie Zusatzschlüssel, führende Null, Vorzeichen, boolescher Text,
Fließkomma und nichtkanonischer Pfad scheitern.

## Dateievidenz

Nur Modus 0600 wird akzeptiert. Symlink und Hardlink scheitern. Fehlende,
zusätzliche, doppelte und kommentierte Zeilen sowie Mehrfachgleichheit werden
abgelehnt.

## Isolierung

Ein gleichnamiger Process-Environment-Wert beeinflusst die private Datei nicht.
Die neun Healthwerte bleiben von den 21 Proxysettings getrennt.

## Fähigkeitsgrenze

Loader und Parser erzeugen ausschließlich ein inertes Authorityobjekt und öffnen
keinen Healthlistener.
