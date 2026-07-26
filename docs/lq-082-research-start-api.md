# LQ-082 — Research-Start-API

## Status

- `POST /v1/research/jobs` nimmt einen vollständigen Experiment-Snapshot an.
- Die Route existiert nur bei explizit injiziertem `ResearchRunnerResolver`.
- Der lokale Resolver kann einen Job synchron ausführen; die Antwort bleibt
  vertragsgemäß `202 Accepted` und verweist auf Status beziehungsweise Evidence.
- Ungültige Auflösung und doppelte Job-IDs liefern neutrale 422-/409-Codes.

## Aktivierungsgrenze

Ohne Resolver registriert die App keine Start-Route und antwortet mit 404. Ein
Deployment kann dadurch nicht versehentlich eine nur teilweise konfigurierte
Research-Ausführung veröffentlichen. Die bestehenden Lese- und Betriebsrouten
bleiben davon unabhängig.

## Request

Der Request enthält Job- und Experiment-ID, Titel, Dataset-Referenz und
-Fingerprint, Strategieversion sowie vollständige Strategie-, Risiko- und
Kostenparameter. Pydantic läuft strikt; Strings werden nicht still in Bool- oder
Zahlenwerte umgewandelt.

## Fehler

- `research_inputs_unresolvable` (`422`): Snapshot oder lokale Auflösung ungültig.
- `research_job_conflict` (`409`): `job_id` existiert bereits.

Interne Pfade, Hashwerte aus der tatsächlichen Datei und Exception-Texte werden
nicht in der Antwort ausgegeben.

Nicht endliche technische Kennzahlen wie eine unendliche `profit_factor` werden
an der JSON-Grenze als `null` dargestellt. Der Research-Kern und seine
Berechnung bleiben unverändert; die HTTP-Antwort bleibt standardkonformes JSON.

## Bewusst nicht gebaut

- kein Datei-Upload, keine Jobliste und keine Löschung,
- keine Authentifizierung oder Mandantenfähigkeit,
- keine Queue, Nebenläufigkeit oder WebSockets,
- keine externe Datenquelle, Strategie v1 oder Optimierung,
- kein Release oder Deployment.

## Definition of Done

- ohne Resolver bleibt der Startpfad geschlossen,
- vollständiger lokaler Snapshot erzeugt einen beobachtbaren Job,
- unauflösbare Eingaben hinterlassen keinen Job,
- Duplikate überschreiben keine bestehende Evidence,
- Architektur- und vollständige Testsuite bleiben grün.
