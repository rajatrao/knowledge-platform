"""Citation check: keep a quote only when that retrieved record contains it."""

from __future__ import annotations


def filter_citations(citations: list[dict] | None, records: dict[tuple[str, str], dict]) -> list[dict]:
    kept: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in citations or []:
        kind = raw.get("kind")
        record_id = raw.get("id")
        quote = raw.get("quote") or ""
        if not kind or not record_id or not quote:
            continue
        record = records.get((kind, record_id))
        if record is None or quote not in record.get("text", ""):
            continue
        item = {"id": record_id, "kind": kind, "quote": quote}
        if kind == "complaint":
            document_id = record.get("document_id")
            if not document_id:
                continue
            item["document_id"] = document_id
        key = (item["kind"], item["id"], item["quote"])
        if key in seen:
            continue
        seen.add(key)
        kept.append(item)
    return kept
