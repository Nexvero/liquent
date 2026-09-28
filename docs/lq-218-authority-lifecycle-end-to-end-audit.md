# LQ-218 — Authority Lifecycle End-to-End Audit

## 1. Ergebnis

LQ-218 auditiert die vollständigen Authority-Ketten nach LQ-205 bis LQ-217.

Die beiden Management-Authority-Domänen besitzen nun sichere unterstützte
Grenzen für:

- initialen Bootstrap;
- einmalige Verankerung;
- reguläres Grant, Deactivate und Reactivate;
- owner-only Offline-Bedienung;
- eng begrenzte Recovery;
- owner-only Recovery-Bedienung.

Diese Ketten sind intern vollständig und getrennt. Der End-to-End-Audit deckt
jedoch einen vorgelagerten Restblocker auf: Aus einem leeren Bestand kann der
unterstützte Workflow nur genau den ersten Nutzer und Workspace erzeugen.

Es existiert noch keine reguläre Nutzer- oder Workspace-Lifecycle-Grenze, die
einen zweiten aktiven internen Nutzer für Rotation, Membership-Provisionierung
oder spätere Recovery bereitstellt.

LQ-177 bleibt deshalb konkret blockiert. LQ-218 führt keine neue Mutation ein
und erklärt den Gesamtpfad nicht künstlich für betriebsbereit.

## 2. Auditumfang

Geprüft wurden:

- Migration-Head und persistente Foundations;
- Identity- und erste Authority-Bootstraps;
- OIDC-Trust- und Membership-Authority-Verankerung;
- reguläre Authority-Lifecycle-Adapter;
- fachliche Trust- und Membership-Mutationen;
- Lifecycle- und Recovery-Operatoren;
- PostgreSQL-Konkurrenznachweise;
- Runtime-Prozessisolation;
- der unterstützte Weg aus einem vollständig leeren migrierten Bestand.

Der Slice verändert keine Ports, Adapter, Migration, CLI oder Runtime-
Verdrahtung. Neue Tests und Dokumentation halten ausschließlich die vorhandene
Systemgrenze fest.

## 3. Geschlossene Runtime- und Trust-Grundlagen

LQ-184 bis LQ-197 haben persistente Identität, Admission,
Login-Transaktionen, Sessions, aktive OIDC-Konfiguration, Verifier-
Composition, Process-Wiring, Membership-Lookup und Research-Autorisierung
geschlossen.

Der reale HTTP-Prozess besitzt die erforderliche Engine- und HTTP-Client-
Ownership und aktiviert OIDC sowie Research nur als vollständige opt-in
Abhängigkeitsgruppen.

`SessionPrincipal` bleibt reine Actor-Identität. Er trägt weder Membership,
Research-Permission noch Management-Authority.

## 4. Geschlossene fachliche Control Plane

LQ-198 bis LQ-203 implementieren globale OIDC-Trust-Authority,
revisionsgebundene Trust-Konfiguration, autorisierte Aktivierung, Rotation und
Deaktivierung sowie den getrennten Offline-Operator.

LQ-206 bis LQ-210 implementieren workspacebezogene Membership-Management-
Authority, vollständige Membership-Snapshots, explizite Research-Permissions,
autorisierte Mutation und einen getrennten Offline-Operator.

Damit sind aktive OIDC-Konfiguration und gewöhnliche Membership-/Permission-
Verwaltung keine verbleibenden LQ-177-Blocker mehr.

## 5. Geschlossene initiale Bootstrap-Erreichbarkeit

LQ-205 stellt Identity- und globale Trust-Authority-Bootstrap über einen
kontrollierten owner-only Offline-Prozess bereit.

LQ-208 und LQ-210 ergänzen den einmaligen Membership-Management-Authority-
Bootstrap pro Workspace und seine kontrollierte Bedienung.

Ein leerer migrierter Bestand kann deshalb unterstützt genau folgende erste
Fakten erhalten:

- einen aktiven internen Nutzer;
- einen aktiven internen Workspace;
- dessen Onboarding-Management-Authority;
- globale Trust-Management-Authority für diesen Nutzer;
- Membership-Management-Authority dieses Nutzers im ersten Workspace.

Keine Migration, kein Startup und kein erster Login erfindet diese Fakten.

## 6. Geschlossene Authority-Lifecycle-Ketten

LQ-211 entscheidet den getrennten Lifecycle- und Recovery-Vertrag.

