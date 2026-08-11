# LQ-186 — Atomarer Bootstrap der ersten internen Identität

## 1. Status und Ziel

Dieser Slice ist ein reiner Vertrag. Er enthält keine Python-Implementierung,
Migration, Tests, CLI, HTTP-Route, Operator-Authentisierung oder Production-
Verdrahtung.

LQ-182 verlangte atomar den ersten Nutzer, Workspace und dessen
Verwaltungsautorität. Das reicht im heutigen Produkt nicht: Liquent besitzt nur
den OIDC-Anmeldeweg, und dieser bindet eine erste externe Identität ausschließlich
über eine vorher ausgestellte `IdentityAdmissionId`. Ohne erste Admission wäre
der Verwalter dauerhaft angelegt, könnte sich aber niemals anmelden.

LQ-186 präzisiert daher die Bootstrap-Einheit: Foundation, dauerhafte
Bootstrap-Entscheidung und erste offene Admission werden in **einer**
PostgreSQL-Transaktion wirksam oder gar nicht.

## 2. Einmalige Offline-Grenze

Der Bootstrap bleibt eine interne Offline-Control-Plane-Grenze. Er ist kein
HTTP-Endpunkt, Admin-Header, Environment-Trigger, Migration-Seed, Self-Sign-up,
First-login-Provisioning und kein direkter Datenbankzugriff aus Transportcode.

Production bleibt unverdrähtet, bis ein eigener Slice die authentisierte
Operatorgrenze entscheidet. Die spätere Transportform darf die hier definierte
atomare Operation nur erreichen, nicht deren Eingaben oder Autorität ersetzen.

Die Schließung folgt weiterhin aus persistentem Zustand. Es gibt keinen
konfigurierbaren Bootstrap-Schalter und kein Flag, das einen zweiten Bootstrap
erlaubt.

## 3. Endgültige Port- und Ergebnisform

Der Implementierungsslice ergänzt genau einen operativen Port:

`IdentityAuthorityBootstrapStore.bootstrap_initial_identity(self)`

Die Methode hat außer `self` keine Parameter. Insbesondere nimmt sie keinen
UserId, WorkspaceId, AdmissionId, ProvisioningRequestId, Status, Rollennamen,
Autoritäts-Boolean, Providerwert, Claim, SessionPrincipal, Requestwert, Clock-
Wert, Retry-Flag oder freien Idempotency-Key entgegen.

Erfolg liefert `BootstrappedIdentityAuthority(user_id, workspace_id,
admission_id)`. Die Form ist frozen, slots-basiert, hashbar und alle drei Felder
sind `repr=False`; ihr `repr` enthält keinen Wert. Der interne
`ProvisioningRequestId` bleibt ausschließlich persistenter Bestandteil der
Entscheidung und wird nicht ausgegeben.

`None` ist die einheitliche fachliche Ablehnung eines nicht leeren,
nicht zu diesem Bootstrap gehörenden Bestands. Technische Unmöglichkeit erhält
eine eigene detailfreie `IdentityAuthorityBootstrapUnavailable`; konkrete
Treiber-, Identifier- oder Zustandsdetails bleiben verborgen.

## 4. Abhängigkeiten des persistenten Adapters

Der spätere PostgreSQL-Adapter erhält ausschließlich injizierte Quellen für:

- kryptografisch geeignete `UserId`;
- kryptografisch geeignete `WorkspaceId`;
- kryptografisch geeignete `ProvisioningRequestId`;
- kryptografisch geeignete `IdentityAdmissionId`;
- eine aware-UTC-Serveruhr;
- eine vorab validierte positive Admission-Lebensdauer.

Die Methode selbst nimmt diese Werte nie vom Aufrufer. Die Lebensdauer wird
beim Adapterbau fail-fast geprüft. Uhr und alle vier Generatoren werden erst
nach der persistenten Zustandsprüfung und je höchstens einmal gelesen. Es gibt
keinen automatischen Generator-Retry bei einer Kollision.

## 5. Atomarer Erstübergang

Nur wenn Nutzer-, Workspace-, Autoritäts- und Bootstrap-Entscheidungsbestand
vollständig leer sind, legt eine Transaktion gemeinsam an:

1. einen aktiven internen Nutzer;
2. einen aktiven Workspace;
3. die aktive Onboarding-Verwaltungsautorität dieses Nutzers im Workspace;
4. die historische Singleton-Bootstrap-Entscheidung;
5. einen neuen `ProvisioningRequestId` für genau diese Entscheidung;
6. eine neue offene Identity-Admission für Nutzer und Workspace mit intern
   erzeugter AdmissionId und Ablauf aus Serveruhr plus Lebensdauer.

Jede Check-, Unique-, Foreign-Key-, Clock-, Generator- oder Schreibstörung
rollt alles zurück. Es bleibt kein Nutzer ohne Admission, kein Workspace ohne
Verwalter, keine Autorität ohne Entscheidung und keine halbe Admission zurück.

## 6. Warum LQ-181 nicht nachgelagert aufgerufen wird

Ein Ablauf „Foundation committen, danach `provision_admission` aufrufen" ist
verboten. Scheitert der zweite Commit oder geht seine Antwort verloren, ist der
Bestand bereits nicht mehr leer und der Bootstrap dauerhaft geschlossen; der
erste Nutzer bliebe ohne zuverlässig auffindbare Login-Capability.

