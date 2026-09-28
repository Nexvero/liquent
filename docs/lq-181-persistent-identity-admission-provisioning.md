# LQ-181 — Persistente Identity-Admission-Provisionierung

## 1. Ziel und Grenze

Dieser Slice implementiert die in LQ-178 entschiedene interne
Provisionierungsgrenze auf dem mit LQ-179 bewiesenen PostgreSQL-Pfad und dem in
LQ-180 vollständig angelegten Schema. Er ergänzt keine Migration.

Ein bereits autorisierter, späterer Onboarding-Aufrufer kann damit genau eine
Admission für einen internen Nutzer und Workspace anlegen. Der Aufrufer selbst
und das Production-Wiring bleiben ausdrücklich offen. Es entsteht weder ein
HTTP-Endpunkt noch Self-Sign-up, Nutzer-, Workspace-, Membership-, Rollen- oder
Berechtigungserzeugung. Callback, Login-Start und Runtime-Konsum bleiben
unverändert.

## 2. Interner Wiederholungshandle

`ProvisioningRequestId` ist ein frozen, slots-basierter und repr-freier
Werttyp. Sein Wert ist exakt ein nicht leerer eingebauter `str`; Subklassen und
Normalisierung sind ausgeschlossen. Der Handle ist weder Admission-Capability
noch OIDC-State und wird nicht exportiert, geloggt oder in Fehlertexte
übernommen.

Der getrennte Port `IdentityAdmissionProvisioningStore` erhält Handle,
`target_user_id`, `target_workspace_id` und positive `lifetime`. Er erzeugt die
AdmissionId und Ablaufzeit selbst. Der bestehende Runtime-Port erhält keine
Administrationsmethode.

## 3. Erster Aufruf

Der Adapter validiert Handle, Ziele und Lifetime, bevor er eine Transaktion
öffnet. Ist der Handle unbekannt, liest er die injizierte aware-Zeit genau
einmal und den injizierten AdmissionId-Generator genau einmal. Anschließend
werden AdmissionId, Handle, Ziele, Lifetime in ganzen Mikrosekunden,
`expires_at = now + lifetime` und der offene Konsumzustand atomar gespeichert.

Eine unbrauchbare Uhr, ein falscher Generatorwert, ein Überlauf oder eine
AdmissionId-Kollision ist technische Nichtverfügbarkeit. Es gibt keinen
Ersatzwert, keine versteckte Uhr und keinen zweiten Generator- oder
Schreibversuch.

## 4. Exakte Wiederholung

Ein vorhandener Handle wird unter Zeilensperre gelesen. Stimmen Nutzer,
Workspace und Lifetime byte- beziehungsweise mikrosekundengenau überein, wird
die bereits gespeicherte AdmissionId zurückgegeben. Uhr und Generator werden
nicht berührt, `expires_at` wird nicht verlängert und kein Zustand
überschrieben. Das gilt auch nach dem Konsum: Eine Admission wird nie wieder
geöffnet.

Weicht eine der drei fachlichen Eingaben ab, folgt ausschließlich
`IdentityAdmissionProvisioningConflict`. Die Exception trägt nur ihren neutralen
Code; weder vorhandene Daten noch die abweichende Eingabe werden sichtbar.

## 5. Unklarer Commit und Konkurrenz

Die eindeutige `provisioning_request`-Spalte ist die Wiederholungsentscheidung.
Hat ein erster Aufruf möglicherweise committet, wiederholt der Aufrufer mit
demselben Handle und erhält die gespeicherte AdmissionId.

Zwei konkurrierende Aufrufe dürfen beide zunächst keinen Datensatz sehen. Die
Einfügung läuft deshalb in einem Savepoint. Nur eine Verletzung des strukturiert
aus der Treiberdiagnose gelesenen Constraints
`uq_identity_admissions_provisioning_request` gilt als erwartetes Rennen. Danach
wird der bereits gespeicherte Datensatz in derselben äußeren Transaktion geladen
und nach denselben
Regeln entschieden:

- identische Eingaben erhalten dieselbe AdmissionId;
- abweichende Eingaben ergeben genau einen sauberen Konflikt;
- jede andere Constraint- oder Datenbankverletzung bleibt technisch.

Meldungstext wird nie geparst. Es gibt keinen In-Process-Lock, kein Retry und
keine zweite Admission. PostgreSQL entscheidet die Konkurrenz über getrennte
Engines und Transaktionen.

## 6. Fehler- und Datenschutzgrenze

`IdentityAdmissionStoreUnavailable` bezeichnet ausschließlich technische
Unmöglichkeit; der Konflikt bleibt davon getrennt. Beide Klassen haben keine
Detailparameter. Eine bereits saubere neutrale Exception bleibt objektidentisch,
eine Exception mit Restkette wird ersetzt, und jede andere normale Exception
wird neutralisiert. Austretende Fehler besitzen weder Cause noch Context.
`BaseException` bleibt ungefangen.

Das Adapter-`repr` ist konstant und enthält weder Engine, DSN, Uhr, Generator,
Handle, AdmissionId, Nutzer noch Workspace. Keine dieser Angaben gelangt in
Logs, Telemetrie oder Metriklabels.

## 7. Nachweis und Nicht-Ziele

Die portnahen Tests sichern Form, Signaturen und die Trennung der Fehlerklassen.
Der markierte PostgreSQL-Pfad beweist ersten Insert, unklaren Commit, exakte
Wiederholung ohne Uhr und Generator, unveränderten konsumierten Zustand,
Konflikte für alle fachlichen Eingaben, technische ID-Kollision sowie echte
gleichzeitige identische und abweichende Aufrufe. Beim abweichenden Rennen muss
der gespeicherte Nutzer dem tatsächlich erfolgreichen Teilnehmer entsprechen.

Lokal ohne DSN werden nur die PostgreSQL-Fälle sichtbar übersprungen; CI führt
sie gegen die wegwerfbare Datenbank aus. SQLite bleibt außerhalb des
Nebenläufigkeitsnachweises. Dieser Slice ergänzt keinen autorisierten Aufrufer,
kein Production-Wiring, keine Retention-Löschung und keine Änderungen an
Login-Transaktionen oder Sessions.
