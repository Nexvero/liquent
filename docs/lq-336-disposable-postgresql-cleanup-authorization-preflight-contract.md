# LQ-336 — Disposable PostgreSQL Cleanup Authorization and Preflight Contract

## Zweck

LQ-336 definiert die zusätzliche Autorisierung und den strikt read-only
Preflight vor einer möglichen Entfernung exakt gebundener LQ-330-Ressourcen.

Der Vertrag gilt ausschließlich nach einem aktuellen LQ-335-Ausgang
`cleanup_review_eligible`.

Dieser Slice implementiert keinen Command, startet keinen Dockerprozess und
stoppt oder entfernt weder Container, Netze noch Volume.

## Keine Autoritätsvererbung

Staging-, Reconciliation-, Claim-Reconciliation- und
Dispositionsautorisierungen gewähren kein Cleanuprecht.

Auch `cleanup_review_eligible` ist nur eine read-only Eignungsaussage. Es ist
weder Delete-Ticket noch Ressourcenbesitzübertragung.

Cleanup benötigt eine neue owner-only Autorisierung mit eigener stabiler,
nicht wiederverwendbarer Cleanup-ID und einem aktuellen engen Zeitfenster.

Eine Produktrolle, Workspace-Membership, Researchpermission, SessionPrincipal,
allgemeine Administratorbezeichnung oder caller-geliefertes Allow-Boolean
reicht nicht aus.

## Geschlossene Cleanup-Autorisierung

Die spätere Cleanup-Datei muss mindestens exakt binden:

- Schema-Version und Cleanup-ID;
- ursprüngliche Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-ID;
- Claim-Reconciliation-ID;
- LQ-335-Disposition-ID;
- SHA-256 der Staging-Evidence;
- SHA-256 der LQ-332-Reconciliation-Evidence;
- SHA-256 der LQ-333-Claim-Reconciliation-Evidence;
- SHA-256 der LQ-335-Dispositionsautorisierung;
- Operation exakt `remove_disposable_postgres_resources`;
- einen geschlossenen Cleanup-Scope;
- getrennte Cleanup-Executor-/Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Unbekannte Felder, doppelte Schlüssel, mutable Images, gleiche Identitäten,
stale Zeit oder Hashabweichung sind technisch unavailable.

Die Datei akzeptiert keinen Container-, Netzwerk-, Volume-, Service- oder
Projektwert vom Caller.

## Zwei getrennte Scopes

Der Scope ist exakt einer von:

- `runtime_only`;
- `runtime_and_data_volume`.

`runtime_only` umfasst ausschließlich den exakt gebundenen PostgreSQL-
Container und die beiden ausschließlich diesem Run gehörenden internen Netze.
Das Datenvolume muss erhalten bleiben.

`runtime_and_data_volume` umfasst zusätzlich genau das rungebundene
PostgreSQL-Datenvolume.

Der zweite Scope ist bewusst destruktiver und kann nicht aus dem ersten
abgeleitet, erweitert oder durch einen CLI-Schalter nachträglich aktiviert
werden.

Ein allgemeines `include_volume=true`, freier Scope oder nachträglicher
Operatorentscheid ist unzulässig. Maßgeblich ist ausschließlich die
autorisierte geschlossene Scopebezeichnung.

## Vollständige Evidencekette

Der Preflight muss historische Staging-, Reconciliation- und
Claim-Reconciliation-Autorisierungen sowie aktuelle Dispositions- und
Cleanup-Autorisierung vollständig prüfen.

Alle IDs, Run-, Phase-, Source-, Image-, Compose- und Identitätsrelationen
müssen exakt übereinstimmen.

Die drei Evidenceobjekte und die Dispositionsautorisierung werden bytegenau
gegen die in der Cleanup-Autorisierung gebundenen SHA-256-Werte geprüft.

Finale LQ-332-Evidence muss `isolated` lauten. Die LQ-333-Evidence muss diese
Isolation konsistent finalisieren oder bestätigen.

Der LQ-335-Resolver muss bei unveränderten gebundenen Inputs erneut exakt
`cleanup_review_eligible` ergeben. Ein gespeicherter oder caller-gelieferter
String allein genügt nicht.

## Claimfreiheit

Ursprünglicher Reconciliation-Claim, Claim-Reconciliation-Claim und ein
späterer Cleanup-Claim müssen vor Preflightbeginn fehlen.

Ein sichtbarer Claim ist technisch unavailable. Der Preflight entfernt ihn
nicht, liest kein Alter und startet keine Reconciliation.

Ähnliche oder unbekannte Claimnamen werden nicht als der erwartete Claim
interpretiert.

## Erneute Composebindung

Der Preflight validiert absoluten Dockerpfad, SHA-gebundenes Composefile und
beide owner-only Environmentdateien erneut.

Er führt genau einen read-only `compose config --format json` mit explizitem
Projekt, beiden Environmentdateien und festem Composefile aus.

Das Modell muss dieselben geschlossenen LQ-330-Invarianten besitzen:

- exakt gebundenes PostgreSQL-Image;
- keine Ports;
- feste Database-/User-/Secretwerte;
- geschlossener Healthcheck und Capabilitysatz;
- exakt zwei interne nicht externe Runnetze;
- genau ein nicht externes rungebundenes Datenvolume.

Ressourcennamen werden erneut ausschließlich aus Run und Modell abgeleitet.

## Aktuelle read-only Ressourcenprüfung

Der Preflight listet und inspiziert ausschließlich:

