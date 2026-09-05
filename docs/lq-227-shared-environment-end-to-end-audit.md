# LQ-227 — Shared Environment End-to-End Audit

## 1. Ergebnis

LQ-227 versucht den abschließenden integrierten LQ-177-Nachweis aus einem
leeren migrierten Bestand ausschließlich über unterstützte Prozessgrenzen.

Der Audit stoppt fail-closed an einer konkreten operativen Lücke: Der initiale
Identity-Bootstrap erzeugt die ersten User- und Workspace-Lifecycle-Revisionen,
gibt deren IDs im geschützten Resultat jedoch nicht zurück.

Die regulären User- und Workspace-Lifecycle-Operatoren verlangen genau die
jeweilige erwartete Current-Revision. Kein unterstützter Offline-Prozess stellt
diese initialen Werte bereit.

LQ-177 bleibt deshalb trotz vollständiger Persistenz- und Mutationsadapter
operativ blockiert. LQ-227 erfindet keinen direkten SQL-Ersatz.

## 2. Vorgesehene integrierte Kette

Der Audit sollte ohne Abkürzung verbinden:

1. Migration auf den exakten Head;
2. initialen Identity- und Lifecycle-Authority-Bootstrap;
3. reguläre Anlage eines zweiten Nutzers;
4. reguläre Anlage eines zweiten Workspace;
5. OIDC-Trust- und Membership-Authority-Rotation;
6. Membership- und Research-Permission-Vergabe;
7. beobachtbaren Research-Zugriff über persistente Session und Membership;
8. Membership- beziehungsweise Permission-Entzug und spätere Verweigerung;
9. neutral geschlossene Recovery bei noch wirksamem Manager;
10. getrennten Disaster-Recovery-Nachweis unter dessen engen Vorbedingungen.

Die Kette darf weder IDs noch Revisionen aus Datenbanktabellen ablesen.

## 3. Unterstützter Start

`liquent-initial-bootstrap identity` besitzt eine kontrollierte owner-only
Prozessgrenze.

Sie erzeugt bei vollständig leerem Bestand atomar:

- ersten aktiven Nutzer;
- ersten aktiven Workspace;
- erste Onboarding-Manager-Bindung;
- erste User-Lifecycle-Authority;
- erste Workspace-Lifecycle-Authority;
- vollständige erste User-Lifecycle-Revision;
- vollständige erste Workspace-Lifecycle-Revision.

Der Bootstrap bleibt nach Erfolg geschlossen und migriert nicht selbst.

## 4. Tatsächliches Bootstrap-Resultat

Das exklusive Resultat enthält ausschließlich:

- `user_id`;
- `workspace_id`.

Es enthält weder `user_revision_id` noch `workspace_revision_id`.

Das ist keine Vertraulichkeitsanforderung aus dem bisherigen Vertrag. Beide
Revisionen sind opake technische Optimistic-Concurrency-Identitäten, die der
Operator für den unmittelbar folgenden regulären Schritt benötigt.

## 5. Vorbedingung der regulären Nutzeranlage

`liquent-user-lifecycle create` akzeptiert strukturell zu Recht keine
caller-supplied Ziel-UserId.

Sein Request verlangt aber zwingend:

- Actor-UserId;
- stabile User-Lifecycle-Change-ID;
- `expected_revision` als exakte aktuelle vollständige Nutzerrevision.

Ohne die initiale Revision kann der sichere zweite Nutzer nicht über diesen
Prozess angelegt werden. Weglassen oder Raten wird fail-closed verworfen.

## 6. Vorbedingung der regulären Workspaceanlage

`liquent-workspace-lifecycle create` verlangt entsprechend:

- Actor-UserId;
- stabile Workspace-Lifecycle-Change-ID;
- bestehenden aktiven ersten Onboarding-Manager;
- exakte aktuelle vollständige Workspace-Revision.

Auch diese initiale Revision verlässt den Bootstrap-Prozess nicht. Der zweite
Workspace ist daher auf dem unterstützten Betriebsweg ebenfalls nicht
erreichbar.

## 7. Kein unterstützter Current-Revision-Lookup

Keiner der owner-only Operatoren besitzt ein `inspect`-, `status`-,
`current-user-revision`- oder `current-workspace-revision`-Kommando.

HTTP-App und Runtime-Entrypoint veröffentlichen bewusst keine Control-Plane-
Leseroute. Das ist weiterhin korrekt.

Auch die beiden Lifecycle-Runbooks benennen nur eine unabhängig geprüfte
Revision als Vorbedingung, aber keinen unterstützten Weg, diese aus dem
System of Record zu erhalten.

## 8. Einordnung des LQ-226-PostgreSQL-Nachweises

LQ-226 beweist korrekt die atomare Persistenzkette auf PostgreSQL.

Der Test ruft den Bootstrap-Adapter direkt auf und injiziert deterministische
Generatoren für beide initialen Revisionen. Der Testcode kennt die Werte daher
bereits vor dem regulären Operatoraufruf.

Das ist ein valider Adapter- und Datenbanknachweis, aber kein Beleg dafür, dass
ein realer Operator die Revision nach sicherer Zufallserzeugung beobachten
kann.

LQ-227 ersetzt diesen Unterschied nicht durch Testwissen.

## 9. Warum direktes SQL unzulässig bleibt

Ein Datenbankquery auf die beiden Current-Tabellen würde die fehlenden Werte
technisch liefern, ist aber keine kontrollierte Produktgrenze.

