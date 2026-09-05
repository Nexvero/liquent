# LQ-2640 — PostgreSQL 18 Volume and Bootstrap Failure Stop

## Beobachtung

Der zweite bestätigte Bootstrap-Versuch erreichte PostgreSQL und endete am
Health-Gate. Das digestgebundene offizielle PostgreSQL-18-Image verweigert den
historischen Mountpunkt `/var/lib/postgresql/data`: Ab Version 18 erwartet es
den gemeinsamen Root `/var/lib/postgresql`, unter dem versionsbezogene
Datenverzeichnisse angelegt werden.

Der Fehler trat vor Migration, Control Plane und Edge-Handoff auf. Host-nginx
blieb aktiv. Der restartende PostgreSQL-Container wurde gestoppt; das in diesem
Versuch neu erzeugte benannte Volume war danach vollständig leer. Es wurde
kein Datenbestand erzeugt oder entfernt.

## Korrektur

Basis-Compose mountet `liquent_postgres_data` nun an
`/var/lib/postgresql`. Eine Regression verbietet gleichzeitig den alten
Unterpfad. Zusätzlich stoppt der Bootstrap-Fehlerpfad neben der Control Plane
auch PostgreSQL, damit ein fehlgeschlagener Initiallauf keinen restartenden
Datenbankcontainer zurücklässt.

## Grenze

Der Slice löscht weder Container noch Volume und führt keine Migration aus.
Die vier bereits angelegten, eigenschaftsgeprüften leeren Netzwerke dürfen als
idempotente Infrastruktur bestehen bleiben. Ein erneuter Bootstrap benötigt
wieder einen gemergten Reviewstand, grüne CI, Artefaktgleichheit und die
bestehende ausdrückliche `INITIALIZE-STAGING`-Bestätigung.
