# LQ-462 — Local Docker Manifest Handoff Supervisor Engine Adapter

## Ergebnis

LQ-462 implementiert den LQ-461-Port als
`LocalDockerManifestHandoffSupervisorEngine`.

Der Adapter arbeitet ausschließlich über einen konstruktiv injizierten Client,
der bereits an genau einen freigegebenen lokalen Docker-Daemon gebunden ist.

## Keine neue SDK-Abhängigkeit

Das Projekt erhält keine neue Docker-SDK- oder Shellabhängigkeit.

Eine private minimale Clientgrenze kapselt Find, Create, Inspect, Start, Wait,
Stop und Kill.

Der Client ist Infrastruktur des späteren Production-Composers und kein
Requestparameter.

## Feste Images

Writer- und Recovery-Digest werden getrennt beim Adapteraufbau gesetzt.

Create muss exakt den für sein Profil konfigurierten Digest tragen.

Abweichung ist detailfreier Konflikt und erzeugt keinen Engineaufruf.

Tags oder dynamische Imagewahl bleiben ausgeschlossen.

## Stabile Labels

Create setzt genau Creation-ID, Handle, Control-Directory-ID und Profil als
interne Labels.

Die Creation-ID ist das einzige Find-Kriterium für Create-Unknown.

Name, PID und zufällige Containerlabels werden nicht zur Adoption verwendet.

Labelwerte werden nicht ausgegeben.

## Geschlossene Create-Spezifikation

Der Adapter setzt Netzwerkmodus `none`, Restartpolicy `no`, kein Auto-Remove,
read-only Rootfilesystem und vollständigen Capability-Drop.

Privileged ist false und PID-Namespace bleibt privat.

Diese Werte entstehen im Adapter und sind nicht caller-konfigurierbar.

Der minimale Client materialisiert das konstruktiv konfigurierte Writer- oder
Recoveryprofil einschließlich seiner festen Entrypoint- und Mountpolicy.

## Create-Unknown

Vor jedem Create sucht der Adapter nach derselben Creation-ID.

Mehr als ein Treffer ist Konflikt.

Ein Treffer wird nur bei exakten Labels, Digest, Profil und vollständigem
Sicherheitsprofil als derselbe Ausgang angenommen.

Jede Divergenz ist Konflikt; es wird kein zweiter Container erzeugt.

Kein Treffer führt zu genau einem Createversuch.

Ein technisch unklarer Create-Ausgang bleibt unverfügbar und wird beim Retry
über dieselbe Creation-ID reconciliert.

## Create-Ergebnis

Der Enginebestand muss eine nicht leere unveränderliche Container-ID liefern.

Der Adapter rekonstruiert den geschlossenen Created-Record aus Request und
direkter Engineantwort.

Er persistiert die Runtimebinding nicht selbst.

Die Composition muss das Ergebnis vor Launch-Bestätigung über LQ-460 binden.

## Inspect

Inspect adressiert ausschließlich die Runtime-Container-ID.

Fehlender erwarteter Bestand ist technische Unverfügbarkeit, nicht `None`.

Die Antwort muss Container-ID, Creation-ID, festes Profil, konfigurierten
Digest und einen der vier geschlossenen Zustände tragen.

Das vollständige Sicherheitsprofil wird bei jeder Beobachtung erneut geprüft.

## Start

Vor Start inspiziert der Adapter direkt dieselbe Container-ID.

Nur Zustand created darf genau einmal gestartet werden.

Running, exited oder dead führen zu Konflikt statt blindem Restart.

Die Startbestätigung behauptet weder Engine-Running noch Wrapper-ready.

## Wait

Wait delegiert die konstruktiv begrenzte Wartepolicy an den lokalen Client.

Nur exited oder dead werden als Beobachtung zurückgegeben.

Created, running, Timeout oder unlesbare Antwort bleiben technische
Unverfügbarkeit.

Exitcode und fachliches Outcome sind nicht Teil der Antwort.

## Terminate

Terminate inspiziert zuerst die exakt gebundene Container-ID.

Exited oder dead liefern eine idempotente Annahme derselben Terminate-ID ohne
weitere Enginewirkung.

Für created oder running versucht der Adapter zuerst Stop und bei dessen
Nichtannahme Kill gegen dieselbe Container-ID.

Die Bestätigung ist weiterhin kein Terminalnachweis; Wait oder Inspect muss
exited beziehungsweise dead beobachten.

## Kein Remove

Der minimale Client und Adapter bieten keine Remove-, Prune- oder
Cleanupmethode.

Terminale Container bleiben für spätere direkte Beobachtung erhalten.

Retention und owner-kontrolliertes Cleanup bleiben separate Slices.

## Sicherheitsprüfung

Jede Create-Adoption und jede spätere Beobachtung prüft Netzwerk, Restart,
Auto-Remove, Rootfilesystem, Capabilities, Privileged und PID-Namespace.

Ein unsicherer oder beschädigter Bestand wird niemals normalisiert.

Create-Divergenz ist Konflikt; erwartete Runtime-Divergenz ist technische
Unverfügbarkeit.

## Fehlergrenze

Client-, Daemon-, Decode-, Zustands- und Protokollfehler werden über die
bestehende `ManifestHandoffRegistryUnavailable` detailfrei vereinheitlicht.

Socket-, Host-, Container- und Labeldetails verlassen den Adapter nicht.

LQ-462 benennt keinen neuen Exceptiontyp.

## Keine Authority

Der Adapter akzeptiert keine Session, Rolle, Permission oder Allowentscheidung.

Er prüft keine Plattformauthority und leitet sie nicht aus Enginebestand ab.

Journal- und Authorityvoraussetzungen müssen vor dem Aufruf in der späteren
Servicecomposition geprüft werden.

## Keine Dateiwirkung

Control-Directory-ID bleibt eine Korrelation.

Der Adapter erstellt kein Verzeichnis und liest oder publiziert kein
Control-Artefakt.

Der atomare Filepublisher bleibt separat.

## Kein Wiring oder Schema

LQ-462 ergänzt weder Production-Client noch Daemonendpoint, CLI, Compose,
Route, Serviceprozess oder Plattformcomposer.

Es gibt keine Migration, Tabelle, Spalte, Seed oder Backfill.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

## Tests

Fokussierte Tests belegen Create-Reconciliation, exakte Sicherheitswerte,
Digest-/Profilsperre, Start nur aus created, terminales Wait, Stop-/Killfolge,
fehlendes Remove und detailfreie Fehler.

## Nächster Slice

LQ-463 sollte den geschlossenen Control-Artefaktcodec und die atomare lokale
Filepublisher-Grenze definieren.

Production-Client und Supervisorservice bleiben danach separat.
