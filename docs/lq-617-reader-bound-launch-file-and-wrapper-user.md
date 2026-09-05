# LQ-617 — Reader-bound Launch File and Wrapper User

## Ergebnis

LQ-617 integriert dieselbe LQ-616-Policy additiv in Launchfileadapter und
lokalen Dockerclient.

## Launchfile

Bei expliziter Policy muss Host-Owner-UID der effektiven Prozess-UID
entsprechen.

Die Pending-Datei erhält vor Inhaltspublikation über `fchown` Owner und
Readergruppe sowie über `fchmod` Modus `0640`.

Erst danach folgen vollständiger Write, fsync und No-replace-Link.

Read prüft exakt Policy-Owner, Reader-GID, `0640`, Single-Link und Größe.

## Dockerclient

Bei expliziter Policy darf kein paralleler freier Userstring vorliegen.

Der Create-Body erhält exakt `policy.docker_user`.

Der Konstruktor bleibt ohne Socket-I/O.

## Kompatibilitätsgrenze

Ohne Policy verlangt der bestehende Client weiterhin einen expliziten
Userstring und der Launchfileadapter weiterhin owner-private `0600`-Fakten.

Es gibt keinen stillen Übergang zwischen beiden Modi.

## Nachweise

Tests belegen Policyablehnung, repr-freie Werte, atomare `0640`-Publikation,
korrekte UID/GID, stabilen Retry, falschen Hostowner und exakte Docker-
Usermaterialisierung ohne I/O.

## Noch offen

Read-only Launchfile-Mount, Digestlabels, Prepare-Reihenfolge und Loader bleiben
separate Slices.

## Nächster Slice

LQ-618 führt Abschlussaudit und vollständige Regression aus.
