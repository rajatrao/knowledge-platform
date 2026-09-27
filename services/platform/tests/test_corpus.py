from collections import Counter

from kp.corpus.generate import generate_corpus
from kp.corpus.inventory import BATTERY_MONTH_END, ON_HAND, Q4_INSTALLS, monthly_issues, projected_end
from kp.corpus.performance import ERCOT_MONTHLY_PEAKS, LOAD_PEAK_MW, MONTHS, QUARTERS, ZONE_PEAK, september_daily_peaks


def test_outage_chart_uses_outage_counts_not_complaint_themes():
    from kp.knowledge.artifacts import chart_plans

    charts = chart_plans("create chart for customer outages that happened in last 3 months")
    assert charts is not None
    title, values, y_title = charts[0]
    assert title == "Customer outages"
    assert y_title == "Customers"
    assert [row["label"] for row in values] == ["July 2026", "August 2026", "September 2026"]
    assert [row["count"] for row in values] == [121, 188, 67]
    all_months = chart_plans("create chart for outages")
    assert all_months is not None
    assert [row["label"] for row in all_months[0][1]][0] == "April 2026"
    assert len(all_months[0][1]) == 6


def test_customer_outages_cover_the_last_six_months():
    from kp.corpus.outages import MONTHS, outage_knowledge_items, six_month_totals
    from kp.knowledge.retrieve import _company_sort_key

    assert [row[0] for row in MONTHS] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    customers, covered, uncovered = six_month_totals()
    assert customers == 696
    assert covered == 592
    assert uncovered == 104
    assert covered + uncovered == customers
    corpus = generate_corpus()
    outages = [row for row in corpus["all_documents"] if row["source_type"] == "customer_outage"]
    assert {row["id"] for row in outages} == {"doc_outage_months", "doc_outage_events"}
    items = outage_knowledge_items()
    assert any(row["id"] == "ki_outage_summary" and "696 customer outages" in row["body"] for row in items)
    assert any("2026-08-14" in row["body"] and "9 batteries did not start" in row["body"] for row in items)

    class Item:
        def __init__(self, item_id, document_id):
            self.id = item_id
            self.document_id = document_id
            self.body = ""

    summary = Item("ki_outage_summary", "doc_outage_months")
    september = Item("ki_outage_2026_09", "doc_outage_months")
    april = Item("ki_outage_2026_04", "doc_outage_months")
    revenue = Item("ki_qr_2026q3", "doc_qr_2026q3")
    text = "customer outages for the last 6 months"
    assert _company_sort_key(summary, text) < _company_sort_key(september, text)
    assert _company_sort_key(september, text) < _company_sort_key(april, text)
    assert _company_sort_key(april, text) < _company_sort_key(revenue, text)


