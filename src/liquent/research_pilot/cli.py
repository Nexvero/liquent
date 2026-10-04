"""Local operator entry point; never uploads data or overwrites an order."""

import argparse
import json
import os
import sys
from pathlib import Path

from .customer_report import pilot_to_dict, pilot_to_markdown
from .execution import execute_pilot


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Doppelte JSON-Felder sind nicht zulässig")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("NaN/Infinity sind keine zulässigen Auftragswerte")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Digitaler Liquent Research Pilot: genau drei vereinbarte Simulationen")
    parser.add_argument("--dataset", type=Path, required=True, help="Lokale OHLCV-CSV, unverändert")
    parser.add_argument("--config", type=Path, required=True, help="Vollständig vereinbarter JSON-Auftrag")
    parser.add_argument("--output", type=Path, required=True, help="Neues Ausgabeverzeichnis; bestehende Aufträge werden nie überschrieben")
    args = parser.parse_args(argv)
    try:
        if args.output.exists():
            raise ValueError("Ausgabeverzeichnis existiert bereits; bitte neuen Namen wählen")
        configuration = json.loads(args.config.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                                   parse_constant=_reject_constant)
        result = execute_pilot(args.dataset, configuration)
        # Finish serialization before creating any delivery files.
        evidence = json.dumps(pilot_to_dict(result), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        report = pilot_to_markdown(result)
        agreed = json.dumps(result.configuration, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
        args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        for name, content in (("report.md", report), ("evidence.json", evidence), ("agreed-config.json", agreed)):
            descriptor = os.open(args.output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
        if result.data_quality["status"] != "valid":
            print("Daten abgewiesen. Gründe im Bericht; keine Simulation wurde gestartet.", file=sys.stderr)
            return 2
        if any(variant.status == "failed" for variant in result.variants):
            print("Mindestens eine Simulation fehlgeschlagen. Bericht ist unvollständig; nicht als erfolgreichen Auftrag liefern.", file=sys.stderr)
            return 3
        print(f"Pilot abgeschlossen: {args.output / 'report.md'}")
        return 0
    except (OSError, ValueError, TypeError, OverflowError) as exc:
        # Parser/validation errors are metadata-only; do not echo raw file content.
        detail = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else type(exc).__name__
        print(f"Pilot nicht gestartet oder Ausgabe nicht vollständig: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
