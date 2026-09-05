# LQ-187 — Autorisiertes Identity-Admission-Onboarding

## 1. Ziel und Grenze

Dieser Slice schließt die Anwendungsfallkette zwischen der persistenten
autorisierten Onboarding-Entscheidung aus LQ-186 und der retry-sicheren
Admission-Provisionierung aus LQ-181.

`AuthorizedIdentityAdmissionOnboarding` orchestriert ausschließlich die beiden
bestehenden Ports. Es ergänzt keine Migration, Tabelle, SQL-Strategie oder
Persistenzmutation außerhalb dieser Grenzen. Kein HTTP, keine CLI und kein
Production-Wiring entstehen.

## 2. Aufrufgrenze

`onboard` erhält die interne stabile `OnboardingDecisionId`, den
authentifizierten `SessionPrincipal` sowie intern ausgewählten Zielnutzer und
Zielworkspace. Diese Werte werden ausschließlich an die LQ-186-Grenze gegeben,
damit sie eine vorhandene Entscheidung exakt wiederholt oder aktuelle Authority
und aktive Foundation-Fakten atomar neu entscheidet.

Der Workflow akzeptiert kein Authority-Boolean, keinen Rollennamen, keine
Capability und keine Research-Permission. `SessionPrincipal` identifiziert den
Akteur weiterhin nur und gewährt selbst keine Autorität.

## 3. Ausschließliche Herkunft der Provisionierung

Nur ein von `AuthorizedOnboardingDecisionStore` zurückgegebenes
`AuthorizedOnboardingDecision` darf die Provisionierung erreichen. Der
Provisioning-Aufruf übernimmt ausschließlich:

- `provisioning_request_id` aus der persistenten Entscheidung;
- `target_user_id` aus derselben Entscheidung;
- `target_workspace_id` aus derselben Entscheidung;
- die fest injizierte Admission-Lifetime des Anwendungsfalls.

Die ursprünglich am Workflow präsentierten Ziele werden am Provisioning-Port
nicht erneut verwendet. Damit kann ein Aufrufer zwischen Authority-Entscheidung
und Provisionierung weder Nutzer noch Workspace austauschen. Decision-ID oder
Sessiondaten werden ebenfalls nicht an den Provisioning-Port weitergegeben.

## 4. Lifetime als feste Richtlinie

Die Admission-Lifetime ist eine positive `timedelta`-Richtlinie, die beim Bau
des Workflows injiziert wird. Sie ist kein freier Parameter jedes
Onboarding-Aufrufs. Ungültige Richtlinien werden vor jedem Portzugriff
abgewiesen.

Jede technische Wiederholung derselben Workflow-Konfiguration verwendet daher
denselben Lifetime-Wert. Zusammen mit dem gespeicherten
`ProvisioningRequestId` und den gespeicherten Zielen erfüllt sie den exakten
LQ-181-Wiederholungsvertrag, ohne Ablauf zu verlängern oder eine zweite
Admission zu erzeugen.

## 5. Ergebnis und Wiederholung

Neutrales `None` der Decision-Grenze wird unverändert zu `None`; der
Provisioning-Port wird dann nicht aufgerufen. Eine erfolgreiche Entscheidung
führt zu genau einem Provisioning-Aufruf und liefert dessen
`IdentityAdmissionId` unverändert zurück.

Bei unklarem Ausgang wird der gesamte Anwendungsfall von außen mit derselben
`OnboardingDecisionId` und derselben Konfiguration erneut aufgerufen. LQ-186
rekonstruiert denselben `ProvisioningRequestId`; LQ-181 rekonstruiert dieselbe
Admission. Der Workflow führt selbst keinen Retry aus, erzeugt keine ID und
rät keinen Ausgang.

## 6. Fehlergrenze

Konflikte und technische Nichtverfügbarkeit der beiden Ports werden
objektidentisch weitergegeben. Der Workflow fängt oder klassifiziert sie nicht
neu und tarnt technische Fehler nie als neutrales `None`. Scheitert die
Decision-Grenze, wird Provisionierung nicht berührt; scheitert Provisionierung,
wird kein zweiter Aufruf versucht.

Der Workflow besitzt ein konstantes wertfreies `repr`. Weder Ports noch
Lifetime, Decision-ID, Request-ID, Admission-ID, Nutzer oder Workspace werden
darin sichtbar. `BaseException` bleibt ungefangen.

## 7. Nicht enthalten

Keine Nutzer-, Workspace-, Membership-, Rollen-, Capability- oder
Research-Permission-Erzeugung oder -Mutation. Keine Identity-Bindung, kein
Login-Start, Callback, Session-Lifecycle, Transport, CSRF, Operator-CLI oder
Production-Composition.

Dieser Slice macht insbesondere die LQ-181-Provisionierungsgrenze nicht
öffentlich. Sie bleibt eine interne administrative Abhängigkeit, die nur mit
den Werten der gespeicherten Entscheidung aufgerufen wird.

## 8. Nachweis und Folgeordnung

Portnahe Tests beweisen Aufrufreihenfolge, Zielherkunft, feste Lifetime,
neutrales Stoppen, unveränderte Fehlerweitergabe und unterlassene automatische
Retries. Ein markierter PostgreSQL-Test verbindet die realen LQ-186- und
LQ-181-Adapter und beweist auf deren normativem Runtime-Pfad, dass eine exakte
Wiederholung auf genau eine Entscheidung und eine Admission konvergiert.

Als nächste separate Slices folgen die kontrollierte Production-Composition
dieser internen Kette sowie weiterhin persistente Login-Transaktionen und
Sessions. Eine mögliche Transport- oder Operator-Grenze braucht einen eigenen
Sicherheitsvertrag und darf nicht aus diesem Anwendungsfall abgeleitet werden.