def test_seeded_counts_match_the_plan():
    corpus = generate_corpus()
    assert len(corpus["conversations"]) == 500
    assert len(corpus["operations_tickets"]) == 100
    assert len(corpus["incidents"]) == 50
    assert len(corpus["documents"]) == 30
    assert all(row["document_id"] for row in corpus["complaints"])

    states = Counter(row["installation_state"] for row in corpus["operations_tickets"])
    assert states["at_risk"] == 47
    assert states["open_incident"] == 12
    assert states["delayed"] == 31

    blockers = Counter(row["blocker"] for row in corpus["operations_tickets"])
    assert [name for name, _ in blockers.most_common()] == [
        "permitting",
        "installer_capacity",
        "customer_scheduling",
    ]

    technical = Counter(row["technical_issue"] for row in corpus["conversations"] if row["technical_issue"])
    assert technical["battery_telemetry"] == 31
    assert technical["mobile_app"] == 22
    assert technical["firmware"] == 17

    sentiment = Counter(row["sentiment"] for row in corpus["conversations"])
    assert sentiment["positive"] == 305
    assert sentiment["neutral"] == 120
    assert sentiment["negative"] == 75

    install = next(issue for issue in corpus["issues"] if issue["slug"] == "installation_delays")
    assert install["complaint_count"] == 175
    assert install["trend"] == 50.0
    joined = sum(1 for row in corpus["issue_complaints"] if row["issue_id"] == install["id"])
    assert joined == install["complaint_count"]

    company = [row for row in corpus["all_documents"] if row["source_type"] in {"company_performance", "revenue", "ercot"}]
    company_ids = {row["id"] for row in company}
    assert {
        "doc_perf_2026",
        "doc_rev_2026",
        "doc_ercot_20260915",
        "doc_ercot_2026",
        "doc_perf_quarters",
        "doc_rev_quarters",
    }.issubset(company_ids)
    assert sum(row["id"].startswith("doc_qp_") for row in company) == 20
    assert sum(row["id"].startswith("doc_qr_") for row in company) == 20
    bodies = {row["id"]: row["body"] for row in company}
    company_items = [row for row in corpus["knowledge_items"] if row["kind"] in {"company_performance", "revenue", "ercot_grid"}]
    assert len(company_items) == 68
    for item in company_items:
        assert item["body"] in bodies[item["document_id"]]
        assert len(item["body"]) <= 180
    assert "18420" in bodies["doc_perf_2026"]
    assert "$4.82 million" in bodies["doc_rev_2026"]
    assert "LZ_HOUSTON 187.40" in bodies["doc_ercot_20260915"]
    assert "78400" in bodies["doc_ercot_20260915"]
    assert "09 $187.40" in bodies["doc_ercot_2026"]
    assert ERCOT_MONTHLY_PEAKS[-1] == ("2026-09", ZONE_PEAK["LZ_HOUSTON"], LOAD_PEAK_MW)
    peak_day = next(row for row in september_daily_peaks() if row[0] == "2026-09-15")
    assert peak_day[1:] == (ZONE_PEAK["LZ_HOUSTON"], LOAD_PEAK_MW)
    assert "820 in 2020 Q1" in bodies["doc_perf_quarters"]
    assert "2020-Q1 820" in bodies["doc_perf_quarters"]
    assert "$2.34 million in 2020" in bodies["doc_rev_quarters"]
    assert "2020-Q1 0.42" in bodies["doc_rev_quarters"]
    q2_grid = round(sum(row[5] for row in MONTHS if row[0] in {"2026-04", "2026-05", "2026-06"}), 2)
    q3_grid = round(sum(row[5] for row in MONTHS if row[0] in {"2026-07", "2026-08", "2026-09"}), 2)
    assert next(row for row in QUARTERS if row[0] == "2026-Q2")[5] == q2_grid
    assert next(row for row in QUARTERS if row[0] == "2026-Q3")[5] == q3_grid
    assert next(row for row in QUARTERS if row[0] == "2026-Q3")[1] == 18420
    quarter_records = [row for row in company_items if row["id"].startswith(("ki_qp_", "ki_qr_"))]
    assert len(quarter_records) == 40
    assert "2022 Q1 performance: 2480 installed homes" in bodies["doc_qp_2022q1"]
    assert "2026 Q3 revenue: grid services $13.80 million" in bodies["doc_qr_2026q3"]
    assert "2026 Q4 forecast performance: 19470 installed homes" in bodies["doc_qp_2026q4"]
    assert "2100 installations" in bodies["doc_qp_2026q4"]

    inventory = [row for row in corpus["all_documents"] if row["source_type"] == "warehouse_inventory"]
    inventory_ids = {row["id"] for row in inventory}
    assert {"doc_wh_onhand", "doc_wh_forecast", "doc_wh_houston", "doc_wh_dallas", "doc_wh_austin", "doc_wh_san_antonio"} <= inventory_ids
    inventory_bodies = {row["id"]: row["body"] for row in inventory}
    inventory_items = [row for row in corpus["knowledge_items"] if row["kind"] == "warehouse_inventory"]
    assert len(inventory_items) == 15
    for item in inventory_items:
        assert item["body"] in inventory_bodies[item["document_id"]]
        assert len(item["body"]) <= 180
    september = monthly_issues()[-1][1]
    assert sum(september.values()) == 640
    assert sum(ON_HAND["BP-BATT-46"].values()) == 2140
    assert Q4_INSTALLS == 2100
    assert projected_end("BP-BATT-46", "San Antonio") == -14
    assert "shortfall of 14" in inventory_bodies["doc_wh_forecast"]
    assert "Houston 980" in inventory_bodies["doc_wh_onhand"]
    assert BATTERY_MONTH_END["2026-09"] == ON_HAND["BP-BATT-46"]
    assert "September 2140" in inventory_bodies["doc_wh_onhand"]
    assert "PO-SAT-1048" in inventory_bodies["doc_wh_forecast"]
    assert "safety stock" in inventory_bodies["doc_wh_forecast"]


