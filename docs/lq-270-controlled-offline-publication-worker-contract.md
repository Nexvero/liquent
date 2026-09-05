# LQ-270 — Controlled Offline Publication Worker Contract

## 1. Ergebnis

LQ-270 friert den Vertrag für einen kurzlebigen Offline-Worker ein, der genau
eine bestehende persistente Publication-Execution kontrolliert weiterführt.

Der Worker verbindet später die bereits geprüfte LQ-249- bis LQ-265-
Zustandsmaschine mit der vollständig besessenen Package-Index-Composition aus
LQ-269.

Dieser Slice implementiert keinen Worker, CLI-Befehl oder Providerzugriff.

## 2. Eigener Prozess

Der Worker läuft außerhalb von HTTP-, OIDC-, Browser-Session- und Research-
Prozessen unter einem dedizierten nicht interaktiven Prozesskonto.

Nur dieser Prozess erhält Zugriff auf das Publication-Credential und den
immutable Creator.

Ein Webrequest, eingeloggter Principal oder Research-Job kann den Worker nicht
direkt starten oder seine Abhängigkeiten übernehmen.

## 3. Genau eine Arbeitseinheit

Ein Worker-Aufruf bearbeitet genau eine persistente Publication-Execution.

Er scannt keine Tabelle, reserviert keine Queue und wählt nicht selbstständig
den nächsten Handoff aus.

Batch-, Watch-, Daemon-, Polling- und Scheduler-Verhalten bleiben außerhalb
dieser Grenze.

Nach einem terminalen oder aktuell nicht fortsetzbaren Ergebnis endet der
Prozess.

## 4. Geschlossener Input

Der spätere Aufruf akzeptiert ausschließlich stabile interne Referenzen, die
zum bestehenden Execution-Vertrag gehören:

- Publication-Execution-ID;
- Handoff-ID;
- Publisher-Authority-ID;
- Channel-ID;
- erwartete Channel-Policy-Revision.

Diese Werte identifizieren die gewünschte initiale Execution, erteilen aber
keine Authority.

Der Caller liefert insbesondere keine Attempt-ID, Attempt-Nummer, Phase,
Retry-Entscheidung, Observation oder Ergebnisart.

## 5. Keine Providerparameter im Input

Unzulässig sind caller-gelieferte:

- Origin-, Upload- oder Inspection-URL;
- Providerart, Zielname, Paketname oder Paketversion;
- Credential-, Secretpfad- oder Profilangabe;
- Artefaktpfad, Artefaktbytes oder Hashüberschreibung;
- Rolle, Allow-Boolean oder Authority-Snapshot;
- Receipt-, Request- oder Reconciliation-Behauptung.

Ziel, Artefakte, Authority und aktueller Zustand stammen ausschließlich aus
der lokalen Composition und dem System of Record.

## 6. Vollständige Abhängigkeitsgruppe

Aktivierung verlangt gemeinsam:

- genau eine Datenbankengine;
- genau eine kontrollierte lokale Artifact-Source;
- die bestehenden persistenten Publication-Adapter;
- genau eine LQ-269-Package-Index-Composition;
- sichere Generatoren für intern benötigte IDs;
- explizite Wall- und Monotonic-Clocks.

Teilkonfiguration scheitert vor jeder Publication-Arbeit fail-closed.

Es gibt keinen In-Memory-, Fake-, No-op- oder anonymen Production-Fallback.

## 7. Startup ohne Providerwirkung

Startup validiert lokale Parameter, öffnet Engine und Package-Index-
Composition und lädt deren Credential genau einmal.

Startup führt keinen Preflight, Provider-Read oder Provider-Write aus.

Erst die explizite Übergabe der vollständigen geschlossenen Execution-
Referenz darf die persistente Zustandsmaschine aufrufen.

## 8. Zustand stammt aus Persistenz

Die Arbeitseinheit entscheidet ihren nächsten Schritt nicht aus einem Caller-
Label.

Die bestehenden Persistenzadapter lösen atomar den aktuellen Zustand auf und
akzeptieren nur den jeweils zulässigen Übergang.

Ein stale Request kann deshalb weder einen früheren Zustand wiederherstellen
noch einen bereits möglichen Provider-Write wiederholen.

## 9. Initialer Attempt

Für eine noch nicht vorhandene Execution ruft der Worker zuerst ausschließlich
den bestehenden Attempt-1-Preflight auf.

Nur dessen committeter `prepared`-Fakt erlaubt die weitere Kette.

