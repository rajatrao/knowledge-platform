"""Field-operations asks retrieve technician and van rows from the CSVs."""

from kp.knowledge.field_ops import include_field_ops_records
from kp.knowledge.retrieve import Bundle, _prompt_record_limit
from kp.knowledge.synthesize import _compact_records


def _field_text(bundle: Bundle) -> str:
    return " ".join(record["text"] for (kind, _), record in bundle.records.items() if kind == "field_ops")


def test_van_location_and_available_technicians_are_retrieved():
    van = Bundle("customer-complaints", {"themes": []})
    van.add("issue", "iss_billing", "Billing confusion is the top customer complaint")
    include_field_ops_records(van, "where is van V001")
    van_text = _field_text(van)
    assert "V001" in van_text
    assert "On Job" in van_text
    assert "T001" in van_text
    assert "Round Rock" in van_text
    assert "J001" in van_text
    compact = _compact_records(van, query="where is van V001")
    assert compact
    assert all(row["kind"] == "field_ops" for row in compact)
    assert any("V001" in row["text"] and "Round Rock" in row["text"] for row in compact)
    assert any("J001" in row["text"] for row in compact)

    people = Bundle("customer-complaints", {"themes": []})
    people.add("issue", "iss_billing", "Billing confusion is the top customer complaint")
    include_field_ops_records(people, "who is currently available")
    people_text = _field_text(people)
    assert "T004" in people_text
    assert "Available" in people_text
    assert "Maren Holt" in people_text
    limit = _prompt_record_limit("who is currently available")
    assert limit >= 7
    shown = _compact_records(people, limit=limit, query="who is currently available")
    assert any(row["id"] == "T004" for row in shown)
    assert all(row["kind"] == "field_ops" for row in shown)

    revenue = Bundle("customer-complaints", {})
    revenue.add("knowledge_item", "ki_qr_2024q1", "2024 Q1 revenue")
    include_field_ops_records(revenue, "what was company revenue in 2024")
    assert not any(kind == "field_ops" for kind, _ in revenue.records)
    revenue_rows = _compact_records(revenue, query="what was company revenue in 2024")
    assert [row["id"] for row in revenue_rows] == ["ki_qr_2024q1"]


def test_named_field_ops_rows_are_cited_verbatim():
    from kp.knowledge.synthesize import _finish_citations

    bundle = Bundle("customer-complaints", {})
    include_field_ops_records(bundle, "where is van V001")
    answer = "Van V001 is On Job with T001 in Round Rock on J001."
    citations = _finish_citations(
        "where is van V001",
        bundle,
        answer,
        [{"id": "V001", "kind": "field_ops", "quote": "this sentence was not retrieved"}],
    )
    assert [item["id"] for item in citations] == ["V001", "T001", "J001"]
    for item in citations:
        assert item["quote"] in bundle.records[("field_ops", item["id"])]["text"]


def test_van_job_shortage_comes_from_inventory_rows():
    bundle = Bundle("complaint-drivers", {})
    include_field_ops_records(bundle, "does van V001 have everything for job J001")
    text = _field_text(bundle)
    assert "P018" in text
    assert "required_quantity 2" in text
    assert "no van_inventory row, quantity 0" in text
    assert "short 2" in text
    assert "J001" in text
