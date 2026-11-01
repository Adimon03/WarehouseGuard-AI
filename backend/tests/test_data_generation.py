"""Tests for data generation, referential integrity and reproducibility."""
import os
import sys
import tempfile

import pytest
from sqlalchemy import text

from app.models import (
    Warehouse, Zone, Sensor, SensorReading, DoorEvent,
    InventoryLot, StorageRequirement, GroundTruthAnomaly,
)


class TestDataGeneration:
    def test_warehouses_created(self, db_session):
        count = db_session.query(Warehouse).count()
        assert count >= 3, f"Expected >=3 warehouses, got {count}"

    def test_zones_created(self, db_session):
        count = db_session.query(Zone).count()
        assert count >= 15, f"Expected >=15 zones, got {count}"

    def test_sensors_created(self, db_session):
        count = db_session.query(Sensor).count()
        assert count >= 45, f"Expected >=45 sensors, got {count}"

    def test_sensor_readings_created(self, db_session):
        count = db_session.query(SensorReading).count()
        assert count >= 18000, f"Expected >=18000 readings, got {count}"

    def test_inventory_lots_created(self, db_session):
        count = db_session.query(InventoryLot).count()
        assert count >= 500, f"Expected >=500 inventory lots, got {count}"

    def test_storage_requirements_created(self, db_session):
        count = db_session.query(StorageRequirement).count()
        assert count == 10, f"Expected 10 storage requirements, got {count}"

    def test_ground_truth_created(self, db_session):
        count = db_session.query(GroundTruthAnomaly).count()
        assert count > 0, "Expected ground truth anomalies"

    def test_door_events_created(self, db_session):
        count = db_session.query(DoorEvent).count()
        assert count > 0, "Expected door events to be created"


class TestReferentialIntegrity:
    def test_zone_warehouse_fk(self, db_session):
        orphans = db_session.execute(text(
            "SELECT COUNT(*) FROM zones z LEFT JOIN warehouses w ON z.warehouse_id = w.id WHERE w.id IS NULL"
        )).scalar()
        assert orphans == 0, f"{orphans} zones with invalid warehouse_id"

    def test_sensor_zone_fk(self, db_session):
        orphans = db_session.execute(text(
            "SELECT COUNT(*) FROM sensors s LEFT JOIN zones z ON s.zone_id = z.id WHERE z.id IS NULL"
        )).scalar()
        assert orphans == 0

    def test_reading_sensor_fk(self, db_session):
        orphans = db_session.execute(text(
            "SELECT COUNT(*) FROM sensor_readings sr LEFT JOIN sensors s ON sr.sensor_id = s.id WHERE s.id IS NULL"
        )).scalar()
        assert orphans == 0

    def test_inventory_zone_fk(self, db_session):
        orphans = db_session.execute(text(
            "SELECT COUNT(*) FROM inventory_lots il LEFT JOIN zones z ON il.zone_id = z.id WHERE z.id IS NULL"
        )).scalar()
        assert orphans == 0

    def test_no_duplicate_pks(self, db_session):
        for table in ["warehouses", "zones", "sensors", "sensor_readings",
                       "inventory_lots", "storage_requirements"]:
            dups = db_session.execute(text(
                f"SELECT id, COUNT(*) c FROM {table} GROUP BY id HAVING c > 1"
            )).fetchall()
            assert not dups, f"Duplicate PKs in {table}: {dups}"


class TestReproducibility:
    def test_same_seed_same_counts(self, db_session):
        """Regenerate with same seed and verify row counts match.
        Then restore the test data since generate_dataset resets the DB."""
        from app.data_generator import generate_dataset, compute_checksums
        from app.anomaly_detection import run_detection

        checksums1 = compute_checksums(db_session)
        generate_dataset(db_session, full=False)
        checksums2 = compute_checksums(db_session)

        for key in checksums1:
            assert checksums1[key] == checksums2[key], (
                f"Reproducibility failed: {key} differs "
                f"({checksums1[key]} vs {checksums2[key]})"
            )

        # Restore the test data that was destroyed by generate_dataset
        generate_dataset(db_session, full=False)
        run_detection(db_session)


class TestDataQuality:
    def test_allowed_sensor_types(self, db_session):
        types = db_session.execute(text("SELECT DISTINCT sensor_type FROM sensors")).fetchall()
        for t in types:
            assert t[0] in ["temperature", "humidity", "occupancy", "door"]

    def test_allowed_zone_types(self, db_session):
        types = db_session.execute(text("SELECT DISTINCT zone_type FROM zones")).fetchall()
        for t in types:
            assert t[0] in ["ambient", "cold_storage", "frozen", "hazardous"]

    def test_departure_after_arrival(self, db_session):
        bad = db_session.execute(text(
            "SELECT COUNT(*) FROM inventory_lots WHERE departure_date IS NOT NULL AND departure_date < arrival_date"
        )).scalar()
        assert bad == 0, f"{bad} lots with departure before arrival"

    def test_calibrated_after_installed(self, db_session):
        bad = db_session.execute(text(
            "SELECT COUNT(*) FROM sensors WHERE last_calibrated_at < installed_at"
        )).scalar()
        assert bad == 0
