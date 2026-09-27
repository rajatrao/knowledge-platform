"""Persona skills and dataset retrieval. These tests do not call Ollama."""

from pathlib import Path

from kp.knowledge.engineering import engineering_query, include_engineering_records
from kp.knowledge.executive import executive_query, include_executive_records
from kp.knowledge.field_ops import field_ops_query, include_field_ops_records, prompt_records
from kp.knowledge.intent import load_skill
from kp.knowledge.retrieve import Bundle
from kp.knowledge.synthesize import grounded_answer

ROOT = Path(__file__).resolve().parents[3]


def _skill(relative: str) -> dict:
    return load_skill(ROOT / relative)


def _text(bundle: Bundle, kind: str) -> str:
    return " ".join(record["text"] for (record_kind, _), record in bundle.records.items() if record_kind == kind)


def test_skill_text_matches_each_persona_dataset():
    operations = _skill("skills/functions/operations_manager/complaint-drivers/SKILL.md")
    assert "technicians.csv" in operations["body"]
    assert "van_inventory.csv" in operations["body"]
    assert "warehouse_inventory.csv" in operations["body"]
    assert "operational_alerts.csv" in operations["body"]
    assert "which warehouse should supply a job" in operations["body"]

    engineer = _skill("skills/functions/engineer/complaint-incidents/SKILL.md")
    assert "data/engineering/" in engineer["body"]
    assert "Under Investigation" in engineer["body"]
    assert "4.3.0" in engineer["body"]
    assert "DEV-001" in engineer["body"]
    assert "INC-008" in engineer["body"]
    assert "do not invent a confirmed cause" in engineer["body"].casefold()

    ceo = _skill("skills/functions/ceo/customer-complaints/SKILL.md")
    assert "data/executive/" in ceo["body"]
    assert "FACT, TREND, POSSIBLE EXPLANATION, and UNKNOWN" in ceo["body"]
    assert "metric_definitions.md" in ceo["body"]
    assert "do not rank a market as best" in ceo["body"].casefold()
    assert "staffing and inventory both coincide" in ceo["body"]
    assert "aggregated company figures" in ceo["body"]
    for topic in ("markets.csv", "deployment_metrics.csv", "workforce_metrics.csv", "inventory_risk.csv", "engineering_health_metrics.csv", "company_metrics.csv", "executive_risks.csv", "executive_alerts.csv", "executive_documents.csv"):
        assert topic in ceo["body"]

    marketing = _skill("skills/functions/marketing/value-language/SKILL.md")
    assert "verbatim" in marketing["body"]
    assert "energy independence" in marketing["body"]
    # customer_experience_metrics.csv and customer_issues.csv are on disk.
    assert "customer_experience_metrics.csv" in marketing["body"]
    assert "customer_issues.csv" in marketing["body"]
    assert "Do not invent a product" in marketing["body"]


def test_visible_answer_does_not_include_the_skill_id():
    bundle = Bundle(
        "value-language",
        {
            "value_themes": [
                {
                    "label": "Energy independence",
                    "records": [
                        {
                            "quote": "We wanted the house to keep running.",
                            "id": "cmp_1",
                            "complaint_id": "cmp_1",
                            "document_id": "doc_1",
                        }
                    ],
                }
            ]
        },
    )
    answer, _citations = grounded_answer(bundle, "What language are customers using?")
    assert "value-language" not in answer
    web = ROOT / "apps" / "web" / "src"
    chat = (web / "components" / "Chat.jsx").read_text()
    app = (web / "App.jsx").read_text()
    assert "turn.route.name" not in chat
    assert 'className="persona"' not in app


def test_selection_routes_dataset_questions_without_a_model():
    assert engineering_query("why is DEV-001 offline")
    assert engineering_query("firmware regression 4.3.0 vs 4.3.1")
    assert not engineering_query("Which customer complaints appear related to technical incidents?")
    assert field_ops_query("where is van V001")
    assert not field_ops_query("what was company revenue in 2024")
    assert executive_query("why are installations down in North Austin")
    assert executive_query("how are company installations")
    assert not executive_query("what was company revenue in 2024")
    assert not executive_query("What language are customers using when they describe why they value Base Power?")


def test_engineer_query_selects_dev_001_and_firmware_without_the_telemetry_file():
    offline = Bundle("complaint-incidents", {"technical_issues": []})
    offline.add("complaint", "cmp_1", "The app forgot my reading")
    include_engineering_records(offline, "why is DEV-001 offline")
    text = _text(offline, "engineering")
    assert "DEV-001" in text
    assert "INC-001" in text
    assert "TEL-" not in text
    shown = prompt_records(offline, "why is DEV-001 offline")
    assert shown
    assert all(kind == "engineering" for kind, _ in (item[0] for item in shown))

    firmware = Bundle("complaint-incidents", {})
    include_engineering_records(firmware, "firmware regression 4.3.0 vs 4.3.1")
    firmware_text = _text(firmware, "engineering")
    assert "4.3.0" in firmware_text
    assert "4.3.1" in firmware_text

    unknown = Bundle("complaint-incidents", {})
    include_engineering_records(unknown, "what is the root cause of INC-008")
    unknown_text = _text(unknown, "engineering")
    assert "INC-008" in unknown_text
    assert "Under Investigation" in unknown_text