def test_revenue_chart_uses_quarterly_grid_services_not_complaints():
    from kp.knowledge.artifacts import _company_chart

    chart = _company_chart("I want to see the revenue quaterly basis in a chart")
    assert chart is not None
    title, values, y_title = chart
    assert title == "Quarterly grid services revenue"
    assert values[0]["label"] == "2022 Q1"
    assert values[0]["count"] == 1.85
    assert values[-1]["label"] == "2026 Q3"
    assert y_title == "Grid services ($ million)"
    assert _company_chart("Chart the operational blockers") is None


def test_a_2027_chart_uses_the_forecast_answer_not_old_homes():
    from kp.knowledge.artifacts import _company_charts

    answer = (
        "2027 Q1 forecast revenue: grid services $15.20 million, member bill savings $4.20 million, and new systems $57.0 million. "
        "2027 Q2 forecast revenue: grid services $15.80 million, member bill savings $4.40 million, and new systems $59.0 million. "
        "2027 Q3 forecast revenue: grid services $16.40 million, member bill savings $4.60 million, and new systems $61.0 million. "
        "2027 Q4 forecast revenue: grid services $17.00 million, member bill savings $4.80 million, and new systems $63.0 million."
    )
    charts = _company_charts(
        "chart out the company revenue performance for past quarters and forecast the same for 2027",
        answer,
    )
    assert len(charts) == 2
    past_title, past_values, past_y = charts[0]
    forecast_title, forecast_values, forecast_y = charts[1]
    past_labels = [row["label"] for row in past_values]
    forecast_labels = [row["label"] for row in forecast_values]
    assert past_title == "Past quarterly revenue"
    assert forecast_title == "Forecast quarterly revenue"
    assert past_y == forecast_y == "Grid services ($ million)"
    assert past_labels[0] == "2022 Q1"
    assert past_values[0]["count"] == 1.85
    assert past_labels[-1] == "2026 Q4"
    assert "2027 Q1" not in past_labels
    assert forecast_labels == ["2027 Q1", "2027 Q2", "2027 Q3", "2027 Q4"]
    assert forecast_values[-1]["count"] == 17.0


def test_a_missing_forecast_quarter_cites_the_latest_record():
    from kp.knowledge.retrieve import Bundle
    from kp.knowledge.synthesize import _company_grounded

    bundle = Bundle("customer-complaints", {})
    bundle.add(
        "knowledge_item",
        "ki_qr_2022q1",
        "2022 Q1 revenue: grid services $1.85 million, member bill savings $0.50 million, and new systems $8.2 million.",
        "doc_qr_2022q1",
    )
    bundle.add(
        "knowledge_item",
        "ki_qr_2026q4",
        "2026 Q4 forecast revenue: grid services $14.60 million, member bill savings $4.05 million, and new systems $54.0 million.",
        "doc_qr_2026q4",
    )
    answer, citations = _company_grounded(bundle, "whats the revenue forecast for 2027 Q1")
    assert answer is not None
    assert "15.86" not in answer
    assert "2026 Q4 forecast revenue" in answer
    assert "2022 Q1" not in answer
    assert citations[0]["id"] == "ki_qr_2026q4"


