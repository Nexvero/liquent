# LQ-398 — Evidence-first PostgreSQL Volume Deletion Finalizer

## Ergebnis

LQ-398 implementiert den in LQ-397 definierten Finalizer als
`liquent-disposable-postgres-volume-delete-finalize`.

Der Command finalisiert ausschließlich eindeutig beobachtete terminale
LQ-396-Zustände über eigene private Evidence vor Claimfreigabe.

Er führt keine Ressourcenmutation aus.

## Aktuelle Finalisierungsauthority

Der Finalizer verlangt eine neue owner-only Autorisierung mit stabiler
Volume-Deletion-Finalization-ID.

Sie bindet Reconciliation-, Lösch-, Claim-, Resolver-, Retention-, Hold- und
Recovery-IDs sowie Run, Source, Image, Compose und das intern abgeleitete
Volume.

Die vollständigen Reconciliation-, Lösch- und Resolverautorisierungen sowie
Lineage- und Clearanceartefakte sind über SHA-256 gebunden.

Operation ist exakt `finalize_disposable_postgres_volume_deletion` und Scope
exakt `data_volume_only`.

Finalization-Executor, -Authorizer und -Reviewer sind getrennt und das aktuelle
UTC-Fenster ist auf höchstens eine Stunde begrenzt.

## Historische Authority bleibt historisch

Lösch- und Reconciliation-Autorisierungen werden in ihren ursprünglichen
gültigen Zeitkontexten erneut vollständig geprüft.

Die aktuelle Finalisierungsauthority verlängert weder Inspektions- noch
Löschrecht.

Run, Source, Image, Compose, Volume, Scope, IDs und Hashbeziehungen müssen über
alle drei Stufen übereinstimmen.

Der SHA-256 der vollständigen Reconciliation-Autorisierung wird ausdrücklich
gegen die Finalisierungsauthority geprüft.

Caller liefern keinen Zustand, Claimstatus oder gewünschten Ausgang.

## Finalization-Evidence vor Inspector

Der Evidencepfad wird ausschließlich aus dem SHA-256 der Finalization-ID
abgeleitet.

Exakt vorhandene owner-only Finalization-Evidence wird vor LQ-396 und Docker
gelesen und steuert nur den idempotenten Claimfreigabe-Retry.

Malformed, fremde oder widersprüchliche Evidence wird nicht überschrieben.

Ohne vorhandene Evidence beginnt der normale Weg mit einer frischen
LQ-396-Entscheidung.

## Frische LQ-396-Auflösung

Der Finalizer ruft den Inspector mit denselben gebundenen Authority-, Lineage-,
Clearance-, Projekt- und Evidenceeingaben erneut auf.

Ein gespeicherter oder caller-gelieferter früherer Zustand wird nicht
akzeptiert.

Die Inspectorausgabe muss kanonische Schemaversion, feste Operation und einen
geschlossenen LQ-396-Ausgang enthalten.

Technische Inspectorfehler bleiben detailfrei unavailable.

Der Inspector selbst führt ausschließlich read-only Volumenliste und optional
Inspect aus.

## Terminale Finalisierung

Die Zuordnung ist geschlossen:

- `volume_absent_evidence_missing` wird
  `volume_removal_finalized`;
- `final_evidence_present` wird
  `deletion_evidence_confirmed`.

Beide Ausgänge schreiben getrennte LQ-398-Finalization-Evidence.

Der Finalizer erzeugt insbesondere keine fehlende originale LQ-394-Evidence
und behauptet keine nachträglich empfangene Removeantwort.

## Nichtterminale und neutrale Zustände

`volume_present` wird `continuation_required`.

Dabei entstehen weder Finalization-Evidence noch Claimfreigabe; der
ursprüngliche Löschclaim bleibt offen.

`not_found` wird ohne Write und ohne Docker durch den Finalizer weitergegeben.

`conflict` wird `investigation_required` und lässt Claim, Evidence und
Ressourcen unverändert.

Keiner dieser Ausgänge startet automatisch eine Continuation oder neue
Löschung.

