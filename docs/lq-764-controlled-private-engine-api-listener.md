# LQ-764 — Controlled Private Engine API Listener

## Umsetzung

`ControlledManifestHandoffSupervisorEngineApiListener` verwaltet höchstens eine
aktive Listenerinstanz und deren beim Bind beobachtete Device-/Inodeidentität.

`open` prüft Elternverzeichnis und Zielabwesenheit vor Socketerzeugung, setzt
Close-on-exec, bindet, setzt Ownership und Modus, lauscht und prüft Pfad und
Deskriptor erneut.

`close` akzeptiert ausschließlich das aktive Objekt, schließt es und entfernt
danach nur den weiterhin identischen Socketpfad.

## Fremdpfadschutz

Weder Openfehler noch Retire entfernen einen Pfad mit abweichendem Typ, Device
oder Inode. Ein vorbestehender Zielname stoppt bereits vor Socketerzeugung.

## Fehlergrenze

Dateisystem-, Socket-, Ownership-, Listen-, Verify-, Close- und Unlinkfehler
werden auf die bestehende detailfreie technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Accept, Connect, Clientsetup, Exchange, Serve-Loop oder Prozessshutdown wird
ergänzt.