Neutrale Ablehnung, aktueller Authority-Entzug, bestehender konkurrierender
Handoff-Execution oder Konflikt erreichen keinen Provider-Write.

Die Attempt-ID wird intern erzeugt und niemals vom Caller übernommen.

## 10. Read-before-write und Create

Ein vorbereiteter Attempt erreicht ausschließlich die bestehende Target-
Inspection und Artifact-Integrity-Grenze.

Nur bestätigte Abwesenheit bei weiterhin aktuellen persistenten Fakten darf
den atomaren `write_started`-Übergang und genau einen immutable Create
erreichen.

Bereits vorhandene, konfliktbehaftete oder technisch unbekannte Ziele führen
in diesem Schritt zu keinem Create.

## 11. Unknown vor jeder Erfolgsbewertung

Nach begonnenem Provider-Create wird der persistente Attempt unabhängig von
Acknowledgement oder technischer Rückgabe als `outcome_unknown` gesichert.

Eine Provider-Acknowledgement ist kein Receipt und darf nicht als terminales
Worker-Ergebnis ausgegeben werden.

Schlägt die Unknown-Sicherung fehl, meldet der Worker ausschließlich technische
Nichtverfügbarkeit; er startet niemals einen zweiten Create.

## 12. Höchstens ein Create pro Aufruf

Ein Worker-Prozess darf höchstens einen semantischen Provider-Create ausführen.

Nach einem möglichen Create sind alle weiteren Provideroperationen desselben
Aufrufs read-only.

Der Aufruf startet insbesondere keinen Attempt 2, auch wenn eine anschließende
Inspection Abwesenheit bestätigt.

Damit können technische Wiederholung, Prozess-Retry oder Scheduler-Retry nicht
zwei Creates in eine einzige undurchsichtige Arbeitseinheit zusammenziehen.

## 13. Unmittelbarer Read-back

Nach einem erfolgreich persistierten `outcome_unknown` darf derselbe Aufruf
genau eine read-only Reconciliation und den passenden Finalizer versuchen.

Bytegleich sichtbare Publication kann dadurch atomar als Receipt abgeschlossen
werden.

Bestätigte Abwesenheit oder Konflikt wird über den bestehenden Recovery-
Finalizer historisch bewahrt.

Technische Unklarheit lässt `outcome_unknown` unverändert und beendet den
Aufruf detailfrei nichtverfügbar.

## 14. Wiederaufnahme eines Unknown-Outcome

Findet ein späterer Worker-Aufruf bereits `outcome_unknown`, führt er keinen
Create aus.

Er verwendet ausschließlich read-only Reconciliation und den zuständig
bestehenden Finalizer.

Die persistierte Attempt-ID wird aus dem System of Record aufgelöst; sie ist
kein Callerparameter.

Ein Prozessabbruch nach `write_started` kann daher nicht zu blindem Upload-
Retry führen.

## 15. Attempt 2 bleibt eigener Aufruf

Nur ein abgeschlossenes `absence_confirmed` für Attempt 1 kann in einem
späteren Worker-Aufruf den bestehenden Attempt-2-Preflight erreichen.

Dieser Preflight prüft Artefakte, Zielabwesenheit und alle Authorities erneut
und erzeugt intern genau eine neue Attempt-ID.

Auch der Attempt-2-Aufruf führt höchstens einen Create aus.

Attempt-2-Abwesenheit und Attempt-2-Konflikt sind terminal; Attempt 3 ist
unzulässig.

## 16. Aktuelle Revocation

Vor jedem Write lesen die bestehenden Persistenzgrenzen Channel, Publisher,
Registry, Signer, Key und Reassessment aktuell.

Eine frühere Worker- oder Preflight-Entscheidung ist kein Grace-Ticket.

Revocation vor Write verhindert den Create. Revocation nach möglichem Effekt
bewahrt eine bestätigte externe Publication mit `pending` Reassessment.

Die Worker-Composition fügt keinen Authority-Cache hinzu.

## 17. Ergebnisfamilien

Nach außen werden nur begrenzte nicht-sensitive Ergebnisfamilien benötigt:

- `published`;
- `published_reassessment_required`;
- `not_published`;
- `publication_conflict`;
- `pending_reconciliation`;
- `not_actionable`;
- `unavailable`.

Das Ergebnis enthält keine Credentials, Providerantwort, URL, Hashliste,
Artefaktbytes oder Authority-Details.

