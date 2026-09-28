# LQ-327 — Disposable PostgreSQL and Current Rollback Evidence Contract

## Zweck

LQ-327 definiert die beobachtbaren Verträge der beiden nächsten LQ-303-Gates:

- `disposable_postgres` mit Fakt `database_isolated`;
- `rollback` mit Fakt `rollback_current`.

Die erste Phase darf genau eine neue rungebundene isolierte PostgreSQL-
Instanz bereitstellen. Die zweite Phase ist strikt read-only und prüft nur
vorhandene Backup-/Application-Rollback-Evidence.

Dieser Slice implementiert oder startet keine Datenbank, keinen Container und
keinen Evidence-Inspector.

## Strikte Phasentrennung

`disposable_postgres` ist eine bewusst mutierende Infrastrukturphase. Sie
besitzt keine Backup-, Promotion- oder Rollbackentscheidung.

`rollback` ist eine read-only Evidencephase. Sie startet, stoppt, ersetzt,
migriert, restauriert oder löscht keine Datenbank und führt keinen Application-
Rollback aus.

Ein Erfolg der einen Phase impliziert niemals den Erfolg der anderen. Beide
erzeugen getrennte neutrale Boolean-Fakten für den bestehenden LQ-308-Reducer.

## Gemeinsame Run-Bindung

Beide Phasen verlangen dieselbe bereits validierte LQ-305-Run-Autorisierung mit
Run-ID, staging Environment, Source-Commit, Application-Image-Digest,
Compose-SHA-256, erwartetem Migration-Head, getrennten Identitäten und engem
UTC-Zeitfenster.

Zusätzlich muss das PostgreSQL-Image aus der owner-only Image-Environmentdatei
eine unveränderliche Digestreferenz sein und durch das erneut gerenderte
Composemodell exakt gebunden werden.

Caller dürfen weder Projekt-, Service-, Container-, Netzwerk-, Volume-,
Datenbank-, Backup-, Snapshot- oder Rollbackziel frei wählen.

Mutable Tags, Wildcards, Default-Composefiles, PATH-Auflösung und geerbte
Docker-/Cloud-/Credentialumgebung sind unzulässig.

## Vorbedingungen vor PostgreSQL-Mutation

Vor dem ersten möglichen Docker-Effekt werden erneut geprüft:

- owner-only aktuelle Run-Autorisierung und Environmentdateien;
- exakter Compose-SHA-256 und staging-only Projektname;
- alle Imagewerte als immutable SHA-256-Digests;
- vollständiger kanonischer Compose-Render ohne unbekannte Services;
- exakter PostgreSQL-Service und autorisiertes PostgreSQL-Image;
- keine Hostportveröffentlichung;
- ausschließlich rungebundene interne Netze;
- genau ein neues rungebundenes Datenvolume;
- einzig das erwartete PostgreSQL-Password-Secret am festen Ziel;
- feste Healthcheck-, User-, Database-, Resource- und Securitygrenzen;
- nachweisliche Abwesenheit aller exakt abgeleiteten Run-Ressourcennamen.

Jeder Fehler endet vor Pull, Create oder Start technisch unavailable.
Vorhandene gleichnamige Ressourcen werden niemals übernommen oder bereinigt.

## Rungebundene Ressourcen

Die Phase darf ausschließlich intern deterministisch aus der validierten
Run-ID abgeleitete neue Ressourcen adressieren:

- einen PostgreSQL-Container oder äquivalenten Compose-Servicezustand;
- dedizierte nicht externe Application-/Data-Netze;
- genau ein dediziertes PostgreSQL-Datenvolume;
- notwendige kurzlebige Compose-Metadaten dieses Runs.

Die Namen enthalten keine DSN, Credential-, User-, Workspace-, Job-, Claim-
oder Hostidentität.

Globale, Production-, bestehende Staging-, Backup-, Artifact-, Monitoring- und
anderer Run-Ressourcen sind außerhalb des Mutationsbudgets.

