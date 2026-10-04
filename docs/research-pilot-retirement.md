# Separaten /pilot/-Bereich prüfen und kontrolliert zurückbauen

## Entscheidung und Grenze

Die Produktentwicklung erfolgt ausschließlich in der bestehenden Research-Umgebung
mit bestehender Anmeldung. `/pilot/` ist keine Grundlage für weitere Produktentwicklung.
Dieses Dokument ist ein Prüf- und Freigabeplan, kein Lösch- oder Stop-Auftrag.
Keine gespeicherten Daten löschen, möglicherweise genutzten Dienste stoppen,
Credentials widerrufen oder Infrastruktur entfernen, solange Nutzung und
Datenklassifikation ungeklärt sind. Ein Rückbau ist hier nicht als erfolgt bestätigt.

## Zunächst nur lesende Bestandsaufnahme

Für jede Ressource eine geschützte Inventarzeile erfassen: Betreiber/Zuständigkeit,
Route/Deployment, Dienst und Abhängigkeiten, Datenablage, Datenart, mögliche Nutzer,
letzte nachweisbare Nutzung, Zugriffsrechte, Aufbewahrungsgrund, Backup und
Wiederherstellungsverfahren. Keine Secrets oder Kundendatensätze in dieses Dokument kopieren.

Prüfen: Reverse-Proxy-/DNS-Routen, Prozess- und Containerdefinitionen, Jobs/Timer,
Volumes/DBs, CSV-Uploads, Ergebnisse, Freigaben, Feedback, Auditdaten,
Credential-Ablagen und Verweise aus Dokumentation. Vorhandene Quelltexte oder
ein fehlender sichtbarer Link beweisen weder Deployment noch Nichtnutzung.
Logs nur zweckgebunden und mit bestehenden Datenschutzrechten lesen.

## Klassifikation und Übernahme

- Synthetische Demonstrationen klar von echten Kundenaufträgen und Feedback trennen.
- Unklar klassifizierte Daten nicht als Testdaten behandeln. Verantwortlichen klären.
- Geeignete reine Validierungs-/Runner-/Berichtsfunktionen nach Tests in bestehende
  Research-Verträge übernehmen; keine zweite Anmeldung oder Parallel-Jobverwaltung.
- Datenmigration/-export nur nach ausdrücklicher Freigabe für konkrete Ablagen,
  Empfänger, Rechtebindung und Umfang. Bestehende Freigaben nicht pauschal übertragen.
- Eigentümerbindung, Eingabefingerprint, Reihenfolge, Modellversion und Auditkette
  bei genehmigter Übernahme erhalten und kontrollieren; Wiederherstellung testen.

## Voraussetzung für einen späteren Rückbau

1. Vollständige Inventarliste und bestätigte Klassifikation/Verantwortung.
2. Bestehende Research-Umgebung funktional abgenommen; Rückfallplan vorhanden.
3. Aktive Nutzer und Abhängigkeiten geklärt; keine unbemerkte Unterbrechung.
4. Erforderliche genehmigte Exporte/Backups geprüft; Aufbewahrungsfristen geklärt.
5. Ausdrückliche Freigabe für exakt benannte Routen, Dienste und Datenmaßnahmen.

Erst danach getrennt planen: Hinweise/Verweise umstellen, Zugänge kontrolliert
auslaufen lassen, Dienste deaktivieren und zuletzt genehmigte Daten-/Ressourcenmaßnahmen.
Weiterleitung nicht blind einrichten: alte IDs, Methoden, Uploads und Freigaben
haben möglicherweise andere Semantik. Jede Phase mit Verantwortlichem,
Zeitpunkt, Kontrolle und Rückfall dokumentieren. Derzeit bleibt die operative
Entscheidung bis zur Inventarisierung und Klärung offen.