`not_actionable` vereinheitlicht neutrale Abwesenheit, stale Referenz und
aktuell nicht erlaubten Übergang, ohne Existenzdetails offenzulegen.

## 18. Detailfreie technische Nichtverfügbarkeit

Datenbank-, Artifact-, Credential-, Client-, DNS-, TLS-, Timeout-, Provider-,
Clock-, Generator- und Strukturfehler werden an der Worker-Grenze detailfrei
als `unavailable` abgebildet.

Die Ursache entscheidet nicht über fachliche Abwesenheit und wird nicht in
einen Upload-Retry übersetzt.

Der Vertrag benennt dafür keinen neuen Domain-Exception-Typ.

## 19. Konkurrenz und exakter Retry

Die persistente Zustandsmaschine bleibt alleinige Konkurrenzgrenze.

Mehrere Prozesse für dieselbe Referenz dürfen höchstens einen neuen
write-fähigen Attempt wirksam machen.

Exakter Retry liefert einen vorhandenen terminalen Fakt oder setzt den einzig
zulässigen Zustand fort, ohne neue externe Identität zu erfinden.

Ein In-Process-Lock oder Singleton-Daemon ist keine Sicherheitsvoraussetzung.

## 20. Ressourcenabschluss

Engine, Package-Index-Client und kurzlebiges Credential gehören dem
Worker-Aufruf.

Alle Ressourcen werden bei Erfolg, neutralem Ergebnis, technischer
Nichtverfügbarkeit und unerwartetem Prozesspfad bestmöglich geschlossen.

Close-Fehler dürfen einen bereits persistent gesicherten Unknown-Zustand nicht
als Erfolg umdeuten oder einen weiteren Provideraufruf auslösen.

Es bleibt kein gemeinsam genutzter Publication-Client im Webprozess zurück.

## 21. Logging und Standardausgabe

Zulässige Ausgabe ist auf Ergebnisfamilie und optional intern sichere
Execution-Korrelation begrenzt.

Logs enthalten keine Handoff-Metadaten, Ziel-URL, Paketversion, Hashes,
Credentialpfade, Provider-Request-ID oder Response-Inhalte.

Standardausgabe und Standardfehler müssen maschinenlesbar, begrenzt und
detailfrei bleiben.

## 22. Retention und Nichtwiederverwendung

Der Worker erzeugt keine eigene Auditdatei.

Persistente Executions, Attempts, Recoveries, Receipts, externe Identitäten,
Providerrevisionen und Reassessments bleiben mindestens so lange erhalten wie
die zugehörige Release- und Publication-Historie.

Execution-, Attempt-, Recovery-, Receipt- und Reassessment-IDs werden niemals
für eine andere fachliche Entscheidung wiederverwendet.

Credentials, rohe Providerantworten und temporäre Clientdaten werden nicht als
historische Fakten aufbewahrt.

## 23. Bewusst nicht entschieden

LQ-270 entscheidet keine:

- Python-Klasse, Signatur, Port oder Exception;
- CLI-Argumente, Requestdatei oder Exitcodes;
- Scheduler-, Queue-, Daemon- oder Service-Unit-Integration;
- konkrete Artifact-Source-Composition;
- ID-Dateiquelle oder Generatorimplementierung;
- Tabelle, Schema, SQL, Migration oder Seed;
- Runtime-, Compose-, CI-, Git- oder Deploymentverdrahtung;
- Withdrawal-, Yank-, Delete- oder Rollback-Funktion.

Es erfolgt kein Provider-, Dateisystem-, Git- oder Deploymentwrite.

## 24. Nachweis und Folgeordnung

LQ-265 belegt die endliche persistente Zustandsmaschine bereits auf SQLite und
PostgreSQL 16. LQ-267 bis LQ-269 belegen den konkreten Package-Index-Adapter,
den begrenzten HTTPS-Transport und dessen lokale Ressourcen-Composition.

LQ-270 verbindet diese Verträge, ohne Implementierungs- oder Aktivierungsumfang
vorwegzunehmen.

Der Migration-Head bleibt `20260819_0024` mit 24 linearen Migrationen. Die
vollständige Pflichtsuite bleibt bei:

```text
3307 passed, 534 warnings
```

LQ-271 implementiert als nächsten Slice die providerneutral testbare
Einzelarbeits-Composition für diese eingefrorene Worker-Zustandsführung, noch
ohne CLI-, Scheduler- oder Production-Wiring.
