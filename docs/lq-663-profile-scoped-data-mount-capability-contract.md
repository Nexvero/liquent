# LQ-663 — Profile-scoped Data Mount Capability Contract

## Ergebnis

Writer und Recovery erhalten unterschiedliche, minimal erforderliche
Dateisystemfähigkeiten aus derselben bereits persistent registrierten
`ManifestHandoffScopeBinding`.

## System of Record

Die Bindung stammt ausschließlich aus
`command.registration.process_request.binding`.

Der Parent hat dieselbe Registration unmittelbar zuvor aus dem Journal gelesen
und vollständig mit dem Preparecommand verglichen.

Requestmounts, Hostpfade aus Settings und frei injizierte Capabilitylisten sind
unzulässig.

## Writerprofil

Writer erhält Source unter einem festen internen Pfad ausschließlich read-only.

Target wird unter einem getrennten festen Pfad mit der für den atomaren
Manifest-Handoff erforderlichen Schreibfähigkeit gebunden.

Writer erhält keine Engine-, Cleanup- oder weitere Hostfähigkeit.

## Recoveryprofil

Recovery erhält ausschließlich Target read-only.

Es erhält keinen Source-Mount, keinen schreibbaren Target-Mount und keine
Writer- oder Cleanupfähigkeit.

## Pfadgrenzen

Source und Target müssen absolute vorhandene Verzeichnisse sein.

Symlinks, relative oder fehlende Pfade sowie Docker-Bind-Trennzeichen und
Zeilenumbrüche scheitern vor Create geschlossen.

## Beobachtung und Retry

Inspect akzeptiert ausschließlich die exakte Anzahl, Reihenfolge, internen
Ziele und Modi des jeweiligen Profils.

Der Parent vergleicht beobachtete Pfade erneut mit der registrierten Bindung.

Abweichung erlaubt weder Adoption noch einen zweiten Create.

## Grenzen

Keine Authority-, Settings-, Appfactory-, Compose-, Entrypoint-, Schema-, SQL-,
Migrations- oder Productionentscheidung wird geöffnet.
