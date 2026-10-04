"""Explicit digital feedback, privately stored; intentions are not paid demand."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone


def _validate(value):
    if type(value) is not dict or set(value) != {"goal", "main_obstacle", "usefulness", "would_use_again", "comment"}:
        raise ValueError("Invalid feedback fields")
    for name in ("goal", "main_obstacle", "comment"):
        if not isinstance(value[name], str) or len(value[name]) > 1000:
            raise ValueError("Feedback text too long or invalid")
        if name != "comment" and not value[name].strip():
            raise ValueError("Feedback goal and obstacle required")
    if type(value["usefulness"]) is not int or not 1 <= value["usefulness"] <= 5:
        raise ValueError("Usefulness must be between one and five")
    if value["would_use_again"] not in ("yes", "no", "unsure"):
        raise ValueError("Explicit repeat-use intention required")
    return {name: item.strip() if isinstance(item, str) else item for name, item in value.items()}


def save_feedback(store, owner: str, value: dict) -> dict:
    feedback = _validate(value)
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("Owner required")
    with store._locked():
        folder = store.root / "feedback"
        if not folder.exists():
            folder.mkdir(mode=0o700)
        store._private(folder, directory=True)
        entry = {"schema": "liquent.product-feedback.v1", "owner": owner,
                 "created_at": datetime.now(timezone.utc).isoformat(),
                 "feedback": feedback, "evidence_type": "self_report_not_purchase"}
        path = folder / (uuid.uuid4().hex + ".json")
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump(entry, target, ensure_ascii=False, allow_nan=False)
    return {"saved": True}


def feedback_summary(store) -> dict:
    """Operator-only aggregate, no free text, names, owner IDs or credentials."""
    with store._locked():
        folder = store.root / "feedback"
        entries = []
        if folder.exists():
            store._private(folder, directory=True)
            for path in folder.iterdir():
                if path.suffix != ".json":
                    continue
                entry = store._load(path)
                if type(entry) is not dict or entry.get("schema") != "liquent.product-feedback.v1" or entry.get("evidence_type") != "self_report_not_purchase":
                    raise ValueError("Invalid feedback entry")
                entries.append(_validate(entry.get("feedback")))
        intentions = {choice: sum(entry["would_use_again"] == choice for entry in entries)
                      for choice in ("yes", "no", "unsure")}
        # A repeated submission is neither a new participant nor a purchase.
        owners = set()
        if folder.exists():
            for path in folder.iterdir():
                if path.suffix == ".json":
                    owners.add(store._load(path)["owner"])
        return {"response_count": len(entries), "distinct_access_count": len(owners),
                "usefulness_average": round(sum(entry["usefulness"] for entry in entries) / len(entries), 2) if entries else None,
                "would_use_again": intentions,
                "evidence_type": "self_report_not_purchase"}