LQ-212 bis LQ-214 implementieren stabile IDs, vollständige Set-Revisionen,
einmalige Bootstrap-Verankerung und reguläre Grant-, Deactivate- und
Reactivate-Mutation mit erwarteter Revision und Lockout-Schutz.

LQ-215 stellt beide regulären Ketten über getrennte owner-only Operatoren
bereit.

LQ-216 und LQ-217 implementieren und bedienen getrennte Recovery-
Entscheidungen, die ausschließlich historisch bereits autorisierte aktive
Nutzer in einem Scope ohne wirksamen Manager reaktivieren.

Damit sind die früheren Trust- und Membership-Management-Authority-
Lifecycle-/Recovery-Lücken als Fähigkeiten geschlossen.

## 7. Nachweis vom leeren Bestand bis zur Verankerung

Der neue End-to-End-Test startet mit einem leeren migrierten Store und nutzt
ausschließlich unterstützte Adapter.

Er erzeugt atomar den ersten Nutzer und Workspace, bootstrapped beide
Management-Authorities und verankert anschließend:

- genau eine globale OIDC-Trust-Authority-Set-Revision;
- genau eine Membership-Management-Authority-Set-Revision im ersten
  Workspace;
- die jeweiligen Current-Pointer und Anchor-Entscheidungen.

Der Store enthält danach weiterhin genau einen Nutzer und einen Workspace.

## 8. Warum Rotation einen zweiten Nutzer benötigt

Sichere Manager-Rotation verlangt nach LQ-211 und LQ-214:

1. Grant oder Reactivate eines zweiten aktiven historisch geeigneten Nutzers;
2. neue Set-Revision;
3. Deactivate des bisherigen Managers gegen diese neue Revision.

Ohne zweiten Nutzer würde Deactivate den letzten wirksamen Manager entfernen.
Die LQ-214-Grenze lehnt dies korrekt neutral ab und zieht keine neue Revision.

Dieser Lockout-Schutz ist kein Fehler und darf für den End-to-End-Nachweis
nicht abgeschwächt werden.

## 9. Fehlender regulärer Nutzer-Lifecycle

Der aktuelle Port- und Operatorbestand besitzt keinen regulären Workflow für:

- Anlage eines weiteren internen Nutzers;
- Aktivierung oder Deaktivierung eines internen Nutzers;
- kontrollierte Stilllegung mit Authority- und Membership-Auswirkungsprüfung;
- Auswahl oder Anlage eines weiteren Workspace außerhalb des einmaligen
  initialen Bootstrap;
- sichere Wiederaktivierung eines für Recovery benötigten historischen
  Nutzers.

Onboarding und Admission erstellen keine neuen `identity_users`. Sie
autorisieren und binden externe Identitäten ausschließlich an bereits intern
bestimmte Zielnutzer.

Direktes SQL ist kein zulässiger Ersatz für diese fehlende Lifecycle-Grenze.

## 10. Auswirkung auf Membership-Provisionierung

LQ-209 kann Membership und Research-Permissions nur für einen bereits
existierenden aktiven Zielnutzer setzen.

Der leere unterstützte Startpfad besitzt aber nur den Bootstrap-Manager. Eine
zweite reale Person kann ohne reguläre Nutzeranlage weder als Membership-Ziel
noch als zweiter Membership-Manager auftreten.

Damit ist die Membership-Mutation selbst vollständig, aber die vorgelagerte
Zielnutzer-Provisionierung im Shared Environment noch nicht vollständig
unterstützt.

## 11. Auswirkung auf Recovery

Recovery darf ausschließlich einen aktiven internen Nutzer mit bereits
inaktiver historischer Authority reaktivieren.

Mit nur einem Bootstrap-Nutzer kann kein solcher sicherer Reservepfad erzeugt
werden:

- reguläre Deaktivierung seiner letzten Authority wird korrekt abgelehnt;
- externe Deaktivierung dieses Nutzers lässt keinen aktiven Recovery-Zielnutzer;
- Recovery darf Nutzerstatus nicht selbst ändern;
- Re-Bootstrap bleibt dauerhaft geschlossen.

Die Recovery-Grenze funktioniert für korrekt vorbereitete Mehrnutzerbestände,
kann aber den fehlenden Nutzer-Lifecycle nicht ersetzen.

## 12. Workspace-Lifecycle bleibt ebenfalls offen

