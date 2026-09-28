# LQ-603 — Wrapper Job Document Loader Implementation Blocker Audit

## Ergebnis

LQ-603 prüft, ob der LQ-599-bis-LQ-602-Bestand unmittelbar durch einen
read-only Kindprozessloader konsumiert werden kann.

Die Entscheidung lautet: noch nicht.

Zwei konkrete konstruktive Blocker verhindern eine sichere Selbstbindung.

## Blocker 1 — Dateizugriff

LQ-601 erzeugt `job-binding.json` als Hostprozess-Eigentum mit Modus `0600`.

Der LQ-591-Client startet den Container mit dem konstruktiv konfigurierten
Benutzer `65532:65532`.

Es gibt weder chown/fchown noch eine gebundene gemeinsame UID-/GID-
Entscheidung.

Der Container kann die private Datei daher im allgemeinen Fall nicht lesen.

## Kein Aufweichen auf 0644

World-readable oder group-readable Defaults würden die private
Control-Directory-Grenze schwächen.

Eine pauschale Moduslockerung ist keine sichere Behebung.

UID, GID, Directoryexecute und Dateileserecht müssen konstruktiv gemeinsam
entschieden und direkt geprüft werden.

## Blocker 2 — zirkulärer Runtime-Anchor

Das LQ-600-Dokument enthält die Runtime-Container-ID.

Diese ID entsteht erst als Ergebnis von Docker Create.

Ein unveränderliches Label oder eine create-gebundene Environmentkonstante mit
dem vollständigen Dokumentdigest müsste dagegen bereits vor Create feststehen.

Der vollständige Digest kann deshalb nicht vor Create unabhängig im selben
Container verankert werden.

## Warum Selbsthash nicht genügt

Der Wrapper kann SHA-256 der gelesenen Datei berechnen.

Ohne einen unabhängig gebundenen erwarteten Digest beweist das nur
Selbstkonsistenz.

Ein ausgetauschtes, ebenfalls kanonisches Dokument würde seinen eigenen Hash
ebenfalls bestehen.

Document-ID, Handle oder Profil innerhalb derselben Datei sind kein externer
Anchor.

## Bestehende Labels reichen nicht

LQ-462/LQ-591 binden Creation-ID, Handle, Control-Directory und Profil als
exakte Labelmenge.

Sie binden keinen Jobdokumentdigest, Claim, Owner, Scope oder Image-unabhängigen
Launchdocumentnachweis.

Die exakte Labelprüfung verhindert außerdem stilles additives Einschleusen
eines neuen Labels.

## Mountgrenze

Der aktuelle Client mountet das gesamte Control-Directory read-write nach
`/run/liquent/control`.

Damit wäre auch das Jobdokument im Capabilitycontainer grundsätzlich unter
einem schreibbaren Mount sichtbar.

Dateimodus allein ist bei passender Container-UID keine unveränderliche
Mountgrenze.

Das Startdokument benötigt einen separaten read-only Bind-Mount.

## Reihenfolgebefund

Der aktuelle Prepareflow erzeugt und startet den Container, bevor irgendein
Jobdokument publiziert wird.

LQ-602 hat diese Publikation bewusst noch nicht verdrahtet.

Ein später nach Start erzeugtes Dokument kann kein Vor-Capability-
Startbinding garantieren.

## Weiterhin gültige Teile

Domainmodell, kanonischer Codec und atomarer No-replace-Handoff aus LQ-600 und
LQ-601 bleiben als isolierte Komponenten korrekt.

Sie sind noch keine sichere Wrapper-Startgrenze.

Die Runtime-ID kann weiterhin Parent-/Persistenzkorrelation dienen.

## Keine Loaderimplementation

Ein Loader, der nur `read()` plus Decode aufruft, würde falsche
Productionfähigkeit behaupten.

LQ-603 ergänzt deshalb keinen Wrapperentrypoint und kein Ready.

## Keine Productionwirkung

Settings, Appfactory, Compose, Socketmount und Deployment bleiben geschlossen.

Es gibt keine Migration oder Portsignaturänderung.

## Nächster Slice

LQ-604 definiert ein vor Create vollständig bestimmbares, digestgebundenes
Launchdokument; Runtime-ID bleibt davon getrennte Parentkorrelation.