- den exakt abgeleiteten PostgreSQL-Container;
- das Application-Netz;
- das Data-Netz;
- das PostgreSQL-Datenvolume.

Alle vier Ressourcen müssen entweder vollständig abwesend oder vollständig
vorhanden sein.

Vollständige Abwesenheit ergibt neutral `already_absent`. Sie erzeugt kein
Cleanuprecht und startet keinen neuen Run.

Teilbestand, fremde Labels, externe Netze, anderes Volume, Portbindung,
abweichender Digest oder zusätzliche Zuordnung ergibt neutral `rejected`.

Malformed Output, Dockerfehler, Timeout, Truncation oder uneindeutige
Beobachtung ist technisch unavailable und nicht `rejected`.

## Voraussetzungen für `ready`

`ready` verlangt gemeinsam:

- aktuelle gültige Cleanup-Autorisierung;
- vollständige hashgebundene Evidencekette;
- erneut abgeleitetes `cleanup_review_eligible`;
- keine offenen Claims;
- vollständig vorhandenen exakt isolierten Runbestand;
- keine Production-, andere Staging- oder fremde Runbindung;
- keinen nachgewiesenen späteren Stagingeffekt.

Der Preflight prüft nur Eignung. Er erzeugt keinen Cleanup-Claim und verändert
keine Evidence.

## Zusätzliche Volumenvoraussetzungen

Für `runtime_and_data_volume` muss zusätzlich rein aus autoritativer Evidence
feststehen:

- `disposable_postgres` war der erste nicht bestätigte Phasenübergang;
- Migration-Gate und alle späteren Phasen blieben unavailable;
- es gab keinen Seed, Restore oder manuellen Datenbankzugriff innerhalb des
  kontrollierten Runs;
- kein Control-Plane- oder Workercontainer wurde für den Run gestartet;
- das Volume besitzt ausschließlich die gebundene Runzuordnung;
- keine Retention-, Legal-Hold-, Backup- oder Investigation-Evidence verlangt
  Erhalt.

Kann auch nur ein Punkt nicht autoritativ bewiesen werden, lautet der
Preflight `rejected` für diesen Scope. Er darf nicht auf `runtime_only`
herabstufen, weil dies die autorisierte Operation verändern würde.

Der Operator kann später eine neue separate `runtime_only`-Autorisierung
anfordern; der Preflight erfindet sie nicht.

## Keine SQL- oder Inhaltsheuristik

Der Preflight öffnet keine Datenbankverbindung und führt keine SQL-Abfrage aus.

Er erklärt ein Volume nicht aufgrund von Größe, Alter, Dateinamen,
Verzeichnisinhalt oder vermeintlich leerem PostgreSQL-Datadir für löschbar.

Fehlende Evidence kann nicht durch heuristische Host- oder Volumeinspektion
ersetzt werden.

## Neutrale Ausgabe

Ein späterer Preflight-Command darf ausschließlich kanonische Schema-Version,
Operation `disposable_postgres_cleanup_preflight` und einen Ausgang liefern:

- `ready`;
- `already_absent`;
- `rejected`;
- technisch unavailable ohne Ergebnis.

Scope, IDs, Hashes, Ressourcennamen, Pfade, Digests, Identitäten, Zeitwerte und
Ablehnungsgründe werden nicht ausgegeben.

`ready` autorisiert keinen Effekt ohne erneute vollständige Validierung im
späteren mutierenden Operator.

## Anforderungen an spätere Mutation

Ein späterer Cleanup-Operator muss dieselbe Autorisierung und Evidence erneut
vollständig laden und den Preflight unmittelbar vor dem ersten Effekt
wiederholen.

Er darf keine caller-gelieferte frühere `ready`-Antwort akzeptieren.

Jede Ressource muss einzeln exakt adressiert werden. Allgemeines
`docker compose down`, `--volumes`, Projekt-/System-Prune, Wildcards, Prefix-
oder Labelgruppenauswahl bleiben verboten.

Nach dem ersten möglichen Effekt führt jede technische Mehrdeutigkeit zu
Unknown Outcome ohne Retry, Fortsetzung oder Blind-Cleanup.

Mutation benötigt eine eigene Evidence-first-Claim- und spätere
Reconciliation-Grenze.

## Retention und Nichtwiederverwendung

Cleanup-ID, Scope, Autorisierungen, Claims, Run- und Reconciliation-IDs sowie
alle Evidenceobjekte müssen mindestens so lange unterscheidbar bleiben, wie
Audit, Retry, Cleanup oder Unknown-Outcome-Reconciliation darauf angewiesen
sind.

Keine ID darf unter anderem Scope, anderer Runbindung oder neuer Bedeutung
wiederverwendet werden.

Dieser Vertrag bestimmt keine konkrete Retentionfrist oder Archivierung.

## Nichtziele

LQ-336 implementiert keinen Preflight, Entry Point, Cleanup-Claim,
Evidencewriter oder mutierenden Operator.

Es gibt keinen Dockerzugriff, Stop, Remove, Prune, SQL-, Schema-, Migration-,
Port-, Domainmodell-, Compose- oder Production-Wiring-Effekt.

Bundle-Gates bleiben bei 33 Entry Points, 37 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-337 sollte ausschließlich den read-only Cleanup-Preflight implementieren.
Er muss Scope, Evidencehashes, aktuelle Ressourcenzuordnung und
Claimfreiheit prüfen und darf noch keinen Cleanup-Claim oder Docker-Remove
erzeugen.
