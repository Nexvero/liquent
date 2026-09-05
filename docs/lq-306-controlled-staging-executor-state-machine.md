# LQ-306 — Controlled Staging Executor State Machine

## Ergebnis

LQ-306 implementiert die kontrollierte, infrastrukturseitig injizierte
State-Machine des LQ-305-Staging-Executors.

Sie lädt genau eine owner-only Run-Autorisierung, ruft die 29 Gates in fester
Reihenfolge höchstens einmal auf und schreibt einen atomaren
LQ-304-kompatiblen Evidence-Datensatz.

Der Slice implementiert noch keinen Docker-/PostgreSQL-Adapter und startet
deshalb keine externe Stagingoperation.

## Autorisierung

Die geschlossene JSON-Datei bindet Run-ID, staging, Source-Commit, immutable
Image-Digest, Compose-SHA-256, aktuellen Migration-Head, Executor,
unterschiedlichen Autorisierer und ein aktuelles UTC-Zeitfenster.

Die Datei verwendet die bestehende owner-only Grenze ohne Symlink, Hardlink,
breite Modi, fremden Owner oder Environmentfallback.

Jede beschädigte, abgelaufene, zukünftige, Production- oder Mutable-Tag-
Autorisierung endet detailfrei als
`research_worker_staging_executor_unavailable` vor einem Phaseaufruf.

## Injizierte Phasengrenze

`StagingPhaseRunner` erhält ausschließlich den festen Phasennamen und die
validierte Autorisierung.

Ein Phaseergebnis ist exakt `passed`, `failed` oder `unavailable`. Ausgeführte
Ergebnisse verlangen opake Referenz und lowercase SHA-256; `unavailable`
verlangt beide Felder `None`.

Die State-Machine kennt keine Dockercommands, DSN, Hostpfade, SQL-Abfragen,
Jobidentitäten oder Artifactinhalte.

## Monotone Ausführung

Alle 29 LQ-303-Gates sind als unveränderliches geordnetes Tupel implementiert.

Nur `passed` erlaubt den nächsten Aufruf. Das erste `failed`, explizite
`unavailable`, ungültige Ergebnis oder jede Exception stoppt weitere
Phaseaufrufe.

Alle nicht erreichten Gates werden deterministisch mit `unavailable` und
leeren Nachweisfeldern ergänzt. Es gibt keinen Retry, Sprung, Parallelpfad oder
nachträgliches Auffüllen durch Annahmen.

Private Runner-Exceptions und Rückgabedetails verlassen die Grenze nicht.

## Evidence-Datei

Das Ziel muss ein absolutes, leeres, aktueller-Owner-besessenes Verzeichnis
ohne Group-/World-Rechte sein.

Die State-Machine erzeugt eine neue zufällige temporäre Datei mit Modus 0600,
schreibt kanonisches JSON, fsynct Datei und Verzeichnis und verlinkt danach
atomar auf `<run-id>.json`.

Ein bestehendes Ziel oder anderes Verzeichnisobjekt wird niemals ersetzt,
gelöscht oder verändert.

Die Datei enthält die gebundene Autorisierung, Beobachtungs-/Reviewzeit,
getrennte Executor-/Autorisiereridentitäten und exakt alle Gateergebnisse.

## Entscheidungstrennung

Die Executor-State-Machine importiert oder ruft den LQ-304-Verifier nicht auf
und gibt keine Readinessentscheidung zurück.

Tests reichen die erzeugte Datei separat an LQ-304 weiter, um
Schema-Kompatibilität und die erwartete unabhängige Abbildung auf approved,
rejected oder unavailable zu beweisen.

Ein vollständig `passed`-Datensatz in Tests ist keine reale Stagingfreigabe,
weil der injizierte Test-Runner keine externe Evidence behauptet.

## Nichtziele

Keine Console CLI, Docker-/Compose-Ausführung, Imageprüfung,
PostgreSQL-Verbindung, Migration, Control-Plane-Anfrage, Permissionmutation,
Artifactprüfung oder Signalübertragung wird in LQ-306 implementiert.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Produktwiringänderung.

## Nächster Slice

LQ-307 sollte den lokalen, owner-kontrollierten Prozessadapter definieren, der
die festen Phasen auf sichere Argumentlisten und eine geschlossene Umgebung
abbildet. Reale Stagingausführung bleibt weiterhin ausdrücklich autorisiert und
separat.
