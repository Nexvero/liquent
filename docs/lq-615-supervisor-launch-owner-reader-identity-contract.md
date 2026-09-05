# LQ-615 — Supervisor Launch Owner/Reader Identity Contract

## Ergebnis

LQ-615 definiert eine gemeinsame numerische Identity-Policy für Hostpublisher,
Launchfile-Reader und Wrappercontainer.

## Vier Werte

Die Policy bindet Host-Owner-UID, Reader-GID, Wrapper-UID und Wrapper-GID.

Alle Werte sind positive nicht-root numerische IDs im unterstützten Bereich.

Wrapper-GID muss exakt der Reader-GID entsprechen.

Wrapper-UID darf nicht Host-Owner-UID sein.

## Keine Namensauflösung

Benutzernamen, Gruppennamen, `/etc/passwd`, NSS und Environmentwerte werden
nicht ausgewertet.

Docker erhält ausschließlich `uid:gid`.

Requests können die Identity nicht überschreiben.

## Dateipolicy

Der Parent bleibt Eigentümer des Launchfiles.

Die Readergruppe erhält ausschließlich Leserecht über Modus `0640`.

Andere Nutzer erhalten keine Rechte.

Die Policy wird auf der Pending-Datei vor atomarer Publikation angewendet.

## Kein Nach-Publish-Fenster

Chown und Chmod nach Sichtbarkeit des finalen Namens sind verboten.

Owner, Gruppe und Modus müssen vor dem No-replace-Link vollständig gesetzt und
fsync-synchronisiert sein.

## Kompatibilität

Der bestehende explizite owner-private `0600`-Pfad bleibt für isolierte Tests
und Parent-only-Verwendung erhalten.

Production-Readerfähigkeit verlangt die vollständige Policy.

Es gibt keinen impliziten UID/GID-Default.

## Keine Mountentscheidung

Dieser Vertrag öffnet noch keinen read-only Docker-Mount und keinen Loader.

## Nächster Slice

LQ-616 implementiert den geschlossenen Policytyp.