Der initiale Identity-Bootstrap erzeugt genau einen Workspace. LQ-208 kann
Membership-Management-Authority nur für einen bereits existierenden aktiven
Workspace bootstrappen.

Es gibt keinen regulären unterstützten Workspace-Erstellungs-, Aktivierungs-
oder Deaktivierungsworkflow.

Für den ersten Shared-Environment-Workspace ist das kein Startblocker. Für
dauerhafte Multi-Workspace-Verwaltung und vollständiges Offboarding bleibt es
jedoch eine offene Control-Plane-Grenze.

## 13. Runtime-Isolation bleibt korrekt

Die End-to-End-Nachweise bestätigen erneut, dass HTTP-Entrypoint und App-
Factory keine Bootstrap-, Anchor-, Lifecycle-, Recovery- oder Operatormodule
importieren.

Die Runtime veröffentlicht keine Identity-, Authority-, Membership-, Trust-
oder Recovery-Managementroute.

Diese Isolation ist kein Restblocker. Die fehlende Nutzer-/Workspace-
Lifecycle-Fähigkeit gehört in eine separate kontrollierte Control Plane, nicht
in HTTP-Startup oder Browser-Sessions.

## 14. Kein zulässiger Ersatzweg

Folgende Abkürzungen bleiben ausdrücklich unzulässig:

- direkte SQL-Anlage weiterer Nutzer oder Workspaces;
- Migration-Seeds;
- Environment-Allow oder Admin-Header;
- Login-basierte Selbstfreischaltung;
- automatische Nutzeranlage aus OIDC-Claims;
- Wiederöffnung des initialen Bootstrap;
- Abschwächung des letzten-Manager-Schutzes;
- Recovery-Auswahl einer nie historisch autorisierten Person.

Ein End-to-End-Test darf solche Abkürzungen nicht verwenden, um einen
unzutreffenden Readiness-Claim zu erzeugen.

## 15. LQ-177-Entscheidung

LQ-177 ist weitgehend implementiert, aber weiterhin konkret blockiert.

Geschlossen sind:

- Runtime-Composition und Prozess-Ownership;
- persistente Sessions, Trust und Membership-Auflösung;
- initiale Identity- und Authority-Bootstraps;
- OIDC-Trust-Konfigurationsverwaltung;
- Membership- und Research-Permission-Verwaltung;
- beide Management-Authority-Lifecycles und Recoveries;
- getrennte owner-only Operatorgrenzen.

Verbleibend sind:

1. regulärer persistenter Nutzer-Lifecycle;
2. regulärer persistenter Workspace-Lifecycle;
3. darauf aufbauender vollständiger Mehrnutzer-End-to-End-Nachweis für
   Rotation, Offboarding, Membership und Recovery;
4. erst danach der endgültige Shared-Environment-Readiness-Audit.

## 16. Sichere Folgeordnung

Der nächste Slice muss zuerst den Vertrag für reguläre Nutzer- und Workspace-
Lifecycle-Grenzen entscheiden.

Er muss insbesondere Creation-Authority, stabile IDs, active/inactive-
Übergänge, letzte-Manager-Auswirkungen, Onboarding-Zielbestimmung,
Nichtwiederverwendung, Retry, Konkurrenz, Recovery und Operator-Ownership
klären.

Erst danach dürfen Persistenz, Mutation und Operatoren implementiert werden.
Der Mehrnutzer-End-to-End-Nachweis folgt zuletzt.

## 17. Bewusst nicht enthalten

LQ-218 implementiert keine:

- Nutzer-, Workspace-, Authority- oder Membership-Mutation;
- neue Ports, Modelle, Exceptions, Tabellen oder Migrationen;
- CLI, Route, Settings-, Environment- oder Startup-Verdrahtung;
- direkte SQL-Provisionierung im Produktpfad;
- neue Recovery-Eligibility;
- Abschwächung bestehender Lockout- oder Scope-Grenzen;
- Behauptung vollständiger Production-Betriebsbereitschaft.

## 18. Nächster Slice

LQ-219 soll den persistenten Nutzer- und Workspace-Lifecycle-Vertrag
entscheiden.

Der Vertrag muss die minimale sichere Control Plane für zusätzliche interne
Nutzer und Workspaces festlegen, ohne OIDC-Self-Sign-up, Rollenvermischung,
Bootstrap-Wiederöffnung oder implizite Authority-Vergabe einzuführen.
