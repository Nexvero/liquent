# LQ-185 — Persistente Identity-Autoritätsgrundlage

## 1. Ergebnis

LQ-185 implementiert die in LQ-184 festgelegte Daten- und Modellgrundlage für
interne Nutzer, Workspaces und workspacebezogene Onboarding-Autorität. Der
Slice trifft noch keine Autorisierungsentscheidung und bietet keinen
operativen Port, Lookup, Adapter oder Schreibanwendungsfall.

## 2. Domänenmodelle

`identity.authority` enthält drei getrennte Status-Enums:

- `InternalUserStatus`: aktiv oder inaktiv;
- `WorkspaceStatus`: aktiv oder inaktiv;
- `WorkspaceOnboardingAuthorityStatus`: aktiv oder widerrufen.

`InternalUserRecord`, `WorkspaceRecord` und
`WorkspaceOnboardingAuthorityRecord` sind frozen, slots-basiert, hashbar und
haben ausschließlich Pflichtfelder. Identifier bleiben in `repr` verborgen.
Leere oder nicht exakt als String vorliegende IDs sowie ein Status aus dem
falschen Enum werden neutral per `ValueError` ohne den Wert abgelehnt.

Die Typen sind absichtlich getrennt, obwohl ihre Stringwerte teilweise gleich
sind. Nutzer-Lifecycle, Workspace-Lifecycle und Autoritätsentzug bleiben
eigenständige fachliche Zustände.

## 3. Revision 20260811_0003

Die additive Migration folgt ausschließlich auf `20260811_0002` und erzeugt:

- `internal_users` mit bytegenauem Primärschlüssel und geschlossenem
  aktiv/inaktiv-Status;
- `workspaces` mit derselben stabilen ID- und Lifecycle-Grenze;
- `workspace_onboarding_authorities` mit zusammengesetztem Primärschlüssel,
  aktiv/widerrufen-Status und restriktiven Foreign Keys.

Alle identitätstragenden Schlüssel sind `LargeBinary` und müssen nicht leer
sein. Die Statuswerte sind kleine geschlossene ASCII-Aufzählungen. Es gibt
keinen Surrogatschlüssel, Namen, Zeitstempel, Auditwert, Bootstrap-Marker,
Schalter oder Seed.

## 4. Nachgezogene referenzielle Integrität

Die bislang bewusst vertagten Referenzen erhalten jetzt restriktive Foreign
Keys:

- External-Identity-Bindung auf den internen Nutzer;
- Admission-Zielnutzer auf den internen Nutzer;
- Admission-Zielworkspace auf den Workspace.

Die Migration erzeugt keine fehlenden Ziele und bereinigt keine verwaisten
Bestandsdaten. Ein solcher Bestand lässt das Upgrade atomar fehlschlagen. Ein
Downgrade entfernt zuerst diese abhängigen Schlüssel, dann die
Autoritätszuordnung und zuletzt Workspace- und Nutzertabelle. Kein `CASCADE`
löscht bestehende Identity-Daten.

## 5. Port- und Autorisierungsgrenze

`ports.py` ist unverändert. Insbesondere existiert kein `has_authority`, kein
Status-Lookup und kein CRUD-Port. Die neuen Records sind persistierbare Fakten,
aber keine separat lesbare Freigabeentscheidung.

Damit kann kein späterer Anwendungsfall Autorität in einer Transaktion lesen
und nach einem zwischenzeitlichen Entzug in einer zweiten Transaktion noch eine
Entscheidung schreiben. Der Bootstrap und die reguläre Onboarding-Entscheidung
erhalten jeweils erst in ihrem eigenen Slice eine atomare, schreibende
Portoperation.

## 6. Lifecycle und Retention

LQ-185 führt keine Lifecycle-Mutation ein. Inaktive Nutzer und Workspaces sowie
widerrufene Autoritätszuordnungen sind darstellbarer historischer Zustand;
Reaktivierung oder Neuvergabe wird nicht entschieden. Primärschlüssel und
restriktive Foreign Keys verhindern eine Löschung, die vorhandene Bindungen,
Admissions oder Zuordnungen verwaisen ließe.

## 7. Nachweisgrenzen

Die portable Suite belegt Modellinvarianten, exakte Tabellen und benannte
Constraints, geschlossene Statuswerte, referenzielle Integrität und den
geordneten Downgrade auf SQLite.

Der markierte PostgreSQL-Pfad ist normativ. Er prüft die fünf tatsächlichen
Foreign Keys und dass ein Upgrade von Revision `20260811_0002` mit einer
verwaisten vorhandenen Referenz scheitert und die Revision unverändert lässt.
Bestehende PostgreSQL-Identity-Tests legen ihre benötigten Nutzer und
Workspaces nun explizit als Foundation-Fixtures an; ihre Fachlogik bleibt
unverändert.

## 8. Nicht enthalten und Folge

Nicht enthalten sind Bootstrap, Nutzer- oder Workspace-Erzeugungsgrenze,
Autoritätsvergabe oder -entzug, reguläre Onboarding-Entscheidung, Admission-
Provisionierung, Membership, Rollen, Research-Permissions, HTTP, CLI und
Production-Wiring.

Als Nächstes folgt der einmalige, atomare Offline-Bootstrap. Erst danach folgt
die reguläre atomare Onboarding-Entscheidung, anschließend persistente Login-
Transaktionen und Sessions und zuletzt die Wiederaufnahme von LQ-177.
