# LQ-341 — Read-only Runtime Cleanup Claim Inspector

## Ergebnis

LQ-341 installiert `liquent-disposable-postgres-cleanup-reconcile` als strikt
read-only Inspector für offene LQ-339-`runtime_only`-Cleanup-Claims.

Er klassifiziert die geschlossene LQ-340-Zustandsmatrix und verändert weder
Claim, Evidence, Container, Netze noch Volume.

## Neue Reconciliation-Autorisierung

Der Command verlangt eine separate aktuelle owner-only Autorisierung mit
Operation exakt `inspect_disposable_postgres_runtime_cleanup`.

Sie bindet Cleanup-Reconciliation-ID, ursprüngliche Cleanup-ID, Run, Phase,
Source, Image, Compose, Reconciliationkette, alle Evidence- und
Autorisierungshashes, Scope `runtime_only`, getrennte Identitäten und ein
UTC-Fenster von höchstens einer Stunde.

Unbekannte Felder, doppelte Schlüssel, gleiche Identitäten, stale Zeit,
freier Scope oder Hashabweichung enden detailfrei unavailable.

Die frühere Cleanup-Autorisierung wird nur an ihrem historischen gültigen
Mittelpunkt verifiziert. Sie wird nicht als aktuelle Löschbefugnis verlängert.

## Vollständige historische Kette

Der Inspector lädt ursprüngliche Run-, Reconciliation-,
Claim-Reconciliation-, Dispositions- und Cleanup-Autorisierungen erneut.

Der bestehende read-only Dispositionsresolver prüft Staging-, LQ-332- und
LQ-333-Evidence einschließlich ihrer privaten SHA-256-Bindungen erneut.

Nur eine konsistente historische Disposition `cleanup_review_eligible` darf
Claim oder Ressourcen erreichen.

Caller liefern keine Ressourcennamen, Ausgänge, letzten Schritte,
Allow-Booleans oder Dockerargumente.

## Claim- und Evidencepriorität

Claim- und Evidencename werden ausschließlich aus dem vollständigen SHA-256
der Cleanup-ID abgeleitet.

Finale LQ-339-Evidence wird zuerst owner-only und vollständig gegen dieselbe
kanonische Bindung geprüft. Bei exakter Evidence lautet der Ausgang
`final_evidence_present`, ohne Docker und ohne Claimfreigabe.

Fehlen finale Evidence und Claim gemeinsam, lautet der Ausgang `not_found`
ebenfalls ohne Docker.

Ein vorhandener Claim muss regulär, owner-only, einfach verlinkt und
kanonisches JSON sein. Er bindet alle LQ-339-Fakten und eine gültige
zeitzonenbehaftete Startzeit.

Beschädigte, fremde oder widersprüchliche Claim-/Evidencezustände bleiben
technisch unavailable.

## Aktuelle Ressourcenbeobachtung

Nur ein exakter Claim ohne finale Evidence erreicht Docker.

Der Inspector validiert absoluten Dockerpfad, SHA-gebundenes Composefile und
beide owner-only Environmentdateien.

Ein read-only Compose-Render leitet den exakten Container, Application-Netz,
Data-Netz und das Datenvolume erneut aus dem geschlossenen Modell ab.

Danach folgen ausschließlich exakte Ressourcenlisten. Nur vorhandene
erwartete Objekte werden inspiziert.

Alle Prozesse verwenden temporäres leeres CWD, `LANG=C`, `LC_ALL=C`, keine
Shell sowie feste Zeit- und Outputgrenzen.

## Geschlossene Zustandsmatrix

Das Volume muss vorhanden und exakt rungebunden bleiben. Danach gelten:

- `runtime_intact`: Container läuft gesund und beide Netze besitzen
  ausschließlich seinen Endpoint;
- `container_stopped`: Container ist gestoppt oder beendet, seine statische
  Image-, Mount-, Port- und Netzwerkbindung bleibt exakt und beide Endpoints
  bestehen;
- `container_removed`: Container fehlt, beide Netze bestehen ownergebunden
  und endpointfrei;
- `application_network_removed`: Container und Application-Netz fehlen, das
  Data-Netz besteht ownergebunden und endpointfrei;
- `runtime_removed_evidence_missing`: Container und beide Netze fehlen, das
  Volume besteht exakt weiter.

Die statische Prüfung eines gestoppten Containers normalisiert nur den
beobachteten Laufzustand intern für dieselbe bestehende Isolationsprüfung. Sie
verändert kein Dockerobjekt.

## Konflikt und technische Fehler

Ein vollständig lesbarer unmöglicher Reihenfolgepräfix ergibt `conflict`.

Dazu gehören fehlendes oder fremdes Volume, Container bei fehlendem Netz,
Application-Netz ohne Data-Netz, zusätzliche Endpoints sowie abweichende
Image-, Mount-, Port-, Netzwerk- oder Projektbindung.

Malformed Output, uneindeutige Namensliste, Nonzero, stderr, Timeout,
Truncation oder Hard Kill bleibt unavailable und wird nicht als Konflikt oder
Abwesenheit ausgegeben.

## Nachweisbare Read-only-Grenze

Der Operator enthält keinen Stop-, Start-, Remove-, Disconnect-, Down-, Kill-
oder Prunepfad.

Er schreibt keine Datei, legt keinen Reconciliation-Claim an, persistiert
keine neue Evidence und entfernt auch bei finalem Zustand keinen Cleanup-
Claim.

Er liest keine Docker-Events, Logs, Historie, SQL- oder Volumeinhalte und
rekonstruiert keine verlorene Prozessbestätigung.

Kein Ausgang autorisiert eine spätere Mutation automatisch.

## Neutrale Ausgabe

Die CLI schreibt nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_reconciliation` und einen geschlossenen
Ausgang.

IDs, Hashes, Ressourcen, Pfade, Zeitwerte, Identitäten und Fehlerdetails
bleiben privat. Technische Nichtverfügbarkeit endet ohne stdout oder stderr.

## Tests

Fake-basierte Tests decken alle fünf Sequenzzustände, unmögliche Reihenfolge,
finale Evidence vor Claim und Docker sowie Claim-/Evidence-Abwesenheit ab.

Weitere Tests prüfen fremde Claimbindung, technischen Dockerfehler, erlaubte
read-only argv und detailfreie CLI-Ausgabe.

Kein Test verwendet oder verändert echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 36 Entry Points und 40
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-341 implementiert keine Claimfinalisierung, Reconciliation-Evidence,
Cleanupfortsetzung oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-342 sollte den Evidence-first Finalisierungsvertrag für eindeutig
beobachtete Cleanupzustände definieren.

Er muss Claimfreigabe, Evidencepersistenz und mögliche Fortsetzung strikt
trennen. Jede weitere Ressourcenmutation und insbesondere Volumenlöschung
benötigt weiterhin eine separate Autorisierung und Implementierung.
