import json

from tests.conftest import login


def test_dashboards_quote_synthetic_file_facts(client):
    login(client, "ceo")
    ceo = client.get("/v1/dashboards/ceo")
    assert ceo.status_code == 200
    files = ceo.json()["files"]
    blob = json.dumps(files)
    assert "North Austin" in blob
    assert "477" in blob
    assert "San Marcos" in blob
    assert "Cedar Park" in blob
    assert "best market" not in blob.lower()
    north = next(row for row in files["markets"] if row["market_id"] == "MKT-002")
    assert "primary" in " ".join(north["lines"]).lower()
    installations = next(row for row in files["metrics"] if row["key"] == "installations_completed")
    assert installations["value"] == "477"

    login(client, "operations_manager")
    ops = client.get("/v1/dashboards/operations_manager").json()["files"]
    text = json.dumps(ops)
    assert "V001" in text
    assert "P018" in text
    assert "J001" in text
    assert "J007" in text
    assert "W002" in text
    gap = next(row for row in ops["kit_gaps"] if row["van_id"] == "V001" and row["part_id"] == "P018")
    assert gap["job_id"] == "J001"
    assert gap["van_quantity"] == "0"

    login(client, "engineer")
    engineer = client.get("/v1/dashboards/engineer").json()["files"]
    assert any(row["device_id"] == "DEV-001" and row["status"] == "Offline" for row in engineer["offline"])
    unresolved = next(row for row in engineer["under_investigation"] if row["incident_id"] == "INC-008")
    assert unresolved["confirmed_root_cause"] == "Under Investigation"
    assert "estimator" not in json.dumps(unresolved).lower()
    assert any(row["device_id"] == "DEV-054" and row["status"] == "Online" for row in engineer["proactive_watch"])
    firmware = next(row for row in engineer["metrics"] if row["key"] == "firmware_430")
    assert firmware["value"] == "2"