Der Bootstrap implementiert deshalb dieselben Admission-Invarianten innerhalb
seiner eigenen Transaktion. Gemeinsamer privater Persistenzcode mit LQ-181 ist
zulässig, sofern keine öffentliche API erweitert und keine zweite Transaktion
geöffnet wird. Die öffentliche LQ-181-Portsemantik bleibt unverändert.

## 7. Persistente Wiederholungsidentität

Eine neue Tabelle `identity_authority_bootstrap_decisions` enthält genau eine
historische Zeile. Ihr datenbankseitig konstanter Singleton-Schlüssel ist auf
den einzigen zulässigen Wert beschränkt und verweist restriktiv auf die erste
Admission. Nutzer, Workspace und `ProvisioningRequestId` werden verlustfrei aus
dieser unveränderlichen Admission und ihren Foundation-Referenzen aufgelöst.

Die Zeile ist kein Aktivierungsflag: Löschen, Umschalten oder Neuerzeugen öffnet
den Bootstrap nicht. Sie ist der dauerhafte Nachweis des abgeschlossenen
Vorgangs und die Wiederholungsidentität nach einem unklaren Commit-Ausgang.

Die Migration enthält keine Zeile. Der erste erfolgreiche Bootstrap schreibt
Entscheidung und Admission atomar. Ein fehlender Entscheidungsdatensatz bei
irgendeinem vorhandenen Nutzer-, Workspace- oder Autoritätsbestand ist
fachliche Ablehnung und wird niemals repariert oder adoptiert.

## 8. Exakte Wiederholung

Existiert die vollständige Bootstrap-Entscheidung bereits, liefert ein späterer
Aufruf exakt dieselben drei Identifier. Er liest weder Uhr noch Generator,
verlängert keinen Ablauf, erzeugt keine zweite Admission, überschreibt keinen
Status und öffnet eine bereits konsumierte Admission nicht wieder.

Das gilt auch nach Deaktivierung, Autoritätsentzug oder Admission-Konsum: Der
Aufruf wiederholt nur die historische Antwort und trifft keine neue
Autorisierungs- oder Lifecycle-Entscheidung. Eine neue Login-Capability braucht
später eine reguläre autorisierte Onboarding-Grenze.

Ist Entscheidungszeile oder referenzierter Zustand strukturell unvollständig,
ist das technische Nichtverfügbarkeit, kein neuer Bootstrap und kein `None`.

## 9. Konkurrenz und unklarer Commit-Ausgang

Zwei Teilnehmer dürfen gleichzeitig einen leeren Bestand beobachten. Die
Singleton-Eindeutigkeit und die PostgreSQL-Transaktion entscheiden genau einen
Erstschreiber; dessen Foundation und Admission bleiben als einzige erhalten.
Der andere Teilnehmer rollt seine erzeugten Werte vollständig zurück, lädt die
committete Entscheidung und liefert dasselbe beobachtbare Ergebnis.

Nach Verbindungsabbruch oder verlorener Antwort ruft die authentisierte
Offline-Grenze dieselbe parameterlose Methode erneut auf. Der persistente
Entscheidungsdatensatz findet den abgeschlossenen Vorgang wieder; der Operator
muss keinen geheimen Idempotency-Key speichern oder neu übermitteln.

Es gibt keinen In-Process-Lock, keinen Cache, keinen stale fallback, keine
zweite Transaktion und keinen automatischen Wiederholungsloop.

## 10. Fehler- und Datenschutzgrenze

Normale unerwartete Exceptions sowie strukturell beschädigte oder unlesbare
Entscheidungen werden in die detailfreie Bootstrap-Unavailable-Form übersetzt.
Sie verlässt die Grenze ohne Cause oder Context. Eine bereits saubere eigene
Exception darf nur mit leerer Kette identisch weitergereicht werden;
`BaseException` bleibt ungefangen und objektidentisch.

Kein Identifier, DSN, Tabellen-, Constraint- oder Treibertext, Generatorwert,
Zeitwert oder Admission-Detail erscheint in Exception, `repr`, Log, Trace oder
Metriklabel. LQ-186 führt selbst kein Logging und keine Telemetrie ein.

## 11. Nachweise des Implementierungsslices

SQLite belegt Modell-, Signatur-, Migrations- und portable Constraintform, aber
nicht die atomare Leereentscheidung. PostgreSQL muss zusätzlich beweisen:

- vollständigen Erstübergang und exakte referenzielle Zuordnung;
- Rollback bei Fehlern an jeder Schreibstufe;
- idempotente Wiederholung ohne Abhängigkeiten und ohne Ablaufverlängerung;
- Wiederholung nach Konsum ohne Wiederöffnung;
- Ablehnung eines fremden nicht leeren Bestands;
- zwei echte konkurrierende Teilnehmer mit genau einer gespeicherten Foundation
  und demselben Ergebnis;
- unvollständige Entscheidungsreferenzen als detailfreie technische Störung.

## 12. Nicht enthalten und Folge

Nicht enthalten sind konkrete CLI, Operator-Authentisierung, HTTP, Environment-
Trigger, Production-Wiring, reguläres Onboarding, Membership, Rollen, Research-
Permissions, Autoritätsvergabe/-entzug, Login-Transaktions- oder
Sessionpersistenz und Änderungen am OIDC-Callback.

Als Nächstes folgt die Implementierung dieses atomaren Bootstrap-Stores samt
Migration und PostgreSQL-Konkurrenznachweis. Danach folgen die authentisierte
Offline-Aufrufgrenze, die reguläre atomare Onboarding-Entscheidung, persistente
Login-Transaktionen und Sessions und zuletzt LQ-177.