## Eigene Finalization-Evidence

Die private Evidence bindet vollständige Finalisierungs-, Reconciliation- und
Löschauthority, Claim, Run, Source, Image, Compose, Volume, Scope, sämtliche
Entscheidungs- und Evidencehashes sowie den frisch beobachteten Zustand und
kanonischen Ausgang.

Der SHA-256 der Finalisierungsautorisierung wird zusätzlich aufgenommen.

Der Abschlusszeitpunkt ist zeitzonenbehaftet und in UTC normalisiert.

Historische Original-Evidence und Reconciliationartefakte bleiben
unverändert.

## Atomare Evidenceanlage

Evidence entsteht owner-only über exklusive Temporäranlage, vollständigen
Write und Flush.

Die finale Datei wird atomar per Hardlink angelegt und das private
Evidenceverzeichnis synchronisiert.

Anschließend wird sie vollständig zurückgelesen und semantisch gegen dieselbe
Bindung geprüft.

Erst diese erfolgreiche Rücklesung macht Claimfreigabe erreichbar.

Teilgeschriebene oder kollidierende Dateien gelten nicht als Evidence.

## Exakte Claimfreigabe

Der Claimpfad wird aus dem SHA-256 der ursprünglichen Claim-ID abgeleitet.

Ein vorhandener Claim muss vollständig der historischen LQ-394-Bindung
entsprechen.

Nur dieser exakte Claim wird entfernt und das Evidenceverzeichnis danach
erneut synchronisiert.

Ist der Claim bereits abwesend, ist die Freigabe idempotent abgeschlossen.

Suche, Altersheuristik, Prefix, Wildcard oder Gruppenfreigabe existieren nicht.

## Evidence-Retry

Bleibt die Claimfreigabe nach persistierter Evidence technisch mehrdeutig,
bleibt die Evidence erhalten und der Command endet unavailable.

Der exakte Wiederholungsaufruf prüft zuerst dieselbe Evidence und danach nur
den exakten Claim.

Bei vorhandenem gebundenem Claim wird ausschließlich dessen einzelne Freigabe
wiederholt.

LQ-396 und Docker bleiben im Evidence-Retry unerreichbar.

Eine neue ID, neue Authority oder veränderte Evidence ist kein Retry.

## Geschlossene CLI-Ausgänge

Die CLI liefert ausschließlich:

- `not_found`;
- `volume_removal_finalized`;
- `deletion_evidence_confirmed`;
- `continuation_required`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die feste Operation lautet
`disposable_postgres_volume_deletion_finalization`.

Interne IDs, Hashes, Claims, Ressourcen, Pfade, Identitäten und technische
Details bleiben privat.

## Tests

Zehn Tests prüfen:

- Abwesenheitsfinalisierung mit Evidence vor Claimfreigabe;
- Bestätigung vorhandener originaler LQ-394-Evidence ohne Docker;
- `continuation_required` mit unverändertem offenen Claim;
- write-freies `not_found`;
- `investigation_required` bei Fremdbindung;
- Reconciliation- und Löschauthorisierungshash vor Inspector;
- unbekannte Claimfreigabe und Evidence-Retry ohne Inspector;
- detailarme CLI und installierten Entry Point.

Kein Test führt einen Ressourcenschreibpfad aus.

## Bundle und Nichtziele

LQ-398 ergänzt ein Operatormodul und einen Console Entry Point.

Der Bundle-Bestand steigt auf 54 Entry Points und 58 Operatormodule.

Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Service-, HTTP- oder Production-Wiring-Änderung.

Der Slice implementiert keine Continuation für `volume_present`, keine weitere
Volume-Mutation und keine Disposition anderer Datenkopien.

## Nächster Slice

LQ-399 sollte den streng autorisierten Continuationvertrag für den
nichtterminal finalisierten Zustand `volume_present` definieren.

Er muss eigene aktuelle Authority, die frische LQ-396-Beobachtung, den offenen
ursprünglichen Claim und ein minimales einzelnes Remove-Budget binden, ohne
historische Evidence oder IDs umzudeuten.
