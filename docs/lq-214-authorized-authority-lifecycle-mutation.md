# LQ-214 — Authorized Authority Lifecycle Mutation

## 1. Status und Ziel

LQ-214 implementiert reguläre atomare Grant-, Deactivate- und Reactivate-
Entscheidungen für zwei getrennte Management-Authority-Domänen:

- globale OIDC-Trust-Management-Authority;
- workspacebezogene Membership-Management-Authority.

Die Grenzen setzen eine zuvor durch LQ-213 verankerte aktuelle Authority-Set-
Revision voraus. Sie erzeugen aus einer zielbezogenen Absicht selbst den neuen
vollständigen Authority-Satz.

Es entsteht keine generische Admin-Rolle und keine domänenübergreifende
Authority-Vererbung.

## 2. Getrennte Lifecycle-Modelle

Die globale Domäne besitzt `OidcTrustAuthorityLifecycleIntent` mit:

- `GRANT`;
- `DEACTIVATE`;
- `REACTIVATE`.

Die Workspace-Domäne besitzt den getrennten
`WorkspaceMembershipAuthorityLifecycleIntent` mit denselben fachlichen, aber
nicht austauschbaren Werten.

Erfolgreiche Entscheidungen liefern domänenspezifische unveränderliche
Ergebnisse aus Change-ID, resultierender Set-Revision, Zielnutzer und Intent.
Das Workspace-Ergebnis bindet zusätzlich den exakten Workspace.

## 3. Portgrenzen

Jede globale Änderung akzeptiert ausschließlich:

- domänenspezifische Lifecycle-Change-ID;
- authentifizierten `SessionPrincipal`;
- exakte Ziel-`UserId`;
- einen der drei regulären Intents;
- exakt erwartete globale Set-Revision.

Die Workspace-Grenze akzeptiert zusätzlich genau einen `WorkspaceId`.

Kein Port akzeptiert Authority-Status, vollständige Mitgliederlisten, Rollen,
Capabilities, Research-Permissions, Allow-Booleans oder eine resultierende
Revision.

## 4. Aktuelle Autorisierung

Der `SessionPrincipal` identifiziert ausschließlich den Actor. Für jede neue
Entscheidung löst der persistente Adapter atomar auf:

1. Actor existiert und ist aktiv;
2. Zielnutzer existiert und ist aktiv;
3. Actor besitzt aktuell aktive Authority derselben Domäne;
4. im Membership-Fall existiert der exakte Workspace und ist aktiv;
5. die aktuelle Set-Revision stimmt exakt mit der Erwartung überein.

Eine globale Trust-Authority kann keine Membership-Authority gewähren. Eine
Workspace-Authority kann ausschließlich ihren eigenen Workspace verändern.

Fehlende oder inaktive Foundation und Authority sowie stale Revisionen enden
neutral fail-closed.

## 5. Vollständige Ausgangskonsistenz

Vor einer Mutation vergleicht der Adapter den aktuellen operativen Authority-
Bestand mit allen Mitgliedern der erwarteten unveränderlichen Set-Revision.

UserIds und active/inactive-Status müssen vollständig übereinstimmen. Ein
fehlendes, zusätzliches oder abweichendes Mitglied ist kein normaler
Lifecycle-Zustand, sondern detailfreie technische Nichtverfügbarkeit.

Damit wird keine neue Revision auf beschädigter oder außerhalb der
Lifecycle-Grenze veränderter Historie aufgebaut.

## 6. Grant

`GRANT` ist nur zulässig, wenn für den Zielnutzer im exakten Scope noch nie ein
Authority-Fakt existiert.

Der Zielnutzer muss bereits als aktiver interner Nutzer existieren. Grant
erzeugt ausschließlich eine aktive Management-Authority und keine Membership,
Research-Permission, Onboarding-Authority oder Trust-Konfiguration.

Ein bereits aktiver oder inaktiver Authority-Fakt wird nicht überschrieben.
Aktive Wiederholung benötigt dieselbe Change-ID; inaktive Historie benötigt
explizit `REACTIVATE`.

## 7. Deactivate

`DEACTIVATE` verlangt einen aktuell aktiven Authority-Fakt des Zielnutzers.

Die Operation löscht ihn nicht, sondern setzt seinen Status auf `inactive`.
Die stabile UserId und sämtliche historische Set-Mitgliedschaften bleiben
erhalten.

Selbstdeaktivierung ist zulässig, wenn danach mindestens ein anderer
wirksamer Manager verbleibt. Der Commit wirkt auf jede später neu begonnene
Authority- oder fachliche Managemententscheidung.

## 8. Schutz des letzten wirksamen Managers

Eine Deaktivierung wird neutral abgelehnt, wenn danach kein Authority-Fakt
mehr zugleich aktiv und an einen aktuell aktiven Nutzer gebunden wäre.

Im Workspace-Fall ist der Workspace bereits als aktive Vorbedingung gebunden.

Die Lockout-Prüfung verwendet den vollständigen geplanten Satz und geschieht
in derselben Transaktion wie Statusänderung, neue Revision, Pointerwechsel und
Change-Entscheidung.

Ein inaktiver Nutzer mit formal aktiver Authority zählt nicht als wirksamer
verbleibender Manager.

## 9. Reactivate

`REACTIVATE` verlangt einen vorhandenen aktuell inaktiven Authority-Fakt im
exakten Scope.

