# LQ-763 — Private Engine API Listener Lifecycle Contract

## Ziel

Der Proxy darf genau einen privaten Unix-Listener unter einem festen, zuvor
kontrollierten Elternverzeichnis publizieren und später sicher zurückziehen,
ohne bereits Clients anzunehmen.

## Vorbedingungen

Der Socketpfad ist absolut, kein Rootpfad und liegt nicht direkt unter Root. Das
Elternverzeichnis existiert als echtes Verzeichnis, gehört exakt der festen
Host-UID/GID und hat Modus 0700.

Der Zielname muss abwesend sein. Ein bestehender Socket, Symlink oder anderer
Dateityp wird weder übernommen noch entfernt.

## Publikation

Genau ein AF_UNIX/SOCK_STREAM mit Close-on-exec wird erzeugt. Inheritability wird
vor Bind explizit auf false gesetzt.

Nach Bind werden UID/GID und Modus 0660 ohne Symlinkfolge gesetzt. Erst danach
wird mit festem positivem Backlog gelauscht.

Pfadtyp, Device/Inode, Ownership, Modus, Deskriptortyp, Inheritability,
Acceptstatus und lokaler Endpoint werden vor Rückgabe geprüft.

## Fehlercleanup

Ein partieller Listener wird best-effort geschlossen. Der Pfad wird nur entfernt,
wenn Typ, Device und Inode noch exakt dem selbst publizierten Socket entsprechen.

Ein ausgetauschter oder fremder Pfad bleibt unangetastet.

## Retire

Nur die aktive Listenerinstanz darf geschlossen werden. Nach erfolgreichem Close
wird ausschließlich der weiterhin identische Socketpfad entfernt.

Scheitert Close, bleibt der aktive Zustand für einen expliziten Retry erhalten.

## Grenzen

Kein Accept, Clienttimeout, Exchange, Loop, Signal oder Prozesslifecycle wird
ergänzt.
