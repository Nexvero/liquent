# LQ-075 — Minimal HTTP-/Job-Vertrag

## Status

- Der öffentliche Vertrag für einen bereits validierten Research-Job ist
  festgelegt.
- Der Vertrag bildet die vorhandenen Identitäten, Zustände und Evidence ab,
  ohne ein zweites Fachmodell einzuführen.
- Noch kein Produktendpunkt wird implementiert: Der aktuelle Kern besitzt weder
  einen vollständigen Experiment-Input noch einen Job-Speicher.
- Keine Authentifizierung, Datenbank, Queue, Worker- oder Retry-Infrastruktur.

## Produktgrenze

HTTP transportiert einen fachlich vollständigen, vorab validierten
Experiment-Snapshot zur bestehenden Anwendungsgrenze. HTTP erzeugt keine
Strategieparameter, lädt keine Marktdaten nach und führt keine Orders aus.

Ein Jobstart ist erst implementierbar, wenn der Aufrufer alle eingefrorenen
Eingaben eindeutig referenzieren kann. Bis dahin wäre ein ausführbarer Endpunkt
entweder unvollständig oder würde einen nicht spezifizierten Speicher voraussetzen.

## Vorgesehene Ressourcen

| Methode und Pfad | Zweck | Erfolgsstatus |
|---|---|---|
| `POST /v1/research/jobs` | neues Experiment aus einem vollständigen, validierten Snapshot starten | `202 Accepted` |
| `GET /v1/research/jobs/{job_id}` | Zustand und neutrale Fehlerkennung lesen | `200 OK` |
| `GET /v1/research/jobs/{job_id}/evidence` | Evidence eines erfolgreichen Jobs lesen | `200 OK` |

Die Pfade sind Produktvertrag, noch keine aktivierten Routen. Bestehende
`/health/*`- und `/internal/metrics`-Endpunkte bleiben unverändert.

## Startvertrag

Der Startrequest enthält später ausschließlich:

- eine neue `job_id`,
- eine unveränderliche `experiment_id`,
- die Referenz auf einen vollständig validierten Experiment-Snapshot.

`202 Accepted` bestätigt nur die Annahme des Research-Jobs. Es bestätigt weder
Erfolg noch Ergebnisqualität. Derselbe Idempotency-Schlüssel darf nicht
unbemerkt einen zweiten Job erzeugen; konkrete Speicherung und Ablaufzeit des
Schlüssels werden erst zusammen mit der Persistenz festgelegt.

## Statusantwort

Die Statusantwort enthält genau:

- `job_id`, `experiment_id`,
- einen Zustand aus dem bestehenden `ResearchJobStatus`,
- optional `error_code` ausschließlich bei `Failed`,
- einen Evidence-Link ausschließlich bei `Succeeded`.

Interne Exception-Texte, Stacktraces, Dateipfade und Strategy-Signale werden
nicht als Fehlerdetails veröffentlicht. `execution_failed` bleibt zunächst der
einzige neutrale Ausführungsfehler.

## Evidence-Antwort

Die Evidence-Antwort verwendet die vorhandene `BacktestExperimentSummary`.
Es entsteht kein paralleles HTTP-Evidence-Modell. Ein Lauf ohne Signale ist eine
gültige erfolgreiche Evidence. Für nicht erfolgreiche Jobs liefert der
Evidence-Pfad keine Teil-Evidence.

## Fehlersemantik

| Status | Bedeutung |
|---|---|
| `400 Bad Request` | syntaktisch ungültiger Request |
| `404 Not Found` | Job oder Evidence existiert nicht |
| `409 Conflict` | Identitäts- oder Lifecycle-Konflikt |
| `422 Unprocessable Entity` | fachlich unvollständiger oder ungültiger Snapshot |
| `500 Internal Server Error` | unerwarteter Transportfehler ohne interne Details |

Ein fachlicher Runnerfehler bleibt ein lesbarer Job im Zustand `Failed`; er
wird nicht nachträglich als erfolgreicher HTTP-Start umgedeutet.

## Implementierungsgate

Die drei Routen dürfen erst aktiviert werden, wenn folgende kleine Lücke
geschlossen ist:

1. Ein vollständiger, unveränderlicher Experiment-Snapshot ist definiert.
2. Eine minimale Job-Ablage besitzt eindeutige Lese- und Schreibsemantik.
3. Der bestehende `InMemoryResearchJob` bleibt alleinige Lifecycle-Logik.
4. Contract-Tests beweisen Status-, Fehler- und No-Signal-Semantik.

Dieses Gate verhindert einen Demo-Endpunkt, der Eingaben oder Persistenz nur
vortäuscht.

## Bewusst nicht gebaut

- kein In-Memory-Repository als vorweggenommene Persistenzabstraktion,
- keine Authentifizierung oder Mandantenfähigkeit,
- keine Pagination, Filterung oder Jobliste,
- keine WebSockets, Progress-Events oder Cancellation,
- keine OpenAPI-Veröffentlichung,
- keine Broker-, Paper-, Live- oder externe Datenfunktion,
- kein Release oder Deployment.

## Definition of Done

- Ressourcen, Zustände, Erfolgs- und Fehlersemantik sind eindeutig,
- der Vertrag verwendet vorhandene Identitäten, Lifecycle und Evidence,
- unvollständige Eingaben scheitern fail-closed,
- interne Fehlerdetails bleiben privat,
- Aktivierung ist an einen vollständigen Snapshot und minimale Ablage gebunden,
- kein spekulativer Produktcode oder Infrastrukturaufbau erfolgt.
