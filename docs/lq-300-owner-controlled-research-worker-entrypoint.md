# LQ-300 — Owner-controlled Research Worker Entry Point

## Ergebnis

LQ-300 implementiert den installierbaren Command `liquent-research-worker`.

Der Entry-Point verlangt zwei explizite absolute Argumente: die owner-only
LQ-299-Processkonfiguration und eine getrennte owner-only Datenbank-URL-Datei.

Er prüft alle lokalen Grenzen und die exakte Datenbank-Readiness, komponiert den
LQ-297-Pfad, installiert begrenzte Stophandler und startet erst danach den
LQ-298-Loop.

## Datenbank-Secret

`OwnerOnlyResearchWorkerDatabaseUrlSource` verwendet dieselbe owner-only
Dateigrenze wie LQ-299: regulär, aktueller Owner, Linkcount eins, `0400` oder
`0600`, begrenzte Größe und kein Symlink.

Genau ein abschließender Newline darf entfernt werden. Zulässig ist nur eine
whitespace-freie `postgresql+psycopg://`-URL.

URL, Credentials und Pfad erscheinen weder im `repr` noch in der detailfreien
Operator-Exception.

Es gibt keinen Environment-, CLI-Wert-, SQLite- oder Default-DSN-Fallback.

## Fail-fast Reihenfolge

Der Entry-Point führt kontrolliert aus:

1. Processkonfiguration laden und validieren;
2. stabile Worker-ID aus ihrer separaten Datei lesen;
3. Datenbank-URL aus der separaten Secretdatei lesen;
4. extern besessene Engine bauen;
5. Verbindung und exakten Migration-Head prüfen;
6. geschlossenen lokalen CSV-Resolver aufbauen;
7. owner-kontrollierten LQ-296-ArtifactStore aufbauen;
8. vollständigen LQ-297-Einzeljobpfad komponieren;
9. LQ-298-Loop mit sicherem Jitter starten.

Bei fehlender Datenbank oder Revision-Mismatch entstehen weder Composition
noch Claim, Resolver-, Artifact- oder Loopzugriff.

Der Entry-Point führt keine Migration aus und erzeugt keine Konfigurations-,
Worker-ID-, Secret-, Dataset- oder Artifactverzeichnisse.

## Identitätsmaterial

Job-, Revision- und Claimidentitäten werden erst bei tatsächlichem Storebedarf
über getrennte kryptografisch sichere Generatoraufrufe erzeugt.

Composition ruft diese Generatoren nicht auf. Die stabile Worker-ID stammt
ausschließlich aus der owner-kontrollierten Datei und wird nicht rotiert.

## Signal- und Stopgrenze

SIGTERM und SIGINT setzen ausschließlich das interne Stop-Event.

Die Handler führen keine Datenbank-, Artifact-, Logging-, Wait- oder
Finalizeroperation aus. Unterbrechbares Idle-/Backoff-Warten endet sofort; ein
laufender synchroner Job darf seinen claimgebundenen Abschluss versuchen.

Nach Loopende werden vorherige Signalhandler wiederhergestellt.

## Ressourcenbesitz

Die processweite Engine wird genau einmal erzeugt und im `finally` disposed,
auch bei Readiness-, Composition-, Loop- oder Stopfehlern.

Resolver und lokaler ArtifactStore besitzen keine offen gehaltenen externen
Clients. Der Entry-Point startet keinen zweiten Thread oder Kindprozess.

## Exit- und Fehlergrenze

Normaler Stop liefert Exitcode `0`. Konfigurations-, Secret-, Readiness-,
Composition- und Runtimefehler werden als detailfreie
`research_worker_operator_unavailable` vereinheitlicht; `main` liefert dann
Exitcode `1`.

Es werden keine Exceptions, DSNs, Pfade, Job-, Claim-, User- oder
Workspaceinformationen auf stdout oder stderr geschrieben.

## Packaging und Compose

Der neue Console Entry Point erhöht die geprüfte Anzahl auf 21 und die
Operatormodulanzahl auf 20. Das Release-Bundle-Gate wurde entsprechend
aktualisiert.

Compose bleibt absichtlich nicht runnable: Der vorhandene Service reicht die
beiden erforderlichen owner-only Dateien und Commandargumente noch nicht ein.
Nur Statuskommentare und README benennen jetzt diesen tatsächlichen Restblocker.

Schema und Migration-Head bleiben `20260819_0027`.

Die vollständige lokale Suite besteht mit 3392 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-301 sollte das kontrollierte Compose-/Secret-Wiring für Config,
Datenbank-URL, Worker-ID, Researchdaten und Artifactvolume ergänzen sowie
Readiness und Grace Period gegen den Entry-Point auditieren.

Danach folgt der verpflichtende PostgreSQL-Mehrprozess- und End-to-End-Nachweis.