def test_forecast_label_names_the_asked_period():
    from kp.knowledge.synthesize import _forecast_label

    assert _forecast_label("whats the revenue forecast for 2027") == "2027"
    assert _forecast_label("revenue forecast for 2027 Q1") == "2027 Q1"
    from kp.knowledge.synthesize import _forecast_labels

    assert _forecast_labels("revenue forecast for 2027 over Q1,Q2,Q3,Q4 quarters") == [
        "2027 Q1",
        "2027 Q2",
        "2027 Q3",
        "2027 Q4",
    ]
    assert _forecast_labels("create chart for 2027 and 2028 quarters projections")[:4] == [
        "2027 Q1",
        "2027 Q2",
        "2027 Q3",
        "2027 Q4",
    ]
    assert _forecast_labels("create chart for 2027 and 2028 quarters projections")[-4:] == [
        "2028 Q1",
        "2028 Q2",
        "2028 Q3",
        "2028 Q4",
    ]
    span = _forecast_labels("create chart for 2027 to 2030 quarters projections")
    assert span[0] == "2027 Q1"
    assert span[4] == "2028 Q1"
    assert span[8] == "2029 Q1"
    assert span[12] == "2030 Q1"
    assert span[-1] == "2030 Q4"
    assert len(span) == 16
    hyphen = _forecast_labels("forecast revenue from 2027-2029 quarterly")
    assert hyphen[0] == "2027 Q1"
    assert hyphen[4] == "2028 Q1"
    assert hyphen[8] == "2029 Q1"
    assert hyphen[-1] == "2029 Q4"
    assert len(hyphen) == 12


def test_a_forecast_question_sorts_the_latest_revenue_record_first():
    from kp.knowledge.retrieve import _company_sort_key

    class Item:
        def __init__(self, item_id, document_id, body):
            self.id = item_id
            self.document_id = document_id
            self.body = body

    early = Item("ki_qr_2022q1", "doc_qr_2022q1", "2022 Q1 revenue: grid services $1.85 million.")
    forecast = Item(
        "ki_qr_2026q4",
        "doc_qr_2026q4",
        "2026 Q4 forecast revenue: grid services $14.60 million.",
    )
    text = "whats the revenue forecast for 2027 q1"
    assert _company_sort_key(forecast, text) < _company_sort_key(early, text)


def test_a_year_range_sends_every_revenue_quarter():
    from kp.knowledge.retrieve import _company_sort_key, _prompt_record_limit

    class Item:
        def __init__(self, item_id, body):
            self.id = item_id
            self.document_id = item_id.replace("ki_", "doc_")
            self.body = body

    items = [
        Item("ki_qr_2023q2", "2023 Q2 revenue: grid services $3.65 million."),
        Item("ki_qr_2024q1", "2024 Q1 revenue: grid services $5.35 million."),
        Item("ki_qr_2025q3", "2025 Q3 revenue: grid services $9.90 million."),
        Item("ki_qr_2026q3", "2026 Q3 revenue: grid services $13.80 million."),
        Item("ki_qr_2026q4", "2026 Q4 forecast revenue: grid services $14.60 million."),
    ]
    ordered = sorted(items, key=lambda item: _company_sort_key(item, "revenue from 2024 to 2026"))
    assert [item.id for item in ordered] == [
        "ki_qr_2024q1",
        "ki_qr_2025q3",
        "ki_qr_2026q3",
        "ki_qr_2026q4",
        "ki_qr_2023q2",
    ]
    assert _prompt_record_limit("revenue from 2023 to 2026") >= 16
    assert _prompt_record_limit("revenue from 2024 to 2026") >= 13


def test_a_named_quarter_sorts_ahead_of_the_year_summary():
    from kp.knowledge.retrieve import _company_sort_key

    class Item:
        def __init__(self, item_id, document_id, body):
            self.id = item_id
            self.document_id = document_id
            self.body = body

    summary = Item("ki_q10_2024", "doc_perf_quarters", "2024 quarter-end homes: Q1 6920.")
    quarter = Item("ki_qr_2024q2", "doc_qr_2024q2", "2024 Q2 revenue: grid services $6.05 million.")
    text = "what was revenue in 2024 q2"
    assert _company_sort_key(quarter, text) < _company_sort_key(summary, text)


