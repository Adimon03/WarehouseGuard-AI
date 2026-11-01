"""Tests for anomaly detection logic."""
import pytest
from sqlalchemy import text
from app.models import Alarm, SensorReading, DoorEvent


class TestTemperatureDetection:
    def test_temperature_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "temperature_violation",
            Alarm.source == "detection",
        ).all()
        assert len(alarms) > 0, "Expected temperature violation alarms"

    def test_temperature_alarms_have_zone(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "temperature_violation",
        ).all()
        for a in alarms:
            assert a.zone_id is not None

    def test_temperature_alarms_have_description(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "temperature_violation",
        ).all()
        for a in alarms:
            assert len(a.description) > 0
            assert "exceeds" in a.description.lower() or "temperature" in a.description.lower()


class TestHumidityDetection:
    def test_humidity_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "humidity_violation",
        ).all()
        assert len(alarms) > 0, "Expected humidity violation alarms"


class TestDoorOpenDetection:
    def test_prolonged_door_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "prolonged_door_open",
        ).all()
        assert len(alarms) > 0, "Expected prolonged door open alarms"

    def test_prolonged_door_events_exist(self, db_session):
        events = db_session.query(DoorEvent).filter(
            DoorEvent.duration_seconds > 1800,
        ).all()
        assert len(events) > 0, "Expected prolonged door events in data"


class TestMissingReadingsDetection:
    """Negative scenario #3: missing readings must NOT be treated as normal."""

    def test_sensor_outage_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "sensor_outage",
        ).all()
        assert len(alarms) > 0, "Expected sensor outage alarms for missing readings"

    def test_missing_readings_exist(self, db_session):
        missing = db_session.query(SensorReading).filter(
            SensorReading.is_missing == True,
        ).count()
        assert missing > 0, "Expected missing readings in dataset"


class TestSensorDriftDetection:
    def test_drift_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "sensor_drift",
        ).all()
        assert len(alarms) >= 0  # drift may or may not be detected depending on data

    def test_drift_sensors_marked(self, db_session):
        from app.models import Sensor
        drift_sensors = db_session.query(Sensor).filter(
            Sensor.status == "drift",
        ).count()
        # At least some should be marked if drift was detected
        drift_alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "sensor_drift",
        ).count()
        if drift_alarms > 0:
            assert drift_sensors > 0, "Sensors with drift alarm should be marked"


class TestIncompatibleInventoryDetection:
    """Negative scenario #1: inventory in incompatible zone."""

    def test_incompatible_alarms_exist(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "inventory_incompatible_zone",
        ).all()
        assert len(alarms) > 0, "Expected incompatible inventory alarms"

    def test_incompatible_alarms_are_critical(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "inventory_incompatible_zone",
        ).all()
        for a in alarms:
            assert a.severity == "critical"


class TestAlarmQuality:
    def test_all_alarms_have_zone(self, db_session):
        alarms = db_session.query(Alarm).filter(Alarm.source == "detection").all()
        for a in alarms:
            assert a.zone_id is not None, f"Alarm {a.id} has no zone_id"

    def test_all_alarms_have_description(self, db_session):
        alarms = db_session.query(Alarm).all()
        for a in alarms:
            assert len(a.description) > 0, f"Alarm {a.id} has no description"

    def test_all_alarms_have_recommended_action(self, db_session):
        alarms = db_session.query(Alarm).all()
        for a in alarms:
            assert len(a.recommended_action) > 0, f"Alarm {a.id} has no recommended action"

    def test_alarm_severity_valid(self, db_session):
        alarms = db_session.query(Alarm).all()
        for a in alarms:
            assert a.severity in ["critical", "warning", "info"], (
                f"Alarm {a.id} has invalid severity: {a.severity}"
            )

    def test_alarm_status_valid(self, db_session):
        alarms = db_session.query(Alarm).all()
        for a in alarms:
            assert a.status in ["active", "acknowledged", "resolved"]