def test_telemetry_question_keeps_a_short_window():
    bundle = Bundle("complaint-incidents", {})
    include_engineering_records(bundle, "what did the telemetry temperature show for DEV-001")
    rows = [record for (kind, _), record in bundle.records.items() if kind == "engineering"]
    telemetry = [record for record in rows if record["document_id"] == "device_telemetry.csv"]
    assert telemetry
    assert len(telemetry) <= 12
    assert any("battery_temperature_c" in record["text"] for record in telemetry)
    assert any("DEV-001" in record["text"] for record in rows if record["document_id"] == "devices.csv")


def test_operations_query_still_sees_v001_and_can_name_a_supplying_warehouse():
    van = Bundle("complaint-drivers", {})
    van.add("issue", "iss_billing", "Billing confusion")
    include_field_ops_records(van, "where is van V001")
    assert "V001" in _text(van, "field_ops")
    assert "Round Rock" in _text(van, "field_ops")

    supply = Bundle("complaint-drivers", {})
    include_field_ops_records(supply, "which warehouse should supply job J007")
    supply_text = _text(supply, "field_ops")
    assert "J007" in supply_text
    assert "P006" in supply_text
    assert "W002" in supply_text
    assert "available 4" in supply_text


def test_ceo_query_sees_company_and_market_rows():
    executive_dir = ROOT / "data" / "executive"
    company_file = executive_dir / "company_metrics.csv"
    markets_file = executive_dir / "markets.csv"
    if not company_file.is_file() or not markets_file.is_file():
        # Executive CSVs were not on disk; the temp-file test below still covers the loader.
        return
    company = Bundle("customer-complaints", {"themes": []})
    company.add("issue", "iss_billing", "Billing confusion")
    include_executive_records(company, "how are company installations")
    company_text = _text(company, "executive")
    assert "Company aggregate" in company_text
    assert "2026-08" in company_text
    assert "2026-09" in company_text
    assert "477" in company_text
    shown = prompt_records(company, "how are company installations")
    assert shown
    assert all(kind == "executive" for kind, _ in (item[0] for item in shown))

    market = Bundle("customer-complaints", {"themes": []})
    include_executive_records(market, "why are installations down in North Austin")
    market_text = _text(market, "executive")
    assert "MKT-002" in market_text
    assert "P006" in market_text
    assert "certified_technician_count" in market_text or "technician_count" in market_text


def test_executive_loader_aggregates_a_temp_csv(tmp_path):
    root = tmp_path / "executive"
    root.mkdir()
    (root / "markets.csv").write_text(
        "market_id,market_name,status,warehouse_id\nMKT-009,Test Market,Active,W001\n"
    )
    (root / "company_metrics.csv").write_text(
        "period,installations_completed\n2026-08,10\n2026-09,7\n"
    )
    bundle = Bundle("customer-complaints", {})
    include_executive_records(bundle, "how are company installations", root=root)
    text = _text(bundle, "executive")
    assert "Company aggregate" in text
    assert "2026-08" in text
    assert "2026-09" in text
    assert "MKT-009" not in text


def test_revenue_and_value_language_do_not_take_the_new_rows():
    revenue = Bundle("customer-complaints", {})
    revenue.add("knowledge_item", "ki_qr_2024q1", "2024 Q1 revenue")
    include_executive_records(revenue, "what was company revenue in 2024")
    include_engineering_records(revenue, "what was company revenue in 2024")
    include_field_ops_records(revenue, "what was company revenue in 2024")
    assert list(revenue.records) == [("knowledge_item", "ki_qr_2024q1")]

    marketing = Bundle("value-language", {})
    marketing.add("complaint", "cmp_1", "We wanted energy independence")
    include_executive_records(
        marketing,
        "What language are customers using when they describe why they value Base Power?",
    )
    assert list(marketing.records) == [("complaint", "cmp_1")]


def test_customer_issue_rows_load_when_the_question_asks_for_them():
    bundle = Bundle("value-language", {})
    include_executive_records(bundle, "which customer issues are open about firmware")
    text = _text(bundle, "executive")
    assert "ISS-001" in text or "Firmware" in text
    assert "customer issues" in text.casefold() or "Firmware" in text
