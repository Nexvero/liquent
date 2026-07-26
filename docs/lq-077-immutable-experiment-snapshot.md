# LQ-077 — Unveränderlicher Experiment-Snapshot

## Status

- Jeder Research-Job referenziert genau einen eingefrorenen Experiment-Snapshot.
- Dataset-Referenz und -Fingerprint, Strategieversion sowie wirksame Strategie-,
  Risiko- und Kostenparameter sind gemeinsam gebunden.
- Parameter werden als sortierte, unveränderliche Schlüssel-Wert-Paare gehalten.
- Keine Datenkopie, Persistenz, Runner-Factory oder HTTP-Route eingeführt.

## Zweck

Ein Job darf nicht von später veränderten Eingaben abhängen. Der Snapshot hält
deshalb die Identitäten, den Dataset-Fingerprint und die tatsächlich wirksamen
Parameter eines bereits validierten Experiments zusammen. Er enthält nur
skalare Werte und bleibt damit klein und eindeutig serialisierbar.

Der Snapshot kopiert keine Marktdaten. `dataset_ref` bezeichnet die gewählte
Datenbasis, `dataset_fingerprint` bindet deren geprüften Inhalt. Wie die Daten
später geladen werden, bleibt eine separate Adapterentscheidung.

## Invarianten

- Pflichtidentitäten, Titel, Dataset-Referenz und Fingerprint sind nicht leer.
- Parameter besitzen eindeutige, sortierte Schlüssel.
- Nach der Erstellung kann kein Feld neu zugewiesen werden.
- Ein Job verwendet für Titel und Evidence immer seinen gebundenen Snapshot.

## Bewusst nicht gebaut

- keine verschachtelten oder beliebigen JSON-Strukturen,
- keine Kopie historischer Daten in den Snapshot,
- keine Hash-Berechnung oder ID-Erzeugung im Domänenobjekt,
- keine Runner-, Strategy- oder DataSource-Factory,
- keine Datenbank, Queue, HTTP-Route oder Weboberfläche.

## Definition of Done

- vollständige wirksame Research-Metadaten sind gemeinsam eingefroren,
- Parameterdarstellung ist deterministisch,
- Jobs sind an genau einen Snapshot gebunden,
- ungültige leere oder nichtkanonische Eingaben scheitern fail-closed,
- vollständige Testsuite bleibt grün,
- nächster Schritt kann den Startadapter vom Snapshot zum bestehenden Runner
  gezielt spezifizieren.
