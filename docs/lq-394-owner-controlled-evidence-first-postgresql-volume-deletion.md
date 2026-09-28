# LQ-394 — Owner-controlled Evidence-first PostgreSQL Volume Deletion

## Ergebnis

LQ-394 implementiert den in LQ-393 definierten mutierenden Operator als
`liquent-disposable-postgres-volume-delete`.

Der Command entfernt höchstens einmal genau das intern abgeleitete disposable
PostgreSQL-Datenvolume.

Claim, finale Evidence und Claimfreigabe folgen einer Evidence-first-Ordnung.

## Historische Idempotenzprüfung

Der Operator lädt die exakte Löschautorisierung zunächst in ihrem historischen
gültigen Zeitkontext.

Damit kann er vorhandene finale Evidence auch nach Ablauf des ursprünglichen
Mutationsfensters sicher gegen dieselben unveränderten Eingaben prüfen.

Vor Preflight und Docker wird der finale Evidencepfad ausschließlich aus dem
SHA-256 der stabilen Volume-Deletion-ID abgeleitet.

Exakt gebundene finale Evidence liefert idempotent `volume_removed` oder führt
nur noch die ausstehende Claimfreigabe aus.

Malformed oder fremde Evidence stoppt fail-closed.

## Frischer LQ-392-Preflight

Ohne finale Evidence führt der Operator den vollständigen LQ-392-Preflight mit
der aktuellen Uhr und denselben privaten Eingabedateien erneut aus.

Nur `ready` erreicht die Claimanlage.

`rejected` und `investigation_required` werden detailarm weitergereicht, ohne
Claim oder Mutation.

Technische Nichtverfügbarkeit bleibt ohne Ergebnisobjekt.

Ein caller-gelieferter oder gespeicherter Preflightausgang wird nicht
akzeptiert.

## Exakter Claim

Der Claimpfad wird aus dem vollständigen SHA-256 der vorab autorisierten
Volume-Deletion-Claim-ID abgeleitet.

Der Claim bindet Run, Phase, Source, Image, Compose, Volume, Scope, Operation,
sämtliche Entscheidungs- und Evidencehashes sowie die getrennten Identitäten.

Er wird owner-only mit exklusiver Neuanlage erzeugt, vollständig geschrieben,
geflusht, zurückgelesen und gemeinsam mit dem privaten Evidenceverzeichnis
synchronisiert.

Ein vorhandener oder kollidierender Claim wird nicht überschrieben, ersetzt
oder nach Alter entfernt.

## Letzte Volumebindung

Nach durable Claimanlage inspiziert der Operator das exakte Volume erneut
read-only.

Name und Composeprojekt müssen weiterhin der intern abgeleiteten Runbindung
entsprechen.

Abweichung oder technische Mehrdeutigkeit stoppt mit erhaltenem Claim und ohne
Remove.

Der Operator mountet oder öffnet das Volume nicht und liest keine
PostgreSQL-Dateien.

## Einzige Mutation

Der einzige mutierende Ressourcenaufruf ist:

```text
docker volume rm <intern abgeleitetes exaktes volume>
```

Es gibt keine Forceoption, mehrere Namen, Shell, Compose-Down, Prune,
Wildcard-, Prefix-, Labelgruppen- oder Projektselektion.

Der Aufruf verwendet die bestehende begrenzte Prozessgrenze mit absolutem
Dockerpfad, temporärem Arbeitsverzeichnis, kontrollierter Spracheinstellung,
Timeout und begrenzter Ausgabe.

Kein Container, Netz, Image, Backup, Snapshot, Claim oder Evidenceobjekt gehört
zum Ressourcenmutationsbudget.

## Abwesenheitsbestätigung

Nach dem Remove führt der Operator genau eine exakte Volume-Namensabfrage mit
vollständig verankertem Namen aus.

Nur leere erfolgreiche Ausgabe bestätigt Abwesenheit.

Ein weiterhin sichtbares Volume oder jeder technisch mehrdeutige Ausgang ist
Unknown Outcome.

Der Remove wird danach niemals wiederholt.

Ein erfolgreicher Removeprozess ohne bestätigte Abwesenheit erzeugt keine
finale Evidence.

