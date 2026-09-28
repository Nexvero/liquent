# LQ-546 — Manifest Handoff Alt-Regression Stabilization

## Ergebnis

LQ-546 beseitigt die sieben im LQ-545-Abschlussaudit ausgewiesenen normalen
Altregressionen.

Die Korrekturen betreffen LQ-432, LQ-438, LQ-443 und den inzwischen zu groben
Repository-Architekturguard. Sie ändern keine öffentliche Portsignatur, kein
Schema und keine Migration.

## LQ-432: beschädigte Attempt-Historie

Der autorisierte Attempt-Lookup behält das Attempt nun auch dann in seinem
Resultset, wenn keine Observation vorhanden ist.

Die Latest-Observation-Bedingung liegt dazu vollständig im `LEFT JOIN` und
nicht mehr in der `WHERE`-Klausel.

Ein unbekanntes Attempt bleibt neutral `None`. Ein vorhandenes Attempt ohne
rekonstruierbare Observation erreicht dagegen die bestehende Validierung und
endet detailfrei technisch unverfügbar.

Damit werden Abwesenheit und beschädigte Persistenz wieder getrennt.

## LQ-438: geschlossener Scope-ID-Typ

Der statische Bindingresolver prüft `ManifestHandoffRegistryScopeId` nun gegen
den tatsächlichen geschlossenen Werttyp statt gegen `str`.

Exakt konfigurierte IDs liefern wieder dasselbe unveränderliche Binding.
Unbekannte oder typfremde Werte bleiben neutral `None`.

Der Test für leere typfremde Eingabe übergibt einen leeren String direkt. Er
versucht nicht länger, einen vom Domainmodell ausdrücklich verbotenen leeren
Scope-ID-Wert zu konstruieren.

## LQ-443: Claim-Permanenz

Bei einer neuen Claim-ID wird ein bereits dauerhaft belegtes Attempt vor der
aktuellen Authorityprüfung erkannt.

Ein späterer Authorityentzug ändert deshalb nicht die permanente
Attempt-/Claim-Bindung: Ein anderer Claim bleibt detailfreier
`ManifestHandoffOwnershipConflict`.

Ein unbelegtes Attempt benötigt weiterhin aktuelle User-, Scope- und
Registryauthority und fällt bei Entzug neutral geschlossen aus.

## LQ-443: Renewal-Retry

Ein vorhandener Renewal-Fakt wird ausschließlich anhand seiner tatsächlich
persistierten Renewal-, Claim- und Ownerbindung rekonstruiert.

Die fehlerhafte Prüfung nicht selektierter Start-Observation-Spalten ist
entfernt. Ein exakter Retry liefert wieder dieselben ursprünglichen
Serverzeiten; divergenter Owner bleibt Konflikt.

Neue Renewals prüfen unverändert Claimowner und terminalen Zustand.

## Architekturguard

Reine Application-Services bleiben weiterhin frei von SQLAlchemy, FastAPI,
Transport- und Persistenzadaptern.

Explizit benannte `_composition.py`-Module bilden dagegen den vorgesehenen
Composition Root und dürfen konkrete Adapter verdrahten. Der gemeinsame
detailfreie `identity_errors`-Fehlertyp bleibt als bestehende technische
Grenze zulässig; andere Persistenzimporte in Services bleiben verboten.

Die Ausnahme ist syntaktisch eng und erteilt keine allgemeine Freigabe für
Adapterimports im Application-Layer.

## Verifikation

Die vier direkt betroffenen Testmodule bestehen mit 29 Tests.

Die vollständige normale Suite besteht mit 5021 Tests und einem erwarteten
Skip; 105 PostgreSQL-markierte Tests sind in diesem Lauf gezielt abgewählt.

`git diff --check` bleibt sauber.

## Abgrenzung

LQ-546 ergänzt keine Tabelle, Migration, Route, CLI, Entry Point,
Authorityregel, Cleanupwirkung oder Productionverdrahtung.

Der getrennte LQ-302-Mehrprozess-/Experiment-ID-Befund wird nicht verändert.

Commit, Push und Deployment sind nicht Bestandteil dieses Slices.

## Nächster Slice

LQ-547 diagnostiziert und stabilisiert den LQ-302-PostgreSQL-Mehrprozess-
Research-Worker einschließlich seiner Experiment-ID-Bindung.
