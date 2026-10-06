# Digitale Research Nutzung in Liquent

Die Änderungen erweitern die bestehende Research Umgebung und ihre Anmeldung.
Die Datenprüfung ist unabhängig von einem Research Auftrag und von Feedback.
Dieses Dokument beschreibt den implementierten Ablauf; eine Staging Veröffentlichung
und echte Kundentests müssen separat mit ihrer tatsächlichen Prüfung belegt werden.

## Daten prüfen

Unter https://staging.liquent.ai/research anmelden, eine UTF-8 CSV mit den Spalten
`timestamp,open,high,low,close,volume` und das erwartete Intervall auswählen.
Unterstützt werden 1m, 5m, 15m und 1h sowie Dateien bis 5 MiB. Zeitstempel benötigen
eine explizite UTC Zeitzone. Die Prüfung verändert keine Daten, speichert die CSV
nicht dauerhaft und legt keinen Auftrag an. Temporäre Dateien werden nach der
Prüfung entfernt. Die Befunde gelten nur für die tatsächlich geprüfte Datei.

Fehler werden beim ersten Befund abgewiesen; weitere Fehler sind möglich.
Zeitlücken einschließlich Handelskalenderpausen werden nicht automatisch toleriert.
Kurze Historie ist ein sichtbarer Hinweis, kein Renditenachweis.

## Optional genau drei Simulationen

Die bestehende Research Schreibberechtigung ist erforderlich. Das Formular in
der bestehenden Research-Seite enthält genau drei Varianten in fester Reihenfolge.
Auftragsangaben, Strategie, Parameter, Risiko, Kosten und Seed werden ausdrücklich
ausgefüllt; leere Felder sind keine Nullwerte oder Empfehlungen. Varianten-IDs
müssen eindeutig sein. Die Datenprüfung bleibt unabhängig von diesen Feldern.
Alternativ kann im ausdrücklich gewählten JSON-Modus eine eigene Konfiguration
bis 64 KiB geprüft und bearbeitet werden. Beide Modi verwenden denselben Vertrag.
Das Format und ein ausschließlich synthetisches Beispiel stehen in
`examples/research_pilot/order.json`; dieses Beispiel ist keine Empfehlung und
wird nicht automatisch in den Auftrag übernommen. Jede Variante legt Strategie,
Parameter, Risiko, Startkapital, Seed und Kosten vollständig fest.

Datei, Intervall und Konfiguration prüfen und binden. Erst danach Datenrechte und
Ausführung ausdrücklich bestätigen. Bei Änderungen werden Bindung und Zustimmung
ungültig; auch ein Wechsel zwischen Formular und JSON erfordert neue Prüfung
und Zustimmung. Nur die ausdrückliche Auftragsfreigabe speichert die Datei geschützt in
der bestehenden Datenbank und stellt den Auftrag in die bestehende Worker Queue.
Gleiche gebundene Eingaben desselben Kunden werden bei Wiederholung dem bestehenden
Auftrag zugeordnet, statt nach einem verlorenen Antwortsignal doppelt gestartet.
Datei und Rückmeldungen gehören niemals ins Repository.

## Ergebnisse verstehen

Die vorhandene Jobansicht zeigt die drei Varianten in vereinbarter Reihenfolge,
ohne Ranking. Eingaben, Fingerprints, tatsächlich gespeicherte Kosten und
Risikowirkung bleiben zugeordnet. Fehlende Werte werden nicht ergänzt oder aus
Kapitalständen rekonstruiert. Keine Signale und fehlgeschlagene Varianten sind
kein versteckter Erfolg. Die geschützte JSON Evidenz ist herunterladbar.

Ein Trade endet nach einem Datenbalken. `stop_price` berechnet nur die
Positionsgröße und führt keinen Stop-Loss aus. Der Schlusskurs dient als
Mittelkurs Proxy. Weitere wirkungslose beziehungsweise abweichend wirksame
Risikoparameter werden angezeigt; diese Semantik wird nicht geändert.

## Lokale Formularprüfung (6. Oktober 2026)

Die Formularerweiterung wurde mit ausschließlich synthetischen Daten lokal im
Browser geprüft: Datenprüfung bei leeren Strategiefeldern, verständliche Ablehnung
unvollständiger Auftragsangaben, drei Varianten in vereinbarter Reihenfolge und
identische Eingabebindung über Formular und JSON. Eine Parameteränderung hebt beide
Zustimmungen auf und sperrt die Ausführung. Der Browserlauf hat keinen Auftrag
freigegeben und ist kein Nachweis einer ausgeführten Worker-Simulation.

Gezielte automatisierte Prüfungen: 236 bestanden, eine PostgreSQL-Prüfung mangels
lokaler Test-Datenbank (`LIQUENT_TEST_DATABASE_URL`) übersprungen. Enthalten sind
bestehende HTTP-/Backend-/Ergebnisprüfungen und neue
Formular-, Zahlen-, Bindungs-, Freigabe- und Parallelitätstests. Ein unabhängiger
Review fand einen Fehler bei gleichzeitig laufender Datenprüfung und Bearbeitung
der Varianten; dieser wurde korrigiert und durch acht Regressionstests abgesichert.
Die erneute unabhängige Prüfung fand keine weiteren relevanten Befunde.

