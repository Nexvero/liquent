# LQ-593 — Local Docker Client Supervisor Engine Integration

## Ergebnis

LQ-593 verbindet den LQ-591-Client ohne neue Composition mit dem bestehenden
`LocalDockerManifestHandoffSupervisorEngine`.

## Create-Pfad

Der Engineadapter sucht zuerst nach derselben Creation-ID.

Bei belegter Abwesenheit erzeugt der Client genau einen Container und
inspiziert ihn vollständig.

Der Adapter validiert anschließend Digest, Profil, Labels und Sicherheitswerte
erneut und rekonstruiert den geschlossenen Created-Record.

## Terminal-Pfad

Die Client-Waitübersetzung bewahrt `exited` und `dead` unverändert.

Der Adapter akzeptiert weiterhin ausschließlich diese beiden Zustände als
terminal.

Clientantworten erteilen keine fachliche Capability oder Authority.

## Trennung

LQ-593 ergänzt keine automatische Servicefactory, keinen Clientbesitz im
Lifespan und keinen Docker-Socket-Mount.

Die konkrete Writer-/Recovery-Capabilityprimitive bleibt der letzte
process-ownable LQ-483-Blocker vor erneutem Production-Wiring-Audit.

## Nächster Slice

LQ-594 schließt Client-, Adapter-, Architektur- und Diffaudit gemeinsam ab.
