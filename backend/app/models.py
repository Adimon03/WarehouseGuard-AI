"""SQLAlchemy ORM models for WarehouseGuard AI.

Every entity uses deterministic integer primary keys so that data generation
with a fixed seed produces identical IDs across runs.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=True, unique=True)  # WH-001
    name = Column(String(120), nullable=False, unique=True)
    location = Column(String(200), nullable=False)
    total_area_sqm = Column(Float, nullable=False)
    manager = Column(String(100))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    zones = relationship("Zone", back_populates="warehouse", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True, unique=True)  # ZONE-001-001
    warehouse_id = Column(Integer, ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(120), nullable=False)
    zone_type = Column(String(40), nullable=False)  # ambient | cold_storage | frozen | hazardous
    area_sqm = Column(Float, nullable=False)
    max_occupancy = Column(Integer, nullable=False, default=50)
    min_temp_c = Column(Float, nullable=False)
    max_temp_c = Column(Float, nullable=False)
    min_humidity_pct = Column(Float, nullable=False)
    max_humidity_pct = Column(Float, nullable=False)

    warehouse = relationship("Warehouse", back_populates="zones")
    sensors = relationship("Sensor", back_populates="zone", cascade="all, delete-orphan")
    door_events = relationship("DoorEvent", back_populates="zone", cascade="all, delete-orphan")
    inventory_lots = relationship("InventoryLot", back_populates="zone", cascade="all, delete-orphan")


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True)
    code = Column(String(40), nullable=True, unique=True)  # SNS-001-TEMP-01
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    sensor_type = Column(String(40), nullable=False)  # temperature | humidity | occupancy | door
    status = Column(String(40), nullable=False, default="active")  # active | drift | offline
    manufacturer = Column(String(80), nullable=False, default="Generic")
    model = Column(String(80), nullable=False, default="SM-100")
    installed_at = Column(DateTime, nullable=False)
    last_calibrated_at = Column(DateTime, nullable=False)

    zone = relationship("Zone", back_populates="sensors")
    readings = relationship("SensorReading", back_populates="sensor", cascade="all, delete-orphan")
    zone_mappings = relationship("SensorZoneMapping", back_populates="sensor", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_sensors_zone_type", "zone_id", "sensor_type"),
    )


class SensorZoneMapping(Base):
    """Tracks all zone assignments for a sensor.  A sensor mapped to multiple
    zones without a justification is a known data-quality anomaly."""

    __tablename__ = "sensor_zone_mappings"

    id = Column(Integer, primary_key=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, nullable=False, default=True)
    justification = Column(String(255), nullable=True)
    assigned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    sensor = relationship("Sensor", back_populates="zone_mappings")
    zone = relationship("Zone")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True)
    code = Column(String(80), nullable=True)  # RDG-0000001
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    reading_timestamp = Column(DateTime, nullable=False)
    temperature_c = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)
    occupancy_count = Column(Integer, nullable=True)
    door_state = Column(String(10), nullable=True)  # open | closed
    is_missing = Column(Boolean, nullable=False, default=False)
    # Internal flag for ground-truth tracking — NEVER used by detection logic.
    is_anomaly_injected = Column(Boolean, nullable=False, default=False)

    sensor = relationship("Sensor", back_populates="readings")

    __table_args__ = (
        Index("ix_readings_sensor_time", "sensor_id", "reading_timestamp"),
        Index("ix_readings_timestamp", "reading_timestamp"),
    )


class DoorEvent(Base):
    __tablename__ = "door_events"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True)  # DEV-000001
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="CASCADE"), nullable=False)
    event_timestamp = Column(DateTime, nullable=False)
    event_type = Column(String(10), nullable=False)  # open | close
    duration_seconds = Column(Float, nullable=True)
    is_anomaly_injected = Column(Boolean, nullable=False, default=False)

    zone = relationship("Zone", back_populates="door_events")
    sensor = relationship("Sensor")

    __table_args__ = (
        Index("ix_door_events_zone_time", "zone_id", "event_timestamp"),
    )


class StorageRequirement(Base):
    __tablename__ = "storage_requirements"

    id = Column(Integer, primary_key=True)
    product_category = Column(String(80), nullable=False, unique=True)
    min_temp_c = Column(Float, nullable=False)
    max_temp_c = Column(Float, nullable=False)
    min_humidity_pct = Column(Float, nullable=False)
    max_humidity_pct = Column(Float, nullable=False)
    dwell_time_limit_days = Column(Integer, nullable=False)
    compatible_zone_types = Column(JSON, nullable=False)  # e.g. ["cold_storage", "frozen"]


class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True, unique=True)  # LOT-2026-000001
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(150), nullable=False)
    product_category = Column(String(80), nullable=False)
    quantity = Column(Integer, nullable=False, default=100)
    unit = Column(String(20), nullable=False, default="units")
    batch_number = Column(String(60), nullable=False)
    arrival_date = Column(DateTime, nullable=False)
    departure_date = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="stored")  # stored | departed | expired

    zone = relationship("Zone", back_populates="inventory_lots")

    __table_args__ = (
        Index("ix_inventory_zone", "zone_id"),
        Index("ix_inventory_category", "product_category"),
    )


class Alarm(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True)  # ALM-000001
    alarm_type = Column(String(60), nullable=False)
    severity = Column(String(20), nullable=False)  # critical | warning | info
    zone_id = Column(Integer, ForeignKey("zones.id", ondelete="CASCADE"), nullable=False)
    sensor_id = Column(Integer, ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True)
    start_timestamp = Column(DateTime, nullable=False)
    end_timestamp = Column(DateTime, nullable=True)
    description = Column(Text, nullable=False)
    recommended_action = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="active")  # active | acknowledged | resolved
    source = Column(String(20), nullable=False, default="detection")  # preexisting | detection
    acknowledged_at = Column(DateTime, nullable=True)
    acknowledged_by = Column(String(100), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    zone = relationship("Zone")
    sensor = relationship("Sensor")
    affected_inventory = relationship("AlarmInventoryLot", back_populates="alarm", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="alarm", cascade="all, delete-orphan")
    remediations = relationship("Remediation", back_populates="alarm", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_alarms_status", "status"),
        Index("ix_alarms_zone", "zone_id"),
    )


class AlarmInventoryLot(Base):
    """Junction table linking alarms to affected inventory lots."""

    __tablename__ = "alarm_inventory_lots"

    id = Column(Integer, primary_key=True)
    alarm_id = Column(Integer, ForeignKey("alarms.id", ondelete="CASCADE"), nullable=False)
    inventory_lot_id = Column(Integer, ForeignKey("inventory_lots.id", ondelete="CASCADE"), nullable=False)

    alarm = relationship("Alarm", back_populates="affected_inventory")
    inventory_lot = relationship("InventoryLot")

    __table_args__ = (
        UniqueConstraint("alarm_id", "inventory_lot_id", name="uq_alarm_inventory"),
    )


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True)  # INSP-000001
    alarm_id = Column(Integer, ForeignKey("alarms.id", ondelete="CASCADE"), nullable=False)
    inspector_name = Column(String(100), nullable=False)
    inspection_timestamp = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | scheduled | completed | cancelled
    findings = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    alarm = relationship("Alarm", back_populates="inspections")
    remediations = relationship("Remediation", back_populates="inspection")


class Remediation(Base):
    __tablename__ = "remediations"

    id = Column(Integer, primary_key=True)
    code = Column(String(30), nullable=True)  # REM-000001
    alarm_id = Column(Integer, ForeignKey("alarms.id", ondelete="CASCADE"), nullable=False)
    inspection_id = Column(Integer, ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True)
    action_type = Column(String(60), nullable=False)
    description = Column(Text, nullable=False)
    performed_by = Column(String(100), nullable=False)
    performed_at = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # pending | in_progress | completed
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    alarm = relationship("Alarm", back_populates="remediations")
    inspection = relationship("Inspection", back_populates="remediations")


class GroundTruthAnomaly(Base):
    """Ground-truth labels for known anomalies.

    This table is populated during data generation to record which entities
    are known anomalies.  The anomaly-detection logic must NEVER query this
    table — it is used solely for evaluation (precision / recall / F1).
    """

    __tablename__ = "ground_truth_anomalies"

    id = Column(Integer, primary_key=True)
    anomaly_type = Column(String(60), nullable=False)
    entity_type = Column(String(40), nullable=False)  # sensor_reading | door_event | sensor | inventory_lot | alarm
    entity_id = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    true_severity = Column(String(20), nullable=False)  # critical | warning | info
    injected_at = Column(DateTime, nullable=False)

    __table_args__ = (
        Index("ix_gt_entity", "entity_type", "entity_id"),
    )
