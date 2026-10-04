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

Die bestehende Research Schreibberechtigung ist erforderlich. Eine eigene JSON
Konfiguration bis 64 KiB enthält genau drei ausdrücklich bestimmte Varianten.
Das Format und ein ausschließlich synthetisches Beispiel stehen in
`examples/research_pilot/order.json`; dieses Beispiel ist keine Empfehlung und
wird nicht automatisch in den Auftrag übernommen. Jede Variante legt Strategie,
Parameter, Risiko, Startkapital, Seed und Kosten vollständig fest.

Datei, Intervall und Konfiguration prüfen und binden. Erst danach Datenrechte und
Ausführung ausdrücklich bestätigen. Bei Änderungen werden Bindung und Zustimmung
ungültig. Nur die ausdrückliche Auftragsfreigabe speichert die Datei geschützt in
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
JSON Konfiguration ist derzeit ein fortgeschrittener Bedienweg und im freiwilligen
Test ausdrücklich auf Verständlichkeit zu prüfen. Es gibt noch keine belegte
Nachfrage oder validierten Preis. `/pilot/` bleibt bis zur geklärten Bestandsaufnahme
unverändert; siehe `docs/research-pilot-retirement.md`.
