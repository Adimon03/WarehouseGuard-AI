"""Tests for inventory impact analysis and alarm-inventory linkage."""
import pytest
from sqlalchemy import text
from app.models import Alarm, AlarmInventoryLot, InventoryLot


class TestInventoryLinkage:
    def test_alarm_inventory_junction_exists(self, db_session):
        links = db_session.query(AlarmInventoryLot).count()
        assert links > 0, "Expected alarm-inventory lot links"

    def test_detection_alarms_have_inventory_links(self, db_session):
        """Detection alarms (not pre-existing) should link to affected inventory
        when inventory exists in the zone during the alarm time window."""
        unlinked = db_session.execute(text("""
            SELECT a.id FROM alarms a
            WHERE a.source = 'detection'
              AND a.alarm_type IN (
                'temperature_violation', 'humidity_violation',
                'prolonged_door_open', 'abnormal_occupancy', 'sensor_outage'
              )
              AND NOT EXISTS (
                SELECT 1 FROM alarm_inventory_lots ail WHERE ail.alarm_id = a.id
              )
              AND EXISTS (
                SELECT 1 FROM inventory_lots il
                WHERE il.zone_id = a.zone_id
                  AND il.arrival_date <= COALESCE(a.end_timestamp, '2026-12-31')
                  AND (il.departure_date IS NULL OR il.departure_date >= a.start_timestamp)
              )
            LIMIT 10
        """)).fetchall()
        assert len(unlinked) == 0, (
            f"{len(unlinked)} detection alarms missing inventory links: "
            f"{[r[0] for r in unlinked]}"
        )

    def test_incompatible_inventory_alarms_link_specific_lot(self, db_session):
        """Incompatible inventory alarms should link directly to the affected lot."""
        alarms = db_session.query(Alarm).filter(
            Alarm.alarm_type == "inventory_incompatible_zone",
            Alarm.source == "detection",
        ).all()
        for a in alarms:
            links = db_session.query(AlarmInventoryLot).filter(
                AlarmInventoryLot.alarm_id == a.id
            ).count()
            assert links >= 1, f"Alarm {a.id} (incompatible) has no inventory link"

    def test_affected_inventory_in_correct_zone(self, db_session):
        """Inventory lots linked to an alarm should be in the alarm's zone."""
        links = db_session.execute(text("""
            SELECT ail.alarm_id, ail.inventory_lot_id, a.zone_id, il.zone_id
            FROM alarm_inventory_lots ail
            JOIN alarms a ON ail.alarm_id = a.id
            JOIN inventory_lots il ON ail.inventory_lot_id = il.id
        """)).fetchall()
        for r in links:
            assert r[2] == r[3], (
                f"Alarm {r[0]} (zone {r[2]}) linked to lot {r[1]} in zone {r[3]}"
            )


class TestInventoryImpactMetrics:
    def test_affected_inventory_count_positive(self, db_session):
        from app.analytics import get_inventory_impact
        impact = get_inventory_impact(db_session)
        by_type = impact["by_alarm_type"]
        total = sum(d["lot_count"] for d in by_type)
        assert total > 0, "Expected some affected inventory lots"

    def test_inventory_impact_has_by_severity(self, db_session):
        from app.analytics import get_inventory_impact
        impact = get_inventory_impact(db_session)
        assert "by_severity" in impact
        assert len(impact["by_severity"]) > 0
