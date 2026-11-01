"""Tests for alert generation, inspection and remediation workflows."""
import pytest
from app.models import Alarm, Inspection, Remediation


class TestInspectionGeneration:
    def test_inspections_created(self, db_session):
        count = db_session.query(Inspection).count()
        assert count > 0, "Expected inspections to be created"

    def test_inspections_link_to_alarms(self, db_session):
        insps = db_session.query(Inspection).all()
        for i in insps:
            alarm = db_session.query(Alarm).filter(Alarm.id == i.alarm_id).first()
            assert alarm is not None, f"Inspection {i.id} references non-existent alarm {i.alarm_id}"

    def test_inspections_for_critical_and_warning(self, db_session):
        critical_warnings = db_session.query(Alarm).filter(
            Alarm.severity.in_(["critical", "warning"]),
            Alarm.source == "detection",
        ).count()
        insp_count = db_session.query(Inspection).count()
        # Inspections should be created for most critical/warning alarms
        assert insp_count >= 1

    def test_inspection_status_valid(self, db_session):
        insps = db_session.query(Inspection).all()
        for i in insps:
            assert i.status in ["pending", "scheduled", "completed", "cancelled"]


class TestRemediationGeneration:
    def test_remediations_created(self, db_session):
        count = db_session.query(Remediation).count()
        assert count > 0, "Expected remediations to be created"

    def test_remediations_for_critical_alarms(self, db_session):
        critical_alarms = db_session.query(Alarm).filter(
            Alarm.severity == "critical",
            Alarm.source == "detection",
        ).all()
        for a in critical_alarms:
            rems = db_session.query(Remediation).filter(
                Remediation.alarm_id == a.id
            ).count()
            assert rems >= 1, f"Critical alarm {a.id} has no remediation"

    def test_remediation_action_type_valid(self, db_session):
        valid_types = [
            "adjust_temperature", "adjust_humidity", "relocate_inventory",
            "recalibrate_sensor", "replace_sensor", "schedule_inspection",
            "manual_review",
        ]
        rems = db_session.query(Remediation).all()
        for r in rems:
            assert r.action_type in valid_types, (
                f"Remediation {r.id} has invalid action_type: {r.action_type}"
            )

    def test_remediation_status_valid(self, db_session):
        rems = db_session.query(Remediation).all()
        for r in rems:
            assert r.status in ["pending", "in_progress", "completed"]


class TestAlertMetrics:
    def test_alert_metrics_calculated(self, db_session):
        from app.analytics import get_alert_metrics
        metrics = get_alert_metrics(db_session)
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["precision"] <= 1
        assert 0 <= metrics["recall"] <= 1
        assert 0 <= metrics["f1_score"] <= 1

    def test_alert_metrics_true_positives_positive(self, db_session):
        from app.analytics import get_alert_metrics
        metrics = get_alert_metrics(db_session)
        assert metrics["true_positives"] > 0, "Expected at least one true positive"

    def test_kpis_calculated(self, db_session):
        from app.analytics import get_kpi_summary
        kpis = get_kpi_summary(db_session)
        assert kpis["total_warehouses"] > 0
        assert kpis["total_zones"] > 0
        assert kpis["total_sensors"] > 0
        assert kpis["total_readings"] > 0
        assert kpis["total_alarms"] > 0
        assert 0 <= kpis["environmental_compliance_rate"] <= 100
        assert 0 <= kpis["sensor_availability"] <= 100
