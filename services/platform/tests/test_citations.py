from kp.knowledge.citations import filter_citations


def test_drops_unknown_id_and_quote_that_is_not_in_the_record():
    records = {
        ("complaint", "cmp_001"): {"text": "Permitting delays keep moving the date.", "document_id": "ticket_001"},
        ("issue", "iss_installation_delays"): {"text": "Installation Delays\nMembers are waiting on home battery installation."},
    }
    citations = [
        {"id": "cmp_001", "kind": "complaint", "quote": "Permitting delays keep moving the date.", "document_id": "wrong"},
        {"id": "cmp_999", "kind": "complaint", "quote": "Permitting delays keep moving the date.", "document_id": "ticket_001"},
        {"id": "cmp_001", "kind": "complaint", "quote": "this sentence was not retrieved"},
        {"id": "iss_installation_delays", "kind": "issue", "quote": "Members are waiting on home battery installation."},
        {"id": "cmp_001", "kind": "complaint", "quote": ""},
    ]
    kept = filter_citations(citations, records)
    assert kept == [
        {
            "id": "cmp_001",
            "kind": "complaint",
            "quote": "Permitting delays keep moving the date.",
            "document_id": "ticket_001",
        },
        {
            "id": "iss_installation_delays",
            "kind": "issue",
            "quote": "Members are waiting on home battery installation.",
        },
    ]


def test_complaint_without_source_document_is_dropped():
    records = {("complaint", "cmp_001"): {"text": "A real quote.", "document_id": None}}
    assert filter_citations([{"id": "cmp_001", "kind": "complaint", "quote": "A real quote."}], records) == []