def test_above_forecast_chart_uses_the_previous_answer():
    from kp.knowledge.artifacts import chart_plans

    prior = (
        "2027 Q1 forecast revenue: grid services $15.20 million, member bill savings $4.20 million, and new systems $57.0 million. "
        "2027 Q2 forecast revenue: grid services $15.80 million, member bill savings $4.40 million, and new systems $59.0 million."
    )
    charts = chart_plans(
        "build a chart for above forecast",
        "The top customer complaint themes are installation delays.",
        prior,
    )
    assert charts is not None
    title, values, y_title = charts[0]
    assert len(charts) == 1
    assert title == "Forecast quarterly revenue"
    assert [row["label"] for row in values] == ["2027 Q1", "2027 Q2"]
    assert values[0]["count"] == 15.2
    assert y_title == "Grid services ($ million)"
    assert chart_plans("build a chart for above forecast", "The top customer complaint themes are installation delays.") is None
    yearly = (
        "2027 forecast revenue: grid services $16.20 million, member bill savings $4.40 million, and new systems $62.4 million. "
        "2028 forecast revenue: grid services $17.80 million, member bill savings $4.80 million, and new systems $68.4 million. "
        "2029 forecast revenue: grid services $19.60 million, member bill savings $5.20 million, and new systems $74.8 million. "
        "These are forecasts, not stored records."
    )
    yearly_charts = chart_plans("build a chart for above forecast", "the next period forecast revenue: grid services $16.20 million.", yearly)
    assert yearly_charts is not None
    assert yearly_charts[0][0] == "Forecast revenue"
    assert [row["label"] for row in yearly_charts[0][1]] == ["2027", "2028", "2029"]
    assert yearly_charts[0][1][0]["count"] == 16.2


def test_forecast_follow_up_skips_a_later_non_forecast_reply():
    from kp.knowledge.context import prior_answer

    forecast = "2027 forecast revenue: grid services $16.20 million, member bill savings $4.40 million, and new systems $62.4 million."
    turns = [
        {"role": "assistant", "content": forecast},
        {"role": "user", "content": "build a chart for above forecast"},
        {"role": "assistant", "content": "the next period forecast revenue: grid services $120 million, member bill savings $85 million, and new systems $55 million."},
    ]
    assert prior_answer(turns, "build a chart for above forecast") == forecast


def test_a_model_chart_is_drawn_without_complaint_themes(client, monkeypatch):
    async def fake_synthesize(*args, **kwargs):
        return (
            "July, August, and September customer outages are below.",
            [],
            [
                {
                    "title": "Customer outages",
                    "y": "Customers",
                    "values": [
                        {"label": "July 2026", "count": 121},
                        {"label": "August 2026", "count": 188},
                        {"label": "September 2026", "count": 67},
                    ],
                }
            ],
        )

    monkeypatch.setattr("kp.knowledge.ask.synthesize", fake_synthesize)
    from tests.conftest import login

    session_id = login(client, "ceo")["session_id"]
    response = client.post(
        f"/v1/sessions/{session_id}/ask",
        json={"query": "create chart for customer outages that happened in last 3 months", "channel": "web", "router": "llm"},
    )
    assert response.status_code == 200
    body = response.json()
    assert [artifact["title"] for artifact in body["artifacts"]] == ["Customer outages"]
    assert [row["label"] for row in body["artifacts"][0]["spec"]["data"]["values"]] == [
        "July 2026",
        "August 2026",
        "September 2026",
    ]
    assert "Customer complaint themes" not in body["answer"]


def test_model_payload_chart_points_are_kept():
    from kp.knowledge.synthesize import _parse_agent_payload

    parsed = _parse_agent_payload(
        '{"answer":"August was the peak.","citations":[],"chart":{"title":"Customer outages","y":"Customers","points":[{"label":"August 2026","count":188}]}}'
    )
    assert parsed is not None
    _answer, _citations, charts = parsed
    assert charts[0]["title"] == "Customer outages"
    assert charts[0]["values"] == [{"label": "August 2026", "count": 188.0}]
    dollars = _parse_agent_payload(
        '{"answer":"August was the peak.","citations":[],"chart":{"title":"Customer outages","y":"Customers","data":[{"name":"August 2026","value":"$188"}]}}'
    )
    assert dollars is not None
    assert dollars[2][0]["values"] == [{"label": "August 2026", "count": 188.0}]
    assert _parse_agent_payload('{"answer":"No series.","citations":[],"chart":null}')[2] == []
