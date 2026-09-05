# LQ-819 — Engine API Entrypoint Bundle and Run/Health Ownership Contract

## Ziel

Der Prozesseinstieg muss genau ein vollständiges Bundle komponieren. Eine
separate Ownergrenze erlaubt genau einen Runclaim und gleichzeitig read-only
Status- und Readinesszugriff.

## Runownership

Der erste Run-Caller beansprucht das Bundle atomar und dauerhaft. Parallele oder
spätere Runversuche scheitern fail-closed, auch wenn der erste Run fehlschlägt.

Der Claimlock wird nur für die Anspruchsentscheidung gehalten, niemals während
des blockierenden Runs.

## Healthownership

Readiness und Snapshot werden ausschließlich über die objektidentischen
Bundlekomponenten gelesen. Sie benötigen den Runclaimlock nicht und dürfen daher
während eines laufenden Runs beobachtet werden.

Die Ownergrenze erzeugt keinen Thread. Der Signal-owned Run bleibt in dem Thread,
der `run` aufruft; Main-Thread-Anforderungen werden nicht umgangen.

## Grenzen

Kein Healthserver, Socket, HTTP, Poller, Callback, Logging, Deployment oder
Restart wird ergänzt.
