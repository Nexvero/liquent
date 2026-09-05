# LQ-708 — Atomic Parent Launch Publication Composition

## Umsetzung

Der Parent-Launch-Prefix erhält einen expliziten Launchpublisher und den
kanonischen Launchdokument-Codec.

Nach gültigem Launch-Commit rekonstruiert er das Dokument, vergleicht den
kanonischen SHA-256 mit dem Command-Sollwert und publiziert no-replace.

## Processcomposition

`AtomicLocalManifestHandoffSupervisorLaunchDocuments` wird genau einmal aus
derselben Controlwurzel, demselben aktiven Directoryresolver und derselben
Identitypolicy wie der übrige Kandidatenpfad erzeugt.

Der Kandidat reicht diese Parentgrenze ausschließlich an den Launch-Prefix.

## Fail-closed

Digestdivergenz endet vor Publisher-I/O als Konflikt.

Publisherkonflikt endet vor Runtimeauflösung und Container-Create.

Unerwartete Rückgabetypen oder technische Fehler bleiben detailfreie
Unverfügbarkeit.

## Inertheit

Composition erzeugt den Publisher, öffnet aber weder Root noch Child-Verzeichnis.

Der aktuelle Hostzustand wird erst bei Prepare geprüft.
