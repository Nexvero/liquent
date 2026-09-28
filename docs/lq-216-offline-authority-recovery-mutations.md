# LQ-216 — Offline Authority Recovery Mutations

## 1. Status und Ziel

LQ-216 implementiert eng begrenzte persistente Offline-Recovery-Mutationen für
zwei strikt getrennte Management-Authority-Domänen:

- globale OIDC-Trust-Management-Authority;
- workspacebezogene Membership-Management-Authority.

Recovery ist kein regulärer Lifecycle-Change. Sie wird ausschließlich benötigt,
wenn ein bereits verankerter Scope keinen aktuell wirksamen Manager mehr
besitzt.

Der Slice implementiert die atomare Persistenzgrenze, aber noch keinen
aufrufbaren Operatorprozess oder Credential-Workflow.

## 2. Separate Recovery-Ports

`OfflineOidcTrustAuthorityRecoveryStore` akzeptiert ausschließlich:

- domänenspezifische `OidcTrustAuthorityRecoveryId`;
- exakte Ziel-`UserId`;
- exakt erwartete `OidcTrustAuthoritySetRevisionId`.

`OfflineWorkspaceMembershipAuthorityRecoveryStore` akzeptiert zusätzlich
genau einen `WorkspaceId` und verwendet die getrennten Membership-Authority-
Recovery- und Set-Revisions-IDs.

Kein Port akzeptiert `SessionPrincipal`, Actor, Rolle, Allow-Boolean,
Authority-Liste, Status, neue Person, Recovery-Token oder resultierende
Revision.

## 3. Kein regulärer Actor

Ein `SessionPrincipal` wäre in einem vollständig geschlossenen Scope kein
sicherer Autorisierungsnachweis. Deshalb besitzt Recovery bewusst keinen
regulären Actorparameter.

Das Fehlen eines Principals gewährt jedoch nichts. Die persistente Grenze
prüft ausschließlich die enge historische Eligibility und darf erst durch
einen späteren separaten owner-only Operatorprozess erreichbar werden.

HTTP-, Login-, Callback-, Session- und Application-Startup-Pfade importieren
oder komponieren Recovery nicht.

## 4. Recovery ist nur im geschlossenen Scope zulässig

Vor jeder neuen Recovery wird der vollständige operative Authority-Bestand des
Scopes mit den aktuellen Nutzerstatus gelesen.

Existiert mindestens eine Authority, die zugleich `active` ist und einem
aktiven internen Nutzer gehört, endet Recovery neutral mit `None`.

Im Workspace-Fall muss zusätzlich der exakte Workspace existieren und aktiv
sein. Ein wirksamer Manager in einem anderen Workspace beeinflusst diesen
Scope nicht.

Damit kann Recovery keine reguläre Grant- oder Reactivate-Entscheidung umgehen.
Solange ein Manager handeln kann, bleibt ausschließlich LQ-214 zulässig.

## 5. Historische Eligibility des Zielnutzers

Der Zielnutzer muss:

1. als stabiler interner Nutzer existieren;
2. aktuell aktiv sein;
3. im exakten Scope bereits einen Authority-Fakt besitzen;
4. dort aktuell den Authority-Status `inactive` tragen;
5. als Mitglied der erwarteten vollständigen Set-Revision enthalten sein.

Recovery kann keine neue Person auswählen, keinen Authority-Fakt erstmalig
erzeugen und keine UserId aus einem anderen Scope übertragen.

Eine formal aktive Authority eines inaktiven Nutzers ist historisch sichtbar,
aber kein reaktivierbares Ziel dieser Grenze. Nutzer-Reaktivierung bleibt eine
separate Identity-Lifecycle-Aufgabe.

## 6. Aktiver Nutzer und Workspace

Recovery ändert niemals Nutzerstatus. Ist der historisch autorisierte
Zielnutzer inaktiv, endet die Entscheidung neutral.

Membership-Authority-Recovery ändert niemals Workspace-Status. Ein inaktiver
oder unbekannter Workspace bleibt geschlossen.

Die Grenzen erstellen weder Nutzer noch Workspaces und wählen keine
Ersatzidentität aus anderen Authority-Fakten.

