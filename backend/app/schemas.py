"""Pydantic schemas for request/response serialization."""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict


# ── Warehouse ──────────────────────────────────────────────────────────────
class WarehouseOut(BaseModel):
    id: int
    name: str
    location: str
    total_area_sqm: float
    manager: Optional[str] = None
    created_at: datetime
    zone_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# ── Zone ───────────────────────────────────────────────────────────────────
class ZoneOut(BaseModel):
    id: int
    warehouse_id: int
    name: str
    zone_type: str
    area_sqm: float
    max_occupancy: int
    min_temp_c: float
    max_temp_c: float
    min_humidity_pct: float
    max_humidity_pct: float
    sensor_count: Optional[int] = None
    inventory_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# ── Sensor ─────────────────────────────────────────────────────────────────
class SensorOut(BaseModel):
    id: int
    zone_id: int
    sensor_type: str
    status: str
    manufacturer: str
    model: str
    installed_at: datetime
    last_calibrated_at: datetime
    zone_mappings_count: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


class SensorZoneMappingOut(BaseModel):
    id: int
    sensor_id: int
    zone_id: int
    is_primary: bool
    justification: Optional[str] = None
    assigned_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Sensor Reading ─────────────────────────────────────────────────────────
class SensorReadingOut(BaseModel):
    id: int
    sensor_id: int
    reading_timestamp: datetime
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    occupancy_count: Optional[int] = None
    door_state: Optional[str] = None
    is_missing: bool
    model_config = ConfigDict(from_attributes=True)


# ── Door Event ─────────────────────────────────────────────────────────────
class DoorEventOut(BaseModel):
    id: int
    zone_id: int
    sensor_id: int
    event_timestamp: datetime
    event_type: str
    duration_seconds: Optional[float] = None
    model_config = ConfigDict(from_attributes=True)


# ── Storage Requirement ───────────────────────────────────────────────────
class StorageRequirementOut(BaseModel):
    id: int
    product_category: str
    min_temp_c: float
    max_temp_c: float
    min_humidity_pct: float
    max_humidity_pct: float
    dwell_time_limit_days: int
    compatible_zone_types: List[str]
    model_config = ConfigDict(from_attributes=True)


# ── Inventory Lot ──────────────────────────────────────────────────────────
class InventoryLotOut(BaseModel):
    id: int
    zone_id: int
    product_name: str
    product_category: str
    quantity: int
    unit: str
    batch_number: str
    arrival_date: datetime
    departure_date: Optional[datetime] = None
    status: str
    zone_name: Optional[str] = None
    zone_type: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


# ── Alarm ──────────────────────────────────────────────────────────────────
class AlarmInventoryLotOut(BaseModel):
    id: int
    alarm_id: int
    inventory_lot_id: int
    model_config = ConfigDict(from_attributes=True)


class AlarmOut(BaseModel):
    id: int
    alarm_type: str
    severity: str
    zone_id: int
    sensor_id: Optional[int] = None
    start_timestamp: datetime
    end_timestamp: Optional[datetime] = None
    description: str
    recommended_action: str
    status: str
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    affected_inventory_ids: List[int] = []
    zone_name: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AlarmAcknowledge(BaseModel):
    acknowledged_by: str = "system"


class AlarmResolve(BaseModel):
    resolved_by: str = "system"


# ── Inspection ─────────────────────────────────────────────────────────────
class InspectionOut(BaseModel):
    id: int
    alarm_id: int
    inspector_name: str
    inspection_timestamp: datetime
    status: str
    findings: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class InspectionCreate(BaseModel):
    alarm_id: int
    inspector_name: str
    inspection_timestamp: datetime
    status: str = "pending"
    findings: Optional[str] = None
    notes: Optional[str] = None


# ── Remediation ────────────────────────────────────────────────────────────
class RemediationOut(BaseModel):
    id: int
    alarm_id: int
    inspection_id: Optional[int] = None
    action_type: str
    description: str
    performed_by: str
    performed_at: datetime
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RemediationCreate(BaseModel):
    alarm_id: int
    inspection_id: Optional[int] = None
    action_type: str
    description: str
    performed_by: str
    performed_at: datetime
    status: str = "pending"


# ── Analytics ──────────────────────────────────────────────────────────────
class KpiSummary(BaseModel):
    total_warehouses: int
    total_zones: int
    total_sensors: int
    total_readings: int
    total_inventory_lots: int
    total_alarms: int
    active_alarms: int
    critical_alarms: int
    acknowledged_alarms: int
    resolved_alarms: int
    environmental_compliance_rate: float
    sensor_availability: float
    missing_reading_pct: float
    affected_inventory_lots: int
    open_inspections: int
    open_remediations: int
    mean_time_to_acknowledge_hours: Optional[float] = None
    mean_time_to_resolve_hours: Optional[float] = None


class AlertMetrics(BaseModel):
    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int
    total_ground_truth: int
    total_detected: int


class TrendPoint(BaseModel):
    timestamp: str
    value: float
    label: Optional[str] = None


class ValidationReport(BaseModel):
    total_checks: int
    passed: int
    failed: int
    warnings: int
    checks: List[Any]


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
