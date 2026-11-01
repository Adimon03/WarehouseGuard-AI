"""Tests for API endpoints using FastAPI TestClient."""
import os
import sys

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture(scope="module")
def client(db_session):
    def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestSystemEndpoints:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_system_status(self, client):
        r = client.get("/api/system/status")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"

    def test_data_dictionary(self, client):
        r = client.get("/api/system/data-dictionary")
        assert r.status_code == 200
        data = r.json()
        assert "warehouses" in data
        assert "sensor_readings" in data


class TestEntityEndpoints:
    def test_list_warehouses(self, client):
        r = client.get("/api/warehouses/")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_list_zones(self, client):
        r = client.get("/api/zones/")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_list_sensors(self, client):
        r = client.get("/api/sensors/")
        assert r.status_code == 200
        assert len(r.json()) > 0

    def test_list_inventory(self, client):
        r = client.get("/api/inventory/")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_list_alarms(self, client):
        r = client.get("/api/alarms/")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_list_inspections(self, client):
        r = client.get("/api/inspections/")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_list_remediations(self, client):
        r = client.get("/api/remediations/")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_storage_requirements(self, client):
        r = client.get("/api/storage-requirements/")
        assert r.status_code == 200
        assert len(r.json()) == 10


class TestAnalyticsEndpoints:
    def test_kpis(self, client):
        r = client.get("/api/analytics/kpis")
        assert r.status_code == 200
        data = r.json()
        assert data["total_warehouses"] > 0
        assert "environmental_compliance_rate" in data

    def test_temperature_trend(self, client):
        r = client.get("/api/analytics/trends/temperature")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_alert_metrics(self, client):
        r = client.get("/api/analytics/alert-metrics")
        assert r.status_code == 200
        assert "precision" in r.json()

    def test_alarm_distribution(self, client):
        r = client.get("/api/analytics/alarm-distribution")
        assert r.status_code == 200

    def test_sensor_health(self, client):
        r = client.get("/api/analytics/sensor-health")
        assert r.status_code == 200

    def test_inventory_impact(self, client):
        r = client.get("/api/analytics/inventory-impact")
        assert r.status_code == 200

    def test_compliance_by_zone(self, client):
        r = client.get("/api/analytics/compliance-by-zone")
        assert r.status_code == 200


class TestValidationEndpoint:
    def test_validation_report(self, client):
        r = client.get("/api/validation/report")
        assert r.status_code == 200
        data = r.json()
        assert data["total_checks"] > 0
        assert data["passed"] > 0


class TestAlarmActions:
    def test_acknowledge_alarm(self, client):
        # Get an active alarm
        r = client.get("/api/alarms/?status=active&limit=1")
        data = r.json()
        if data["data"]:
            alarm_id = data["data"][0]["id"]
            r2 = client.post(f"/api/alarms/{alarm_id}/acknowledge", json={"acknowledged_by": "test_user"})
            assert r2.status_code == 200

    def test_resolve_alarm(self, client):
        r = client.get("/api/alarms/?status=active&limit=1")
        data = r.json()
        if data["data"]:
            alarm_id = data["data"][0]["id"]
            r2 = client.post(f"/api/alarms/{alarm_id}/resolve", json={"resolved_by": "test_user"})
            assert r2.status_code == 200


class TestFilters:
    def test_filter_alarms_by_severity(self, client):
        r = client.get("/api/alarms/?severity=critical")
        data = r.json()
        for a in data["data"]:
            assert a["severity"] == "critical"

    def test_filter_sensors_by_type(self, client):
        r = client.get("/api/sensors/?sensor_type=temperature")
        for s in r.json():
            assert s["sensor_type"] == "temperature"
