"""Tests for the four required negative scenarios."""
import pytest
from sqlalchemy import text
from app.models import Alarm, SensorZoneMapping, SensorReading


class TestNegativeScenario1:
    """Inventory lot assigned to an incompatible zone."""

    def test_incompatible_inventory_exists(self, db_session):
        count = db_session.execute(text("""
            SELECT COUNT(*) FROM inventory_lots il
            JOIN zones z ON il.zone_id = z.id
            JOIN storage_requirements sr ON il.product_category = sr.product_category
            WHERE z.zone_type NOT IN (SELECT value FROM json_each(sr.compatible_zone_types))
        """)).scalar()
        assert count > 0, "Expected incompatible inventory lots"

    def test_incompatible_inventory_alarms_generated(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "inventory_incompatible_zone",
            Alarm.source == "detection",
        ).count()
        assert alarms > 0, "Expected detection alarms for incompatible inventory"

    def test_validation_catches_incompatible(self, db_session):
        from app.validation import run_validation
        report = run_validation(db_session)
        failed_names = [c["check"] for c in report["checks"] if c["status"] == "fail"]
        assert any("incompatible" in n.lower() for n in failed_names), (
            "Validation should flag incompatible inventory"
        )


class TestNegativeScenario2:
    """Sensor mapped to multiple zones without justification."""

    def test_multi_zone_sensors_exist(self, db_session):
        multi = db_session.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT sensor_id FROM sensor_zone_mappings
                GROUP BY sensor_id HAVING COUNT(*) > 1
            )
        """)).scalar()
        assert multi > 0, "Expected sensors mapped to multiple zones"

    def test_unjustified_mappings_exist(self, db_session):
        count = db_session.query(SensorZoneMapping).filter(
            SensorZoneMapping.justification.is_(None),
            SensorZoneMapping.is_primary == False,
        ).count()
        assert count > 0, "Expected unjustified secondary zone mappings"

    def test_validation_catches_multi_zone(self, db_session):
        from app.validation import run_validation
        report = run_validation(db_session)
        failed_names = [c["check"] for c in report["checks"] if c["status"] == "fail"]
        assert any("multiple zones" in n.lower() for n in failed_names)


class TestNegativeScenario3:
    """Missing sensor readings must NOT be treated as normal."""

    def test_missing_readings_exist(self, db_session):
        count = db_session.query(SensorReading).filter(
            SensorReading.is_missing == True
        ).count()
        assert count > 0, "Expected missing readings"

    def test_sensor_outage_alarms_generated(self, db_session):
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "sensor_outage",
        ).count()
        assert alarms > 0, (
            "Missing readings should generate sensor_outage alarms, "
            "NOT be treated as normal"
        )

    def test_validation_confirms_detection(self, db_session):
        from app.validation import run_validation
        report = run_validation(db_session)
        passed_names = [c["check"] for c in report["checks"] if c["status"] == "pass"]
        assert any("missing readings detected" in n.lower() for n in passed_names), (
            "Validation should confirm missing readings are detected as anomalies"
        )


class TestNegativeScenario4:
    """Alarm not linked to affected inventory lots."""

    def test_preexisting_alarms_without_links(self, db_session):
        """Pre-existing alarms (from data generator) should have no inventory links."""
        preexisting = db_session.query(Alarm).filter(
            Alarm.source == "preexisting"
        ).all()
        assert len(preexisting) > 0, "Expected pre-existing alarms"
        from app.models import AlarmInventoryLot
        for a in preexisting:
            links = db_session.query(AlarmInventoryLot).filter(
                AlarmInventoryLot.alarm_id == a.id
            ).count()
            assert links == 0, f"Pre-existing alarm {a.id} should have no inventory links"

    def test_validation_catches_unlinked_alarms(self, db_session):
        from app.validation import run_validation
        report = run_validation(db_session)
        failed_names = [c["check"] for c in report["checks"] if c["status"] == "fail"]
        assert any("without inventory linkage" in n.lower() for n in failed_names), (
            "Validation should flag alarms without inventory links"
        )

    def test_ground_truth_records_scenario(self, db_session):
        from app.models import GroundTruthAnomaly
        gt = db_session.query(GroundTruthAnomaly).filter(
            GroundTruthAnomaly.anomaly_type == "alarm_missing_inventory_link"
        ).count()
        assert gt > 0, "Expected ground truth entries for missing inventory link scenario"
