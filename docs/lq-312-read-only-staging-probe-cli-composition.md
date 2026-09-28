# LQ-312 — Read-only Staging Probe CLI Composition

## Ergebnis

LQ-312 installiert `liquent-staging-phase-probe` für die zehn in LQ-311
implementierten read-only Image-/Composephasen.

Der Command lädt die owner-only LQ-306-Autorisierung, prüft alle lokalen
Bindungen, führt genau einen festen Docker-Read-only-Aufruf aus und reicht
dessen begrenzten Output ausschließlich an den LQ-311-Kern.

Mutierende und noch nicht beweisbare Phasen enden vor Dockerzugriff technisch
ohne stdout oder stderr.

## Korrigierte Autorisierungsbindung

Der LQ-310-Vertrag und die LQ-309-Composition erhalten explizit den siebten
Input `--authorization-file`.

Ohne diese Datei könnte der separate Probeprozess Source-Commit,
Application-Image-Digest und Compose-SHA-256 nicht unabhängig gegen den
autorisierten Run prüfen. Eine Ableitung dieser Sollwerte aus dem zu prüfenden
Image wäre zirkulär und ist nun ausgeschlossen.

Die Autorisierungsdatei verwendet unverändert den owner-only LQ-306-Loader und
das aktuelle UTC-Zeitfenster.

## Lokaler Preflight

Vor Prozessstart verlangt die CLI:

- unterstützte read-only Phase;
- absolutes reguläres ausführbares Docker-Executable;
- exakten rungebundenen Projektnamen;
- reguläres nicht verlinktes Composefile mit autorisiertem SHA-256;
- owner-only Runtime- und Image-Environmentdateien;
- exakt fünf immutable Imagewerte und den separaten Secrets-Directory-Wert;
- exakte Gleichheit von `LIQUENT_APP_IMAGE` und autorisiertem Image-Digest.

Jeder Mismatch stoppt vor Dockerzugriff detailfrei.

## Imageaufruf

Die Phasen `image_digest`, `image_revision` und `runtime_identity` führen
ausschließlich folgende argv-Struktur aus:

`<docker> image inspect <authorized-image-ref>`

Es gibt keinen Pull, Run, Build, Tag, Login oder zweiten Inspect. Output ist
auf ein MiB begrenzt.

## Composeaufruf

Die sieben statischen Composephasen führen ausschließlich aus:

`<docker> compose --env-file <runtime> --env-file <images> --file <compose>
--project-name <bound-run> config --format json`

Es gibt kein Up, Run, Exec, Pull, Build, Profile, Scale oder Serviceargument.
Output ist auf zwei MiB begrenzt.

## Prozess- und Outputgrenze

Jeder Aufruf verwendet ein neues leeres temporäres Arbeitsverzeichnis,
Environment exakt `LANG=C`/`LC_ALL=C`, 60 Sekunden Timeout und fünf Sekunden
Terminate-Grace.

Nonzero, stderr, Timeout, Truncation oder Hard Kill endet technisch ohne
Probeoutput. Nur der kanonische LQ-311-Output wird unverändert auf stdout
geschrieben.

CLI-Parsing- und Laufzeitfehler liefern Exitcode zwei ohne Usage-, Pfad- oder
Fehlertext. Ein valides `true` oder `false`-Faktum liefert Exitcode null; die
fachliche Interpretation übernimmt erst der äußere LQ-308-Parser.

## Bundle

Der neue Console Entry Point und das Operatormodul erhöhen die Gates auf 23
Entry Points und 26 Operatormodule. Migration-Head und Anzahl bleiben
`20260819_0027` und 27.

## Nichtziele

Keine Entry-Point-Existenz-, effektive In-Container-Mount-/Ownership-,
Artifact-, Datenbank-, Job-, Revocation-, Log- oder SIGTERM-Phase wird
implementiert.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell- oder
Composeänderung und keine reale Stagingfreigabe.

## Nächster Slice

LQ-313 sollte die kontrollierte read-only Runtime-Inspection für installierten
Entry Point, effektive Inputownership und read-only Datenmounts definieren,
ohne Artifact-, Datenbank- oder Produktmutation vorwegzunehmen.
