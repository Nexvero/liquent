# LQ-186 — Persistente autorisierte Onboarding-Entscheidung

## 1. Ziel und Grenze

Dieser Slice implementiert den regulären autorisierten Onboarding-Aufrufer
zwischen der persistenten Authority-Foundation und der bestehenden
Admission-Provisionierung. Er prüft aktuelle Autorität und aktive Ziel-Fakten
und speichert die resultierende unveränderliche Entscheidung atomar.

LQ-186 provisioniert noch keine Admission und verdrahtet keinen HTTP-Endpunkt.
Es entstehen weder Nutzer, Workspace, Membership, Research-Permission noch
Management-Capability. CLI, Transport und Production-Wiring bleiben außerhalb.

## 2. Zwei getrennte Wiederholungsidentitäten

`OnboardingDecisionId` ist die vor dem ersten Schreibversuch erzeugte interne
Wiederholungsidentität des fachlichen Entscheidungsvorgangs. Sie wird bei jedem
technischen Retry unverändert verwendet, ist kein öffentlicher Idempotency-Key
und gewährt keine Autorität.

`ProvisioningRequestId` entsteht dagegen erst innerhalb der autorisierten
Schreibtransaktion. Er wird atomar genau der gespeicherten Entscheidung
zugeordnet und ist der bestehende Wiederholungshandle für LQ-181. Ein unklarer
Commit der Entscheidung wird mit derselben `OnboardingDecisionId` aufgelöst;
der Aufrufer erhält dann den bereits gespeicherten `ProvisioningRequestId`,
ohne Generatorzugriff und ohne zweite Entscheidung.

Beide IDs sind nicht leer, bytegenau, ohne Normalisierung und in `repr`
verborgen. Sie erscheinen nicht in Fehlerdetails, Logs, Traces oder
Metriklabels.

## 3. Vertrauensgrenze

`AuthorizedOnboardingDecisionStore.decide` erhält:

1. die stabile interne `OnboardingDecisionId`;
2. einen bereits authentifizierten `SessionPrincipal`;
3. den intern ausgewählten Zielnutzer;
4. den intern ausgewählten Zielworkspace.

`SessionPrincipal` identifiziert nur den Akteur. Die Signatur akzeptiert kein
Allow-Boolean, keinen Rollennamen, keine Research-Permission und keine frei
behauptete Capability. Decision-ID und Ziel-IDs autorisieren sich ebenfalls
nicht selbst.

Die spätere Transport- oder Control-Plane-Grenze muss Zielnutzer und Workspace
aus einem serverseitig kontrollierten Vorgang beziehen. LQ-186 bietet keinen
HTTP-Parser und übernimmt keine ID aus OIDC-Claim, Callback oder Token.

## 4. Atomare Authority-Entscheidung

Innerhalb derselben Schreibtransaktion muss das System of Record bestätigen:

- Akteur existiert und ist aktiv;
- Zielnutzer existiert und ist aktiv;
- Zielworkspace existiert und ist aktiv;
- der Akteur besitzt für exakt diesen Workspace die aktive
  Onboarding-Management-Capability.

PostgreSQL sperrt diese gelesenen Foundation-Zeilen für die Entscheidung. Eine
gleichzeitige Deaktivierung oder ein Capability-Entzug wird dadurch vor oder
nach der Entscheidung geordnet: Entzug vor der Prüfung ergibt keine neue
Entscheidung; ein bereits committeter Entscheid bleibt als historische Tatsache
unverändert.

Bei Autorität erzeugt der Adapter den `ProvisioningRequestId` und speichert
Decision-ID, Request-ID, Akteur, Zielnutzer und Zielworkspace gemeinsam. Alles
committet oder nichts. Kein Check-then-act über getrennte Transaktionen, kein
In-Process-Lock und kein automatischer Retry.

## 5. Wiederholung und Konflikt

Eine exakte Wiederholung derselben Decision-ID mit identischem Akteur,
Zielnutzer und Workspace liefert die gespeicherte Entscheidung unverändert.
Aktueller Status und aktuelle Authority werden dafür nicht erneut verlangt:
Der Retry rekonstruiert eine bereits committete Tatsache und erzeugt keine neue.
So bleibt auch ein unklarer Commit nach späterem Entzug auflösbar.

Dieselbe Decision-ID mit abweichendem Akteur, Zielnutzer oder Workspace ist ein
detailfreier Vertragskonflikt. Es gibt kein Überschreiben, keine neue Request-ID
und keine zweite Entscheidung. Eine Kollision der intern generierten
`ProvisioningRequestId` ist technische Nichtverfügbarkeit, kein Retry mit einem
zweiten Generatorwert.

## 6. Neutrale Ablehnung und technische Fehler

Unbekannter oder inaktiver Akteur, Zielnutzer oder Workspace sowie fehlende oder
entzogene Management-Capability ergeben einheitlich `None`. Kein Generator wird
aufgerufen und kein Datensatz geschrieben; die Antwort verrät nicht, welche
Tatsache fehlt.

Ungültiges Material, Generator-, Datenbank-, Transaktions-, Struktur-,
Constraint- oder Commitfehler sind davon getrennte detailfreie technische
Nichtverfügbarkeit. Konflikt und technische Nichtverfügbarkeit verlassen die
Grenze ohne Cause oder Context. `BaseException` bleibt ungefangen, der Adapter
hat ein konstantes wertfreies `repr` und schließt die Engine nicht.

## 7. Migration und Nachweis

Revision `20260812_0004` ergänzt ausschließlich
`authorized_onboarding_decisions`. Decision-ID ist Primärschlüssel,
Provisioning-Request eindeutig, und Akteur sowie Ziele referenzieren die
LQ-184-Foundation. Es gibt keine Seed-Daten und keine Änderung bestehender
Tabellen.

SQLite beweist Migration, Erfolg, neutrale Ablehnung, exakte Wiederholung nach
Entzug, Konflikt und Rollback. Der markierte PostgreSQL-Test beweist echte
gleichzeitige identische Entscheidungen: Beide Aufrufe konvergieren auf genau
einen gespeicherten Datensatz und denselben `ProvisioningRequestId`.

## 8. Folgeordnung

Der nächste Slice verbindet eine gespeicherte autorisierte Entscheidung mit
`IdentityAdmissionProvisioningStore.provision_admission`. Er darf Ziele und
Request-ID ausschließlich aus dieser Entscheidung übernehmen und muss den
unklaren Ausgang entlang beider stabiler Wiederholungsidentitäten behandeln.
Reguläre Membership- und Capability-Mutation, Login-Transaktionen, Sessions und
LQ-177 bleiben danach getrennte Slices.