Die Phase darf kein extern benanntes `liquent_*`-Netz oder Volume stillschweigend
als isolierte Run-Ressource interpretieren.

## Exakter PostgreSQL-Start

Der spätere Adapter darf ausschließlich das autorisierte PostgreSQL-Image ohne
Build und ohne Tag-Fallback verwenden.

Er startet genau eine Instanz mit:

- keinem veröffentlichten Port und keinem Public-Netz;
- ausschließlich den dedizierten internen Run-Netzen;
- genau dem dedizierten neuen Datenvolume;
- dem owner-kontrollierten PostgreSQL-Password-Secret;
- festem Datenbank- und Usernamen aus der geprüften Composition;
- `no-new-privileges`, geschlossener Capability-Allowlist und festen
  Ressourcenlimits;
- festem Healthcheck ohne Shellwert aus Callerinput;
- keiner Application-, Worker-, Artifact- oder Researchdatenfähigkeit.

Es gibt keine zweite Instanz, Skalierung, Replikation, Restore, Seed,
Extensioninstallation oder Migration in dieser Phase.

## Isolationsnachweis

`database_isolated=true` ist nur zulässig, wenn nach dem Start read-only und
rungebunden beobachtet wurde:

- exakt eine gesunde Instanz aus dem autorisierten Digest;
- keine Hostportbindung und keine nicht erlaubte Netzwerkzuordnung;
- ausschließlich das neu erzeugte rungebundene Datenvolume;
- keine vor dem Run vorhandene Volume- oder Containeridentität;
- keine Production-/anderen Staginglabels oder externen Ressourcennamen;
- noch kein ausgeführtes Migration-Gate;
- keine Application-, Identity-, Workspace-, Job-, Claim-, Outcome- oder
  Artifactfakten aus diesem Lauf.

Der Nachweis darf keine DSN, Secret-, Container-, Netzwerk-, Volume- oder
Hostpfaddetails ausgeben.

Ein eindeutig verletzter Isolationsfakt ergibt neutrales `false`. Technische
Mehrdeutigkeit ist unavailable.

## Empty bedeutet nicht inhaltlich erraten

Die Phase behauptet keine fachlich leere Datenbank durch ungeprüfte Annahme.

Vor Migrationen dürfen ausschließlich PostgreSQL-systemeigene Startobjekte
vorhanden sein. Ob der erwartete Liquent-Schema-Head später erreicht wird,
entscheidet erst `migration_gate` plus `migration_head`.

`disposable_postgres` führt keine frei formulierte SQL-Abfrage aus und legt
keine neue Schema-, Tabellen- oder Seeddefinition fest. Ein späterer
Implementierungsslice muss die minimalen neutralen Startfakten separat
entscheiden.

## Unknown Outcome der Bereitstellung

Nach dem ersten möglichen Docker-Effekt werden Timeout, Daemonverlust,
Outputverlust, Hard Kill, unklarer Healthstatus oder uneindeutige
Ressourcenerzeugung als Unknown Outcome behandelt.

Es gibt keinen automatischen zweiten `up`, keinen alternativen Projektnamen,
kein `down`, Volume-Remove, Network-Remove, Prune oder Blind-Cleanup.

Mögliche Run-Ressourcen bleiben Recoverybestand. Ein separater späterer
Recoveryvertrag muss ihre exakte Run-Bindung read-only beweisen.

Die Phase erzeugt keine scheinbare `false`-Evidence aus technischer
Ungewissheit.

## Ressourcenbesitz und Lebensdauer

Der Staginglauf darf die von ihm neu erzeugten dedizierten Ressourcen für die
nachfolgenden Migration-, Worker-, Job- und Signalphasen verwenden.

Ein bestandener Gate-Aufruf überträgt dem Phasenadapter kein allgemeines
Löschrecht. Geordneter Run-Abschluss und Cleanup bleiben getrennte spätere
Verträge.

