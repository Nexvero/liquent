# LQ-820 — Engine API Bundle Process Owner

## Umsetzung

Der Entrypoint verwendet nun direkt
`compose_manifest_handoff_supervisor_engine_api_proxy_bundle` und führt exakt
dessen `process_run` aus. Settings und Ergebnisvalidierung bleiben unverändert.

`ManifestHandoffSupervisorEngineApiProcessOwner` akzeptiert ausschließlich ein
exaktes Bundle. Ein kurzer Lock schützt den einmaligen Claim; danach wird der Run
ohne gehaltenen Ownerlock ausgeführt.

`readiness` projiziert die gebundene Probe fail-closed. `snapshot` liefert nur
den bestehenden detailbegrenzten Snapshot. Fremde Rückgabetypen und Runfehler
werden detailfrei vereinheitlicht.

## Nicht umgesetzt

Der CLI-Entrypoint startet weiterhin keinen Healthtransport und erzeugt keinen
Thread. Der Owner ist eine inerte Compositionprimitive für den späteren Host.