## 7. Erwartete aktuelle Revision

Im normalen Fall muss ein Current-Pointer vorhanden sein und exakt auf die vom
Offline-Aufrufer erwartete Set-Revision zeigen.

Eine abweichende Revision ist stale und endet neutral. Es gibt kein
Last-write-wins und keinen automatischen Wechsel auf eine andere sichtbare
Revision.

Vor der Mutation muss der operative Authority-Bestand vollständig mit den
Mitgliedern dieser erwarteten Revision übereinstimmen. Abweichender oder
beschädigter Bestand ist technische Nichtverfügbarkeit, nicht stillschweigende
Reparatur.

## 8. Kontrolliert fehlender Current-Pointer

LQ-211 erlaubt Recovery gegen die aktuelle oder zuletzt bekannte
Set-Revision. LQ-216 interpretiert „zuletzt bekannt“ eng und strukturell.

Fehlt der Current-Pointer, muss die erwartete Revision:

- Ergebnis genau einer persistenten Lifecycle- oder Recovery-Entscheidung sein;
- im exakten Scope liegen;
- keine persistente Nachfolgeentscheidung besitzen;
- vollständig mit dem operativen Authority-Bestand übereinstimmen.

Nur dann ist sie eindeutig terminal und der neue Recovery-Commit darf den
Current-Pointer wiederherstellen.

Mehrdeutige, verwaiste, nicht terminale oder scopefremde Revisionen enden
neutral. Bootstrap-Bestand ohne Verankerung kann diesen Nachweis nicht erfüllen.

## 9. Atomare Recovery-Wirkung

Eine erfolgreiche Recovery erzeugt atomar:

1. Reaktivierung genau des historisch inaktiven Ziel-Authority-Fakts;
2. eine neue stabile unveränderliche vollständige Set-Revision;
3. ein Set-Mitglied für jeden Authority-Fakt des exakten Scopes;
4. Wechsel oder kontrollierte Wiederherstellung des Current-Pointers;
5. eine getrennte persistente Recovery-Entscheidung mit Recovery-ID, Ziel,
   erwarteter und resultierender Revision.

Alle anderen Authority-Status bleiben unverändert. Es wird keine reguläre
Lifecycle-Change-Entscheidung erfunden.

Alles committet oder nichts. Der Revisionsgenerator wird erst nach sämtlichen
Eligibility-, Scope-, Revisions-, Konsistenz- und Closed-Scope-Prüfungen
aufgerufen.

## 10. Getrennte Ergebnisfakten

Globale Recovery liefert ein `RecoveredOidcTrustAuthoritySet` aus Recovery-ID,
resultierender Set-Revision und Ziel-UserId.

Workspace-Recovery liefert ein
`RecoveredWorkspaceMembershipAuthoritySet` und bindet zusätzlich den exakten
WorkspaceId.

Die Ergebnisse sind unveränderlich, slotted und tragen weder Credential noch
übertragbare Authority.

## 11. Exakte technische Wiederholung

Eine vorhandene Recovery-ID wird vor allen aktuellen Eligibility-Prüfungen
aufgelöst.

Stimmen Ziel, Scope und erwartete Revision exakt überein, wird dieselbe
resultierende Revision zurückgegeben. Es entsteht keine zweite Reaktivierung,
Revision oder Recovery-Entscheidung.

Damit bleibt ein unklarer Commit-Ausgang selbst nach späterer Nutzer-,
Workspace- oder Authority-Statusänderung auflösbar.

Dieselbe Recovery-ID mit anderem Ziel, Scope oder erwarteter Revision ist ein
detailfreier domänenspezifischer Konflikt.

## 12. Konkurrenzordnung

PostgreSQL ordnet Nutzer, Workspace, operative Authorities, Set-Revisionen,
Mitglieder, Current-Pointer, Lifecycle- und Recovery-Inventare gemeinsam.

Nach dem Warten wird dieselbe Recovery-ID erneut geprüft. Exakte konkurrierende
Retries konvergieren auf dasselbe Ergebnis.

Zwei unterschiedliche Recovery-Versuche im selben geschlossenen Scope können
nicht beide committen. Die erste erfolgreiche Reaktivierung erzeugt wieder
einen wirksamen Manager; der spätere Versuch endet neutral.

