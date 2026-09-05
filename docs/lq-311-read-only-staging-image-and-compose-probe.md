# LQ-311 — Read-only Staging Image and Compose Probe

## Ergebnis

LQ-311 implementiert den ersten rein read-only Probe-Kern für rohe begrenzte
Docker-Image-Inspect- und gerenderte Compose-JSON-Snapshots.

Der Kern wertet die Beobachtungen selbst aus. Er akzeptiert keine
caller-gelieferten Allow-Booleans und gibt ausschließlich kanonischen neutralen
LQ-308-Output zurück.

Es gibt noch keine Probe-CLI und keinen Docker-Unterprozessaufruf.

## Unterstützte Phasen

Imagebezogen sind implementiert:

- `image_digest` / `digest_matches`;
- `image_revision` / `revision_matches`;
- `runtime_identity` / `uid_gid_matches`.

Composebezogen sind implementiert:

- `compose_render` / `render_valid`;
- `trading_disabled` / `trading_disabled`;
- `command` / `command_exact`;
- `networks` / `networks_isolated`;
- `mounts` / `mounts_bounded`;
- `secret_mount` / `secret_owner_only`;
- `grace` / `grace_bounded`.

Alle anderen 19 Phasen bleiben technisch
`staging_read_only_probe_unavailable`. Insbesondere wird installierte
Entry-Point-Existenz nicht aus OCI-Config geraten und keine runtimeabhängige
Mount-, Artifact-, Datenbank-, Job-, Revocation- oder Signal-Evidence erfunden.

## Imageprüfung

Imageinspect muss genau eine JSON-Objektbeobachtung liefern und ist auf ein MiB
begrenzt.

Digestprüfung akzeptiert nur lowercase immutable
`repository@sha256:<64-hex>`-Werte und verlangt die exakt autorisierte
Application-Image-Referenz in `RepoDigests`.

Revisionprüfung vergleicht ausschließlich das OCI-Label
`org.opencontainers.image.revision` mit dem autorisierten 40-stelligen
Source-Commit.

Runtimeidentität akzeptiert ausschließlich `10001` oder `10001:10001` aus
`Config.User`.

Mismatch ist ein eindeutiges `failed`; beschädigte, mehrdeutige oder
unvollständige Inspection ist technisch unavailable.

## Composeprüfung

Das gerenderte JSON ist auf zwei MiB begrenzt und muss die sieben gebundenen
Services einschließlich genau eines objektförmigen `research-worker` enthalten.

Der Command muss exakt den LQ-301-Entry-Point mit Config- und
Datenbank-URL-Dateipfaden enthalten.

Worker-Netze müssen exakt Application, Data und Observability sein; Public ist
unzulässig.

Mounts müssen exakt drei read-only Bindmounts für Config, Worker-ID und
Researchdaten sowie ein beschreibbares benanntes Artifactvolume an den festen
Containerzielen bilden. Hostquellen werden nicht in Output übernommen.

Das Datenbank-Secret muss exakt Ziel `database_url`, UID/GID `10001` und Modus
0400, im Compose-JSON als Integer 256, tragen.

Grace akzeptiert nur kanonische 60-Sekunden-Darstellungen. Die Runtimeumgebung
muss Concurrency eins und Trading disabled enthalten und darf keine Broker-,
Exchange-, API-Key/-Secret- oder Live-Trading-Namen tragen.

## Parser- und Detailgrenze

Doppelte Schlüssel, falsche Typen, übergroße Inputs, gemischte Image-/Compose-
Beobachtungen und unbekannte Phasen enden detailfrei unavailable.

Der reduzierte Output enthält nur Schema-Version, Phase und genau ein Boolean-
Faktum. Imageinspect, Composemodell, Hostpfade, Secretziele, Volumenamen und
private Werte werden nicht weitergereicht.

## Ressourcen und Bundle

Der Kern besitzt nur die übergebenen Bytes und erzeugten neutralen Bytes. Er
öffnet keine Datei, startet keinen Prozess und greift nicht auf Docker,
Netzwerk oder Datenbank zu.

Das neue Modul erhöht das Bundle auf 25 Operatormodule. Entry Points bleiben
22; Migration-Head und Anzahl bleiben `20260819_0027` und 27.

## Nichtziele

Keine CLI, Docker-Composition, Entry-Point-Existenzprüfung, effektive
In-Container-Ownership, Artifactprobe, Datenbank-/Jobprüfung, Permissionmutation
oder Signalphase wird implementiert.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell- oder
Composeänderung.

## Nächster Slice

LQ-312 sollte die read-only Probe-CLI-Composition implementieren: Argumente
laden, exakt `docker image inspect` beziehungsweise `docker compose config
--format json` ausführen und ausschließlich den LQ-311-Kern aufrufen.