Die vollständige Testsuite auf dem unveränderten finalen Stand ergab 8303 bestandene
und 113 übersprungene Prüfungen, keine Fehler. Die übersprungenen Prüfungen sind
kein Nachweis ihrer Funktion; insbesondere bleibt die separate PostgreSQL-CI
erforderlich. Abhängigkeitsprüfung, Syntaxprüfung der Betriebs-Skripte und
`git diff --check` bestanden ebenfalls.

Diese lokale Abnahme ersetzt nicht die CI, das unveränderte Release-Gate oder die
HTTPS-Prüfung nach einer tatsächlichen Staging-Veröffentlichung.

## Anzeigepräzision und Zugangskennzeichnung

Die Ergebnis- und Kostenkarten zeigen gespeicherte Brutto-/Nettowerte, Gebühren,
Spread und Slippage mit bis zu sechs Nachkommastellen. Kleinere von null
verschiedene Beträge erscheinen in wissenschaftlicher Schreibweise, nicht als
`0,00`. Echte Nullwerte bleiben `0,00`, fehlende oder nicht endliche Werte
bleiben `Nicht verfügbar`. Gerundete Einzelbeträge können von der angezeigten
Summe abweichen; der geschützte JSON-Download enthält die ungerundeten
gespeicherten Werte. Berechnung, Evidenz und Modellgrenzen sind unverändert.

Der Research-Einstieg bezeichnet die gesamte Sitzung nicht mehr pauschal als
„Read-only“. Er beschreibt die vorhandene Auftragsliste; neue Simulationen
erfordern weiterhin die tatsächlich geprüften Schreibrechte, Eingabebindung,
Datenrechte und ausdrückliche Ausführungsfreigabe. Diese Textänderung vergibt
keine Berechtigungen. Die vorhandene Ausführungssperre bei fehlenden
Schreibrechten bleibt bestehen.

Lokale Prüfung dieser Anzeigeänderungen am 6. Oktober 2026: 88 gezielte Tests
bestanden; vollständige Suite mit 8313 bestandenen und 113 übersprungenen Tests,
keine Fehler. Die heruntergeladene Evidenz des synthetischen Staging-Auftrags
wurde mit der neuen Projektion geprüft: kleine Kosten sichtbar, Evidenz
unverändert. Abhängigkeitsprüfung und `git diff --check` bestanden. Der unabhängige
Code-Review fand keine relevanten Befunde; seine eigene Testausführung war nicht
verfügbar, die genannten Tests wurden vom Hauptagenten ausgeführt. Dies ist
keine Veröffentlichung der Anzeigeänderungen auf Staging und ersetzt weder
PostgreSQL-CI noch Release-Gate oder HTTPS-Abnahme nach Deployment.

## Freiwilliges Feedback und Preisstatus

Aufgabe, Hindernis, wahrgenommener Nutzen und Wiederverwendungsabsicht können
unabhängig eingegeben werden. Antworten werden geschützt und mit explizitem
Kennzeichen für synthetische Tests gespeichert. Selbstberichte und Absichten
sind keine Käufe. Die erste Studie ist für fünf freiwillige Nutzer vorbereitet
in `docs/research-customer-tests.md`; niemand wurde damit kontaktiert.

690 EUR ist kein aktueller Festpreis. 49 EUR und 99 EUR sind ebenfalls nur
unbestätigte Preishypothesen. Frühere Angebotsdateien sind historische Entwürfe.
Keine Bestellfunktion, Zahlung, persönliche Beratung oder individuelle
Handelsempfehlung ist eingerichtet.

## Veröffentlichung und verbleibende Betriebsgrenzen

Nur der bestehende Release Workflow mit unverändertem Sicherheitsgate darf den
Digest erzeugen. Anschließend frische geprüfte Backup Evidenz und den bestehenden
Staging Promotionsprozess verwenden. Control Plane und Worker müssen dieselbe
neue Resolver Architektur unterstützen; eine alleinige Web Veröffentlichung genügt
nicht. Die additive Migration ist `20261004_0047`.

Der Edge Proxy muss ausschließlich die dokumentierten Research Aktionen, das
digestgebundene Skript und geschützte Evidenz Downloads weiterleiten. CSV Bodies
sind durch Base64 größer als die Datei; die Aktionsrouten erlauben höchstens 7 MiB.
SRI und CSP binden das Skript, nicht beliebige Scripts oder Inline Code.
Vor HTTPS Abnahme Rollenrechte, Worker Abschluss, Ergebnisse und Downloads prüfen.

Vor echten Kunden bleiben Einwilligung, Aufbewahrungsfristen, genehmigtes
Löschverfahren, Upload Quoten und der Umgang mit abgebrochenen Aufträgen zu klären.
Formularbeschriftungen, Einheiten und der alternative JSON-Bedienweg sind im
freiwilligen Test ausdrücklich auf Verständlichkeit zu prüfen. Zahlen für Gebühren
und Slippage sind Anteile (0.01 = 1 Prozent), der Spread ein absoluter Preisbetrag
pro Einheit und Transaktionsseite. Es gibt noch keine belegte
Nachfrage oder validierten Preis. `/pilot/` bleibt bis zur geklärten Bestandsaufnahme
unverändert; siehe `docs/research-pilot-retirement.md`.