Direktes SQL hätte keine festgelegte:

- owner-only Ein- und Ausgabegrenze;
- Detail- und Fehlerbegrenzung;
- Prozess- und Engine-Ownership;
- exakte Shape-Validierung;
- Audit- und Betriebsanleitung;
- Garantie gegen zusätzliche Bestandsausgabe.

LQ-177 und LQ-218 verbieten diesen Ersatz ausdrücklich.

## 10. Keine Revision aus IDs oder Zählerständen

Revisionen sind sicher erzeugte opake IDs. Sie dürfen nicht aus UserId,
WorkspaceId, Change-ID, Zeitstempel, Tabellenzahl oder Migrationsrevision
abgeleitet werden.

Raten kann nur neutral scheitern und wäre keine betriebliche Lösung.

Ein fester Initialwert würde den bestehenden Zufalls- und
Nichtwiederverwendungsvertrag abschwächen und ist nicht zulässig.

## 11. Keine Lockerung des Optimistic-Concurrency-Vertrags

Der erste reguläre Create darf nicht `expected_revision: null` akzeptieren.

Nach dem Bootstrap existiert bereits ein vollständiger Bestand. Eine
revisionslose Mutation könnte konkurrierende oder veraltete Operatorannahmen
nicht sicher vom aktuellen Store binden.

Die richtige Korrekturrichtung ist Beobachtbarkeit der bereits erzeugten
Revisionen, nicht Abschwächung ihrer Pflicht.

## 12. Recovery ist nicht der Ersatzweg

Authority-Recovery erzeugt weder Nutzer noch Workspace und liefert keine
Lifecycle-Bestandsrevision.

Sie darf ausschließlich unter einem bereits historisch vorbereiteten
Authority-Bestand ohne wirksamen Manager eine inaktive historische Authority
reaktivieren.

Im gesunden integrierten Workflow muss Recovery neutral geschlossen bleiben.
Ein erfolgreicher Disaster-Zustand kann durch reguläre APIs wegen
Last-Manager- und User-Drain-Schutz bewusst nicht künstlich erzeugt werden.

## 13. Nachweis

Neue Audit-Tests führen den echten Identity-Bootstrap-Operator auf einem
leeren migrierten Store aus und prüfen das exakte owner-only Resultat.

Sie bestätigen:

- nur UserId und WorkspaceId verlassen den Bootstrap;
- beide benötigten initialen Revisionen fehlen;
- beide regulären Operatoren verlangen `expected_revision`;
- kein Offline-Operator besitzt einen Current-Revision-Lookup;
- Runtime und Runbooks enthalten keinen SQL- oder Tabellen-Shortcut.

Der Audit benötigt keine neue Migration und mutiert keine Produktgrenze.

## 14. LQ-177-Entscheidung

Alle fachlichen Mutations- und Runtime-Fähigkeiten sind implementiert, aber
die unterstützte Inbetriebnahmekette ist noch nicht vollständig ausführbar.

LQ-177 bleibt konkret blockiert an der fehlenden kontrollierten Übergabe der
initialen User- und Workspace-Lifecycle-Revisionen vom Bootstrap an die
regulären Operatorprozesse.

Eine Production- oder Shared-Environment-Freigabe wird nicht behauptet.

## 15. Kleinste sichere Folgelösung

Der nächste Slice muss eine kontrollierte revisionsbezogene Beobachtbarkeit
entscheiden.

Naheliegende sichere Varianten sind:

- additive Ausgabe beider erzeugter Revisionen im erfolgreichen und exakt
  rekonstruierten Identity-Bootstrap-Resultat; oder
- ein separater owner-only read-only Operator, der ausschließlich beide
  Current-Revision-IDs aus einem konsistenten Store liefert.

Die Wahl muss Retry nach verlorenem Bootstrap-Resultat, bestehende bereits
bootstrappte Installationen und detailfreie technische Nichtverfügbarkeit
berücksichtigen.

## 16. Bewusst nicht enthalten

LQ-227 implementiert keine:

- Änderung am Bootstrap-Resultat;
- neue Lookup-, Port-, Adapter- oder Operatorgrenze;
- revisionslose Lifecycle-Mutation;
- Migration, Tabelle, Seed oder festen Initialwert;
- direkte SQL-Betriebsanleitung;
- HTTP-, UI-, Settings- oder Startup-Verdrahtung;
- Recovery-Erweiterung;
- Production-Freigabe.

## 17. Nächster Slice

LQ-228 soll den Vertrag für kontrollierte Lifecycle-Revision-
Beobachtbarkeit festlegen.

Er muss Bootstrap-Erfolg und exakten Retry beziehungsweise Rekonstruktion,
bereits vorhandene kanonische Bestände, owner-only Ausgabe, minimale Shapes,
Current-Konsistenz und detailfreie technische Nichtverfügbarkeit entscheiden,
ohne Mutation oder Authority-Ausweitung einzuführen.

## 18. Schließung durch LQ-229

LQ-229 implementiert den LQ-228-Vertrag. Das Identity-Bootstrap-Resultat
enthält nun beide initialen Lifecycle-Revisionen, und exakte kanonische
Recovery rekonstruiert denselben Vier-Felder-Shape.

Ein erneuter integrierter Test verwendet ausschließlich diese geschützte
Ausgabe, um einen zweiten Nutzer und anschließend einen zweiten Workspace über
die regulären Operatoren zu erzeugen. Der in diesem Audit gefundene
Revision-Übergabeblocker ist damit geschlossen.