Der Zielnutzer muss weiterhin aktiv sein. Die Operation setzt nur den
Authority-Status auf `active`; sie reaktiviert weder Nutzer noch Workspace und
erzeugt keine andere Capability.

Reaktivierung in einem fremden Workspace oder in der anderen Authority-Domäne
ist strukturell ausgeschlossen.

## 10. Atomarer neuer Snapshot

Jede erfolgreiche reguläre Mutation erzeugt atomar:

1. die exakt erlaubte Änderung am operativen Authority-Fakt;
2. eine neue stabile unveränderliche Set-Revision;
3. ein vollständiges Set-Mitglied für jeden Authority-Fakt des Scopes;
4. den Wechsel des Current-Pointers von exakt der erwarteten Revision;
5. eine persistente Lifecycle-Entscheidung mit Actor, Ziel, Intent,
   Vorgänger- und Ergebnisrevision.

Alles committet oder nichts. Der Revisionsgenerator wird erst nach
Autorisierung, Revisions-, Konsistenz-, Übergangs- und Lockout-Prüfung gezogen.

## 11. Technische Wiederholung

Eine vorhandene Change-ID wird vor aktueller Authority und Revision
aufgelöst.

Stimmen Actor, Zielnutzer, Scope, Intent und erwartete Revision exakt überein,
wird dieselbe resultierende Revision zurückgegeben. Weder Status noch Pointer
oder Snapshot werden erneut verändert.

Damit bleibt ein unklarer Commit-Ausgang auch nach Entzug der Actor-Authority
auflösbar.

Dieselbe Change-ID mit abweichendem Inhalt ist ein detailfreier
domänenspezifischer Konflikt und wird niemals durch Überschreiben repariert.

## 12. Konkurrenzordnung

PostgreSQL ordnet Foundation, operative Authority, Set-Revisionen, Mitglieder,
Current-Pointer und Lifecycle-Entscheidungen gemeinsam.

Nach dem Warten wird eine vorhandene Change-ID erneut aufgelöst. Zwei exakte
Retries konvergieren daher auf dasselbe Ergebnis.

Zwei unterschiedliche Änderungen von derselben erwarteten Revision können
nicht beide committen. Genau eine verschiebt den Pointer; die andere sieht
anschließend eine stale Revision und endet neutral.

Statusänderungen am Actor werden über dieselben persistenten Authority-Zeilen
mit späteren fachlichen Trust- und Membership-Entscheidungen geordnet.

## 13. Fehlergrenzen

Neutrales `None` vereinheitlicht unbekannte oder inaktive Foundation,
fehlende Authority, stale Revision, unzulässigen Übergang und Lockout-Schutz.

Change-ID-Inhaltsabweichung bleibt ein eigener detailfreier Konflikt.

Unbrauchbare Typen oder Generatorwerte, beschädigte Snapshots, fehlendes
Schema, nicht unterstützte Dialekte sowie Encoding-, Decoding-, Constraint-,
Transaktions- und Datenbankfehler werden als detailfreie technische
Nichtverfügbarkeit vereinheitlicht.

Kein Ergebnis oder Fehler enthält SQL, DSN, Tabellen-, Constraint-, Treiber-
oder Bestandsdetails. `BaseException` bleibt ungefangen.

## 14. Sicherheitswirkung

Eine committierte Deaktivierung sperrt den Actor bei der nächsten aktuellen
Authority-Auflösung. Die Session selbst bleibt nur Identität und transportiert
keine alte gecachte Berechtigung.

Ordentliche Rotation ist nun möglich: zuerst Grant oder Reactivate eines
zweiten Managers, danach Deactivate des bisherigen Managers mit der neu
entstandenen erwarteten Revision.

Bootstrap bleibt dauerhaft geschlossen. Regulärer Lifecycle verändert keine
Bootstrap-Entscheidung und kann keine revisionslose Authority-Historie
adoptieren.

## 15. Bewusst nicht enthalten

LQ-214 implementiert keine:

- Offline-Operatorgrenze oder Credential-Prüfung;
- Recovery bei Verlust aller wirksamen Manager;
- Nutzer- oder Workspace-Reaktivierung;
- Membership-, Research-Permission- oder Trust-Konfigurationsmutation;
- Migration, Seed, Route, HTTP-Endpunkt oder Startup-Ausführung;
- Settings-, Environment- oder Deployment-Allow-Schalter;
- automatische Rotation oder zeitgesteuerte Authority.

## 16. Nachweis

SQLite-Tests belegen alle drei Übergänge in beiden Domänen, vollständige
historische Snapshots, Scope-Bindung, Lockout-Schutz, stale Vorbedingungen,
späte Generatorziehung, Retry nach Entzug, Konflikte und technische
Fehlervereinheitlichung.

Zusätzliche Nachweise zeigen, dass committierter Entzug den nächsten aktuellen
Authority-Lookup sperrt.

PostgreSQL-Integrationsprüfungen belegen, dass zwei unterschiedliche
konkurrierende Grants von derselben Revision genau einen Erfolg besitzen.

## 17. Nächster Slice

LQ-215 soll getrennte owner-only Offline-Operatorgrenzen für Verankerung und
reguläre Lifecycle-Mutation beider Domänen bereitstellen.

Die Operatoren müssen stabile Change-IDs bewahren, exakte Inputs aus privaten
Dateien lesen, Ergebnisse atomar und detailfrei schreiben und dürfen weder
Recovery noch Bootstrap oder fachliche Trust-/Membership-Mutation vermischen.
