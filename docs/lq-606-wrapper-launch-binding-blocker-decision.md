# LQ-606 — Wrapper Launch Binding Blocker Decision

## Ergebnis

LQ-606 schließt LQ-603 bis LQ-606 als korrigierenden Loader-
Implementierbarkeitsstrang ab.

Der aktuelle LQ-600/LQ-601-Bestand wird nicht unmittelbar als
Production-Wrapperinput aktiviert.

## Bestätigte Blocker

Host-owner `0600` und Containeruser `65532:65532` besitzen keine gemeinsame
Lesbarkeitsentscheidung.

Die erst nach Create bekannte Runtime-ID verhindert einen vollständigen
Pre-create-Digestanchor des heutigen Dokuments.

Der heutige gesamte read-write Control-Mount ist keine unveränderliche
Launchdocumentgrenze.

## Korrigiertes Ziel

Ein neues versioniertes Launchdokument enthält ausschließlich vor Create
bestimmbare Werte.

Document-ID und SHA-256 werden in der exakten Create-Labelmenge verankert.

Die Runtime-ID bleibt separat durch Parent, Engine und Persistenz gebunden.

Das Launchdokument wird als einzelne read-only Datei gemountet; dynamische
Control-Artefakte verwenden einen getrennten read-write Mount.

## Sichere Reihenfolge

1. Launchdocumenttyp und Version-1-Codec getrennt implementieren;
2. numerische Owner-/Reader-UID-/GID-Policy implementieren;
3. atomare Launchfile-Publikation vor Create belegen;
4. Engine-Request, Labels und Runtimebeobachtung um Document-ID/Digest
   erweitert binden;
5. getrennte read-only/read-write Mountprofile implementieren;
6. Kindprozessloader mit unabhängiger Digest- und Selbstbindung implementieren;
7. erst danach direkte Ready-Publikation des Kinds öffnen.

## Bewahrter Bestand

Der heutige Jobdocumentcodec und atomare Adapter bleiben für Parentkorrelation
und als Grundlage der neuen Typen nutzbar.

Der LQ-591-Client bleibt geschlossen, benötigt aber vor Production eine
explizite versionierte Label-/Mount-Erweiterung.

Keine bestehende Runtimewirkung wird in diesem Audit verändert.

## Verifikation

Source-basierte Prüfungen müssen Dateimodus, Containeruser, fehlenden
Digestlabelbestand, Runtime-ID-Reihenfolge und read-write Mount direkt belegen.

Der fokussierte Loader-, Jobdokument-, Dockerclient-, Ownership- und
Architekturlauf besteht mit 46 Tests unter strikter
DeprecationWarning-Grenze.

Die vollständige normale Regression besteht mit 5184 Tests und einem
erwarteten Skip; 107 PostgreSQL-Tests bleiben mangels Persistenzänderung
bewusst abgewählt.

## Keine Productionwirkung

LQ-606 ergänzt keine Runtimequelle, Migration, Settings-, Appfactory-, Compose-
oder Deploymentänderung.

Es führt keinen Dockerzugriff, Commit, Push, Release oder Deployment aus.

Head bleibt `20260826_0042` mit 42 linearen Migrationen.

## Nächster Strang

LQ-607 implementiert das getrennte vor Create bestimmbare Launchdocument und
seinen kanonischen Codec, noch ohne Engine- oder Mountänderung.