Workspace-Recovery bleibt fachlich an den exakten Scope gebunden.

## 13. Ablehnung und technische Fehler

Neutrales `None` vereinheitlicht:

- vorhandenen wirksamen Manager;
- unbekannten oder inaktiven Zielnutzer;
- unbekannten oder inaktiven Workspace;
- fehlende oder nicht inaktive historische Ziel-Authority;
- stale oder nicht eindeutig terminale Revision;
- revisionslosen Bootstrap-Bestand.

Recovery-ID-Wiederverwendung mit anderem Inhalt ist ein eigener detailfreier
Konflikt.

Beschädigte Snapshots, unbrauchbare Typen oder Generatorwerte, fehlendes
Schema, nicht unterstützte Dialekte sowie Encoding-, Decoding-, Constraint-,
Transaktions- und Datenbankfehler sind detailfreie technische
Nichtverfügbarkeit.

Kein Fehler enthält Ziel, Scope, Revision, Recovery-ID, Authority-Bestand, SQL,
DSN, Tabelle, Constraint oder Treiberdetail. `BaseException` bleibt ungefangen.

## 14. Bootstrap bleibt geschlossen

Recovery liest und schreibt keine Bootstrap-Entscheidung. Bestehende Authority-
Historie hält die Bootstrap-Grenzen weiterhin dauerhaft geschlossen.

Ein Scope ohne erste Anchor-Revision ist nicht recoverbar. LQ-216 darf weder
eine Verankerung nachholen noch eine historische Revision erfinden.

Ist der letzte Bootstrap-Manager bereits vor LQ-213-Verankerung verloren,
bleibt der Zustand ein manueller Identity-/Security-Lifecycle-Blocker.

## 15. Retention und Nichtwiederverwendung

Recovery-IDs, erwartete und resultierende Revisionen bleiben dauerhaft
unterscheidbare Sicherheitsentscheidungen und dürfen nicht unter neuer
Bedeutung wiederverwendet werden.

Historische Set-Mitglieder und Recovery-Entscheidungen müssen mindestens so
lange erhalten bleiben, wie Retry, Eligibility, Audit oder weitere
Lifecycle-Entscheidungen darauf verweisen können.

Der Slice legt keine konkrete Aufbewahrungsfrist oder physische
Archivierungsstrategie fest; spätere Verfahren dürfen diese Untergrenzen nicht
unterschreiten.

## 16. Bewusst nicht enthalten

LQ-216 implementiert keine:

- CLI, owner-only Dateigrenze oder Operator-Credentials;
- HTTP-Route, UI, API, Startup- oder Deployment-Verdrahtung;
- Bootstrap, Anchor oder reguläre Lifecycle-Mutation;
- Nutzer- oder Workspace-Reaktivierung;
- neue Person, Rolle oder generische Admin-Capability;
- Membership-, Permission- oder Trust-Konfigurationsmutation;
- Migration, Seed oder Änderung bestehender Tabellen;
- automatische Recovery oder Hintergrundtask.

## 17. Nachweis

SQLite-Tests belegen globale und workspacebezogene Recovery, historische
Eligibility, Scope-Bindung, Closed-Scope-Prüfung, aktive Foundation,
Current-Pointer-Wiederherstellung, exakte Wiederholung, Konflikte und
detailfreie technische Nichtverfügbarkeit.

Die Tests erzeugen den Recovery-Zustand durch spätere Deaktivierung des
vormals wirksamen Nutzers. Unveränderliche historische Set-Revisionen werden
dabei nicht umgeschrieben.

PostgreSQL-Integrationsnachweise prüfen, dass zwei unterschiedliche
konkurrierende Recoveries desselben Scopes genau einen Erfolg besitzen.

## 18. Nächster Slice

LQ-217 soll getrennte owner-only Offline-Recovery-Operatoren für beide Domänen
bereitstellen.

Sie müssen explizite stabile Recovery-IDs, Ziel, Scope und erwartete Revision
aus privaten Dateien bewahren, Resultate atomar schreiben und dürfen weder
reguläre Lifecycle- noch Bootstrap-Kommandos enthalten.