Bestehende Ressourcen werden niemals übernommen, überschrieben, umbenannt oder
als Eigentum des Runs markiert.

## Rollback-Evidence-Eingaben

`rollback` erhält ausschließlich private read-only Evidenceobjekte, die vor
dem Staginglauf durch bestehende kontrollierte Backup-/Promotionprozesse
erzeugt wurden.

Die Evidence muss mindestens binden:

- dieselbe staging Environmentidentität;
- Source-Commit und autorisierten Kandidaten-Application-Digest;
- bekannten vorherigen gesunden Application-Digest;
- Backup-/Snapshotidentität und deren unveränderliche Evidence-Digests;
- erfolgreiche Restore-Verifikation;
- Erzeugungs- und Verifikationszeit in UTC;
- getrennte vorbereitende und prüfende Identitäten;
- unveränderlichen Status, der einen kontrollierten Application-Rollback
  erlaubt.

Die Run-Autorisierung bindet die erwarteten Evidence-Digests; der Caller kann
keinen beliebigen Backup- oder vorherigen Digest präsentieren.

## Bedeutung von `rollback_current`

`rollback_current=true` bedeutet ausschließlich:

- Backup-/Restore-Evidence ist strukturell gültig und innerhalb der festen
  Frischepolicy;
- Environment, Source, Kandidatendigest und vorheriger gesunder Digest sind
  konsistent gebunden;
- der bestehende Application-Rollbackpfad referenziert genau den bekannten
  vorherigen Digest;
- Evidence wurde unabhängig geprüft und ist nicht superseded oder widerrufen;
- keine Evidence stammt aus Production oder einem anderen Run.

Es bedeutet nicht, dass Rollback ausgeführt wurde oder sicher erforderlich ist.
Es gewährt keine Promotion und keine Productionfreigabe.

## Kein Datenbankrollback

Die Phase führt ausdrücklich kein `alembic downgrade`, Restore, Datenbankdrop,
Volumeaustausch oder SQL-Rollback aus.

Application-Rollback stellt nur einen vorher bekannten gesunden Image-Digest
wieder her. Migrationen müssen bis zu einem späteren expand/contract-Vertrag
mit der vorherigen Application-Version kompatibel bleiben.

Fehlende Kompatibilität oder fehlende aktuelle Backup-/Restore-Evidence ergibt
`rollback_current=false`; technische Lesefehler bleiben unavailable.

## Read-only Verarbeitung und Ausgabe

Evidence wird no-follow, größenbegrenzt, mit geschlossener Feldmenge und
Duplikatschlüsselerkennung gelesen. Signaturen, Hashes, Zeitfenster und
Bindungsrelationen werden vor dem Boolean vollständig geprüft.

stdout enthält nur das kanonische LQ-310-Schema:

- `database_isolated` für `disposable_postgres`;
- `rollback_current` für `rollback`.

Raw Evidence, IDs, Digests, Zeitwerte, Pfade, Ressourcennamen und Fehlerdetails
werden nicht ausgegeben oder als Phase-Evidence persistiert.

## Nichtziele

LQ-327 entscheidet keine konkrete Docker-argv, Compose-Override-Datei,
Netzwerk-/Volumenamensyntax, Health-Timeouts, SQL-Startabfrage,
Backup-Evidence-Signatur oder Frischezahl.

Es gibt keine Implementierung, keinen Testcontainer, keinen realen PostgreSQL-
Start, kein Restore, keinen Rollback und keine Schema-, Tabellen-, SQL-,
Migration-, Port-, Domainmodell-, Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-328 sollte zuerst den reinen read-only `rollback_current`-Evidence-Inspector
implementieren. Die mutierende disposable-PostgreSQL-Composition benötigt
danach einen eigenen Implementierungs- und Recoverystrang.
