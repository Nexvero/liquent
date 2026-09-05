# LQ-287 — Evidence-based Offline Provider Readiness Audit

## Ergebnis

LQ-287 materialisiert den LQ-286-Vertrag als konkrete, evidence-basierte
Offline-Checkliste.

Das neue Runbook
`operations/runbooks/release-environment-readiness.md` führt Scope,
Pflichtnachweise, unabhängige Attestierungen, Vollständigkeitsaudit,
detailarmes Ergebnis, Retention und Revalidierung zusammen.

Der Slice führt keinen Production-Upload und keine technische Freigabeaktion
aus.

## Warum kein automatischer Approval-Parser entsteht

Ein Parser könnte formal vorhandene Felder prüfen, aber weder
Provider-Ownership noch Credential-Scope, TLS-Trust, Egress, Hosthärtung oder
die Unabhängigkeit realer Reviewer aus sich selbst beweisen.

Ein caller-geliefertes `approved`-Feld wäre deshalb nur eine untrusted
Behauptung und keine Authority-Auflösung.

LQ-287 hält die Entscheidung bewusst im eingeschränkten betrieblichen
Evidence-Record und fügt kein Produktmodell, Datenbankflag oder Runtime-Allow
hinzu.

## Gebundener Scope

Die Checkliste verlangt stabile Bindung von:

- Decision-ID und Environment;
- kanonischem HTTPS-Origin;
- Package `liquent` und genau einem Ziel;
- nicht geheimer Credential-Identität;
- Anwendungsversion und Operational-Bundle-SHA-256;
- Publication-Host und Prozesskonto;
- Reviewrevision und Gültigkeitsfenster.

Eine Änderung startet eine neue Review. Bestehende Records werden nicht
umgeschrieben oder auf einen anderen Scope übertragen.

## Evidence-Familien

Pflichtnachweise sind getrennt für:

- Provider- und Package-Ownership;
- create-only Protokoll und GET-Readback;
- minimalen Credential-Scope und Revocation;
- TLS, DNS, Trustpfad und Egress;
- Publication-Host und Prozessisolation;
- Monitoring, Unknown Outcome und Incidentweg;
- Deploymenttrennung, Backup, Health und Rollback.

Jedes Evidenceobjekt wird nur über stabile Referenz und lowercase SHA-256
gebunden. Secretwerte und private Infrastrukturpfade bleiben ausgeschlossen.

## Kein Production-Probe

Providersemantik muss aus Dokumentation, Accountkonfiguration oder einer
providerrepräsentativen Nicht-Production-Umgebung hervorgehen.

Die Checkliste führt keinen DNS-Lookup, TLS-Handshake, Credentialread,
Providerrequest, Datenbankzugriff, Upload oder Deployment aus.

Fehlende Evidence bleibt `unavailable`; sie wird nicht durch spontane
Productiondiagnostik ergänzt.

## Vier getrennte Attestierungen

Provider-/Package-, Security-, Operations- und Release-Perspektive attestieren
denselben finalen Evidence-Set-Digest und dieselbe Reviewrevision.

Actor-Referenzen dokumentieren Separation of Duties, werden aber nicht zu
Application-Rollen oder Publication-Authorities.

Geänderte Evidence invalidiert die betroffene Attestierung.

## Offline-Vollständigkeitsaudit

Ein nicht vorbereitender Reviewer bestätigt read-only:

- alle Checklistenpunkte ohne Placeholder;
- Erreichbarkeit und Hashgleichheit aller Evidenceobjekte;
- identischen Scope über alle Nachweise;
- vier passende Attestierungen;
- aktuelles Gültigkeitsfenster;
- fehlende neuere Revocation oder Scopeänderung;
- Abwesenheit von Secrets und sensitiven Rohdaten.

Der Audit ruft keine Productionkomponente auf.

## Detailarmes Ergebnis

Außerhalb des eingeschränkten Records wird ausschließlich eine Outcome-Familie
offengelegt:

- `approved`;
- `rejected`;
- `expired`;
- `revoked`;
- `unavailable`.

Welcher einzelne Credential-, Netzwerk-, Reviewer-, Provider- oder Hostcheck
scheiterte, bleibt im geschützten Record.

Nur `approved` erlaubt eine getrennte beaufsichtigte Publication-Invocation.
Es startet keinen Prozess und ersetzt keinen Handoff.

## Revalidierung und Widerruf

Unmittelbar vor einem echten Operatorstart wird der Record erneut auf Ablauf,
Widerruf, Supersession und Änderungen an Origin, Credential, Scope, Host,
Trustpfad, Providerverhalten oder Bundle geprüft.

Nicht aktuelle Records scheitern ohne Providerkontakt fail-closed.

Nach möglichem PUT wird ein späterer Widerruf als Unknown Outcome behandelt;
er behauptet nicht rückwirkend, der Providerwrite sei verhindert worden.

## Statischer Nachweis

Der LQ-287-Test prüft, dass die Checkliste:

- alle LQ-286-Scope- und Evidence-Familien enthält;
- vier getrennte Attestierungen verlangt;
- Hashgleichheit und Gültigkeit offline prüft;
- detailarme Outcomes festlegt;
- Production-Probes, Secrets und automatische Starts verbietet;
- Publication, Deployment, Rollback und Withdrawal getrennt hält.

## Technischer Bestand

LQ-287 ändert keinen Produktionscode, Port, Typ, Schema, SQL, Migration, CLI,
Entry Point oder Operational-Bundle-Format.

Es entsteht kein Credential-, Netzwerk-, Provider-, Git-, Datei- außerhalb der
zwei Dokumente oder Deploymentwrite.

Head bleibt `20260819_0025`; das Bundle bleibt bei 20 Entry Points und 19
Operatormodulen.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit 3401 Tests und 588
bestehenden Warnungen.

## Nächster Slice

LQ-288 sollte den vollständigen Release-Bereich abschließend auf verbleibende
interne Blocker, widersprüchliche Runbooks und ungeschützte Productionclaims
reauditieren, ohne externe Wirkung auszuführen.