## Unknown Outcome

Nonzero, stderr, Timeout, Truncation, Hard Kill oder Prozessverlust ab Beginn
des Remove endet technisch unavailable.

Der Claim bleibt erhalten und finale Evidence fehlt.

Ein unmittelbarer Wiederholungsaufruf stoppt wegen des offenen Claims vor
Docker.

Es gibt keinen Blind-Retry, Ersatzbefehl, manuelles Claimlöschen oder
heuristische Erfolgsableitung.

Die spätere Zustandsklärung bleibt einer getrennten read-only Reconciliation
vorbehalten.

## Finale private Evidence

Nach bestätigter Abwesenheit schreibt der Operator finale owner-only Evidence.

Sie bindet die vollständige Authority- und Entscheidungskette, exakte
Volumeidentität, ausgeführten Einzelschritt
`remove_exact_volume_once`, bestätigte Abwesenheit, Start- und Abschlusszeit
sowie Ausgang `volume_removed`.

Die Datei entsteht über exklusive Temporäranlage, vollständigen Write, Flush,
atomaren Hardlink und Verzeichnissynchronisation.

Anschließend wird sie bytegenau und semantisch zurückgelesen.

Abweichende vorhandene Evidence wird niemals überschrieben.

## Claimfreigabe und Evidence-Retry

Erst nach erfolgreicher Evidence-Rücklesung entfernt der Operator
ausschließlich den exakten Volume-Deletion-Claim und synchronisiert das
Verzeichnis erneut.

Bleibt die Claimfreigabe technisch mehrdeutig, bleibt die finale Evidence
erhalten.

Der exakte Wiederholungsaufruf prüft dann nur historische Autorisierung,
Evidence und Claimbindung und wiederholt ausschließlich die Claimfreigabe.

Preflight, Volumeinspektion, Remove und Abwesenheitsabfrage bleiben beim
Evidence-Retry unerreichbar.

Fehlt der Claim bereits, liefert dieselbe Evidence idempotent erneut
`volume_removed`.

## Geschlossene Ausgänge

Der Operator liefert ausschließlich:

- `volume_removed` nach finaler Evidence und bestätigter Claimfreigabe;
- `rejected` aus dem frisch negativen Preflight;
- `investigation_required` aus dem frischen Konfliktausgang;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die CLI schreibt nur Schemaversion, Operation
`disposable_postgres_volume_deletion` und den kanonischen Ausgang.

Interne IDs, Hashes, Pfade, Ressourcennamen, Identitäten, Zeitwerte und
Fehlerdetails bleiben privat.

## Tests

Vierzehn Tests prüfen:

- die exakte positive Dockerreihenfolge mit genau einem Remove;
- finale Evidence vor Claimfreigabe;
- `rejected` und `investigation_required` ohne Claim;
- letzte Fremdbindung vor Remove mit erhaltenem Claim;
- Nonzero, Timeout und stderr beim Remove als Unknown Outcome;
- nicht bestätigte Abwesenheit ohne zweiten Remove;
- vorhandenen Claim vor Docker;
- Evidence-Retry und idempotente finale Evidence ohne Preflight oder Docker;
- detailarme CLI und installierten Entry Point.

Alle Dockerprozesse sind fake-basiert; kein echtes Volume wird verändert.

## Bundle und Nichtziele

LQ-394 ergänzt ein Operatormodul und einen Console Entry Point.

Der Bundle-Bestand steigt auf 52 Entry Points und 56 Operatormodule.

Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Service-, HTTP- oder Production-Wiring-Änderung.

Der Slice implementiert keine Unknown-Outcome-Reconciliation, Continuation,
Backup-/Snapshotlöschung oder Aussage vollständiger Datenentsorgung.

## Nächster Slice

LQ-395 sollte den strikt read-only Claim-Reconciliation-Vertrag für offene
Volume-Deletion-Claims definieren.

Er muss exakte Claim- und Authoritybindung sowie vorhandenes, abwesendes oder
fremd gebundenes Volume klassifizieren, ohne Claim, Evidence oder Ressourcen
zu verändern.
