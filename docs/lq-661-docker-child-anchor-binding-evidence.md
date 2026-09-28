# LQ-661 — Docker Child Anchor Binding Evidence

## Ergebnis

Der lokale Docker-HTTP-Client bindet den kanonischen Kindanker konstruktiv an
Create und Inspect.

## Create

Nach exakter Prüfung der sechs Supervisorlabels, des Images, Profils und der
Sicherheitskonfiguration konstruiert der Client die vollständige Erwartung.

Die process-eigene Writer- oder Recovery-Commandfolge wird unverändert um den
kanonischen Anker ergänzt. Requests können weder Command noch Ankerargumente
liefern.

## Inspect und Adoption

Inspect rekonstruiert den erwarteten Entrypoint aus Labels, Image und Profil und
verlangt bytegenau dieselbe Argumentliste in der Daemonbeobachtung.

Fehlende, zusätzliche oder divergente Argumente verhindern Adoption.

Die Engine vergleicht danach weiterhin die Parent-Erwartung mit den beobachteten
Labels. Ein anderer strukturell gültiger Launchanker erzeugt keinen zweiten
Container.

## Evidenz

Fokussierte Tests belegen Roundtrip, feste Länge und Reihenfolge,
Reject-on-extra, Reject-on-missing, Digestvalidierung, materialisiertes Create,
Inspect-Rekonstruktion und unveränderte Reconciliationkonflikte.

Kein Dockerdaemon, Netzwerk, Datenbankzugriff oder Prozessstart ist erforderlich.
