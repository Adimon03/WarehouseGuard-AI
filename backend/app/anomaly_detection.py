"""Rule-based anomaly detection for WarehouseGuard AI.

Scans sensor readings, door events and inventory assignments to detect:
  - Temperature violations
  - Humidity violations
  - Prolonged door-open events
  - Abnormal occupancy
  - Missing readings / sensor outages  (NOT treated as normal — scenario #3)
  - Sensor drift
  - Inventory assigned to incompatible zones (scenario #1)

For each detected anomaly an Alarm is created and linked to affected
inventory lots via AlarmInventoryLot.  Inspections and remediations are
generated for critical / warning alarms.

The detection logic NEVER queries the GroundTruthAnomaly table — it works
solely from the operational data.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models import (
    Alarm, AlarmInventoryLot, Inspection, Remediation, Sensor, SensorReading,
    DoorEvent, InventoryLot, Zone, StorageRequirement, SensorZoneMapping,
)

READING_INTERVAL_MIN = 15
PROLONGED_DOOR_THRESHOLD_SEC = 1800  # 30 minutes
DRIFT_THRESHOLD_FACTOR = 0.35        # fraction of zone range
TEMP_CRITICAL_DELTA = 5.0           # °C deviation for critical severity
HUM_CRITICAL_DELTA = 15.0            # % deviation for critical severity

INSPECTORS = ["Alice Chen", "Bob Patel", "Carol Smith", "David Osei",
              "Elena Rossi", "Frank Mueller"]
REMEDIATORS = ["George Lee", "Hannah Park", "Ivan Petrov", "Julia Costa"]


# ═══════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════

def run_detection(db: Session) -> dict:
    """Run all anomaly detection and generate alarms, inspections and
    remediations.

    Returns a summary dict with counts.
    """
    # Remove previously-generated detection alarms so re-runs are idempotent
    _clear_detection_alarms(db)

    max_id = db.query(func.max(Alarm.id)).scalar() or 0
    counter = {"alarm_id": max_id + 1}
    stats = {}

    stats["temperature"] = _detect_temperature_violations(db, counter)
    stats["humidity"] = _detect_humidity_violations(db, counter)
    stats["door_open"] = _detect_prolonged_door_open(db, counter)
    stats["occupancy"] = _detect_abnormal_occupancy(db, counter)
    stats["missing"] = _detect_missing_readings(db, counter)
    stats["drift"] = _detect_sensor_drift(db, counter)
    stats["incompatible"] = _detect_incompatible_inventory(db, counter)

    db.flush()

    n_alarms = sum(stats.values())
    n_inspections, n_remediations = _generate_inspections_and_remediations(db)

    db.commit()
    return {
        "alarms_created": n_alarms,
        "inspections_created": n_inspections,
        "remediations_created": n_remediations,
        "by_type": stats,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _clear_detection_alarms(db: Session):
    """Delete all detection-sourced alarms and their children."""
    det_alarm_ids = [a.id for a in db.query(Alarm.id).filter(
        Alarm.source == "detection").all()]
    if det_alarm_ids:
        db.query(AlarmInventoryLot).filter(
            AlarmInventoryLot.alarm_id.in_(det_alarm_ids)).delete(
            synchronize_session=False)
        db.query(Remediation).filter(
            Remediation.alarm_id.in_(det_alarm_ids)).delete(
            synchronize_session=False)
        db.query(Inspection).filter(
            Inspection.alarm_id.in_(det_alarm_ids)).delete(
            synchronize_session=False)
        db.query(Alarm).filter(Alarm.source == "detection").delete(
            synchronize_session=False)
        db.flush()


def _link_inventory(db: Session, alarm: Alarm) -> list[int]:
    """Find inventory lots present in the alarm's zone during the alarm
    time window and create AlarmInventoryLot entries.

    Returns a list of linked inventory-lot IDs.
    """
    end_ts = alarm.end_timestamp or datetime(2026, 12, 31, 23, 59, 59)
    lots = db.query(InventoryLot).filter(
        InventoryLot.zone_id == alarm.zone_id,
        InventoryLot.arrival_date <= end_ts,
    ).filter(
        (InventoryLot.departure_date.is_(None)) |
        (InventoryLot.departure_date >= alarm.start_timestamp)
    ).all()

    linked_ids = []
    for lot in lots:
        db.add(AlarmInventoryLot(
            alarm_id=alarm.id,
            inventory_lot_id=lot.id,
        ))
        linked_ids.append(lot.id)
    return linked_ids


def _parse_dt(val) -> datetime:
    """Parse a value that might be a datetime or a string into a datetime."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        return datetime.fromisoformat(val)
    return val


def _group_consecutive(rows: list[dict], gap_minutes: float = 15.0) -> list[list[dict]]:
    """Group rows by sensor_id, then split into sub-groups where consecutive
    readings are within *gap_minutes* of each other.

    Each row dict must contain 'sensor_id' and 'reading_timestamp'.
    """
    if not rows:
        return []
    # Normalise timestamps to datetime objects
    for r in rows:
        r["reading_timestamp"] = _parse_dt(r["reading_timestamp"])
    # Sort by sensor, then timestamp
    rows.sort(key=lambda r: (r["sensor_id"], r["reading_timestamp"]))
    groups: list[list[dict]] = []
    current: list[dict] = []
    last_ts: Optional[datetime] = None
    last_sensor: Optional[int] = None
    for row in rows:
        ts = row["reading_timestamp"]
        sid = row["sensor_id"]
        if last_ts is None or sid != last_sensor:
            if current:
                groups.append(current)
            current = [row]
        else:
            delta = (ts - last_ts).total_seconds() / 60.0
            if delta <= gap_minutes + 1:  # allow 1 min tolerance
                current.append(row)
            else:
                groups.append(current)
                current = [row]
        last_ts = ts
        last_sensor = sid
    if current:
        groups.append(current)
    return groups


# ═══════════════════════════════════════════════════════════════════════════
#  Detectors
# ═══════════════════════════════════════════════════════════════════════════

def _detect_temperature_violations(db: Session, counter: dict) -> int:
    """Find temperature readings outside the zone's configured range."""
    sql = text("""
        SELECT sr.id, sr.sensor_id, sr.reading_timestamp, sr.temperature_c,
               s.zone_id, z.name as zone_name,
               z.min_temp_c, z.max_temp_c
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE sr.temperature_c IS NOT NULL
          AND sr.is_missing = 0
          AND (sr.temperature_c < z.min_temp_c OR sr.temperature_c > z.max_temp_c)
        ORDER BY s.zone_id, sr.reading_timestamp
    """)
    rows = [dict(r._mapping) for r in db.execute(sql)]

    groups = _group_consecutive(rows, gap_minutes=READING_INTERVAL_MIN)
    n = 0
    for grp in groups:
        first = grp[0]
        last = grp[-1]
        zone_id = first["zone_id"]
        temp_val = first["temperature_c"]
        mid = (first["min_temp_c"] + first["max_temp_c"]) / 2
        delta = abs(temp_val - mid)
        severity = "critical" if delta > TEMP_CRITICAL_DELTA else "warning"

        alarm_id = counter["alarm_id"]
        counter["alarm_id"] += 1
        alarm = Alarm(
            id=alarm_id,
            alarm_type="temperature_violation",
            severity=severity,
            zone_id=zone_id,
            sensor_id=first["sensor_id"],
            start_timestamp=first["reading_timestamp"],
            end_timestamp=last["reading_timestamp"],
            description=(f"Temperature {temp_val}°C in {first['zone_name']} "
                         f"exceeds allowed range "
                         f"[{first['min_temp_c']}, {first['max_temp_c']}]°C"),
            recommended_action="Verify HVAC system and relocate "
                               "temperature-sensitive inventory if excursion persists",
            status="active",
            source="detection",
        )
        db.add(alarm)
        db.flush()
        _link_inventory(db, alarm)
        n += 1
    return n


def _detect_humidity_violations(db: Session, counter: dict) -> int:
    """Find humidity readings outside the zone's configured range."""
    sql = text("""
        SELECT sr.id, sr.sensor_id, sr.reading_timestamp, sr.humidity_pct,
               s.zone_id, z.name as zone_name,
               z.min_humidity_pct, z.max_humidity_pct
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE sr.humidity_pct IS NOT NULL
          AND sr.is_missing = 0
          AND (sr.humidity_pct < z.min_humidity_pct
               OR sr.humidity_pct > z.max_humidity_pct)
        ORDER BY s.zone_id, sr.reading_timestamp
    """)
    rows = [dict(r._mapping) for r in db.execute(sql)]

    groups = _group_consecutive(rows, gap_minutes=READING_INTERVAL_MIN)
    n = 0
    for grp in groups:
        first = grp[0]
        last = grp[-1]
        zone_id = first["zone_id"]
        hum_val = first["humidity_pct"]
        mid = (first["min_humidity_pct"] + first["max_humidity_pct"]) / 2
        delta = abs(hum_val - mid)
        severity = "critical" if delta > HUM_CRITICAL_DELTA else "warning"

        alarm_id = counter["alarm_id"]
        counter["alarm_id"] += 1
        alarm = Alarm(
            id=alarm_id,
            alarm_type="humidity_violation",
            severity=severity,
            zone_id=zone_id,
            sensor_id=first["sensor_id"],
            start_timestamp=first["reading_timestamp"],
            end_timestamp=last["reading_timestamp"],
            description=(f"Humidity {hum_val}% in {first['zone_name']} "
                         f"exceeds allowed range "
                         f"[{first['min_humidity_pct']}, "
                         f"{first['max_humidity_pct']}]%"),
            recommended_action="Check dehumidifier/humidifier and monitor "
                                "humidity-sensitive products",
            status="active",
            source="detection",
        )
        db.add(alarm)
        db.flush()
        _link_inventory(db, alarm)
        n += 1
    return n


def _detect_prolonged_door_open(db: Session, counter: dict) -> int:
    """Find door events with duration above 30 minutes."""
    events = db.query(DoorEvent).filter(
        DoorEvent.duration_seconds.isnot(None),
        DoorEvent.duration_seconds > PROLONGED_DOOR_THRESHOLD_SEC,
    ).order_by(DoorEvent.zone_id, DoorEvent.event_timestamp).all()

    n = 0
    for evt in events:
        zone = db.query(Zone).filter(Zone.id == evt.zone_id).first()
        alarm_id = counter["alarm_id"]
        counter["alarm_id"] += 1
        minutes = evt.duration_seconds / 60.0
        alarm = Alarm(
            id=alarm_id,
            alarm_type="prolonged_door_open",
            severity="warning",
            zone_id=evt.zone_id,
            sensor_id=evt.sensor_id,
            start_timestamp=evt.event_timestamp,
            end_timestamp=evt.event_timestamp + timedelta(seconds=evt.duration_seconds),
            description=(f"Door open for {minutes:.0f} minutes in "
                         f"{zone.name if zone else evt.zone_id}"),
            recommended_action=("Verify door closure mechanism and inspect "
                                "for unauthorized access"),
            status="active",
            source="detection",
        )
        db.add(alarm)
        db.flush()
        _link_inventory(db, alarm)
        n += 1
    return n


def _detect_abnormal_occupancy(db: Session, counter: dict) -> int:
    """Find occupancy readings exceeding the zone's maximum."""
    sql = text("""
        SELECT sr.id, sr.sensor_id, sr.reading_timestamp, sr.occupancy_count,
               s.zone_id, z.name as zone_name, z.max_occupancy
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE sr.occupancy_count IS NOT NULL
          AND sr.is_missing = 0
          AND sr.occupancy_count > z.max_occupancy
        ORDER BY s.zone_id, sr.reading_timestamp
    """)
    rows = [dict(r._mapping) for r in db.execute(sql)]

    groups = _group_consecutive(rows, gap_minutes=READING_INTERVAL_MIN)
    n = 0
    for grp in groups:
        first = grp[0]
        last = grp[-1]
        alarm_id = counter["alarm_id"]
        counter["alarm_id"] += 1
        alarm = Alarm(
            id=alarm_id,
            alarm_type="abnormal_occupancy",
            severity="warning",
            zone_id=first["zone_id"],
            sensor_id=first["sensor_id"],
            start_timestamp=first["reading_timestamp"],
            end_timestamp=last["reading_timestamp"],
            description=(f"Occupancy {first['occupancy_count']} exceeds maximum "
                        f"{first['max_occupancy']} in {first['zone_name']}"),
            recommended_action=("Check for overcrowding and verify access "
                                "control"),
            status="active",
            source="detection",
        )
        db.add(alarm)
        db.flush()
        _link_inventory(db, alarm)
        n += 1
    return n


def _detect_missing_readings(db: Session, counter: dict) -> int:
    """Find readings flagged as missing (sensor outages).

    These must NOT be treated as normal — scenario #3.
    """
    sql = text("""
        SELECT sr.id, sr.sensor_id, sr.reading_timestamp, sr.is_missing,
               s.zone_id, z.name as zone_name, s.sensor_type
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE sr.is_missing = 1
        ORDER BY sr.sensor_id, sr.reading_timestamp
    """)
    rows = [dict(r._mapping) for r in db.execute(sql)]

    groups = _group_consecutive(rows, gap_minutes=READING_INTERVAL_MIN)
    n = 0
    for grp in groups:
        first = grp[0]
        last = grp[-1]
        sensor = db.query(Sensor).filter(Sensor.id == first["sensor_id"]).first()
        alarm_id = counter["alarm_id"]
        counter["alarm_id"] += 1
        duration_min = (last["reading_timestamp"] - first["reading_timestamp"]).total_seconds() / 60
        alarm = Alarm(
            id=alarm_id,
            alarm_type="sensor_outage",
            severity="warning",
            zone_id=first["zone_id"],
            sensor_id=first["sensor_id"],
            start_timestamp=first["reading_timestamp"],
            end_timestamp=last["reading_timestamp"],
            description=(f"Sensor {first['sensor_id']} ({first['sensor_type']}) "
                        f"missing readings for {duration_min:.0f} minutes in "
                        f"{first['zone_name']} ({len(grp)} readings missing)"),
            recommended_action=("Inspect sensor connectivity and schedule "
                                "maintenance"),
            status="active",
            source="detection",
        )
        db.add(alarm)
        db.flush()
        _link_inventory(db, alarm)
        n += 1

        # Update sensor status to offline
        if sensor:
            sensor.status = "offline"
    return n


def _detect_sensor_drift(db: Session, counter: dict) -> int:
    """Detect sensors where readings gradually drift from the baseline.

    Compares the mean of the first quartile of readings to the mean of the
    last quartile.  If the difference exceeds a threshold proportional to
    the zone's configured range, a drift alarm is raised.
    """
    # Get time range bounds
    min_ts = db.query(func.min(SensorReading.reading_timestamp)).scalar()
    max_ts = db.query(func.max(SensorReading.reading_timestamp)).scalar()
    if not min_ts or not max_ts:
        return 0
    span = (max_ts - min_ts).total_seconds()
    q1_end = min_ts + timedelta(seconds=span * 0.25)
    q4_start = min_ts + timedelta(seconds=span * 0.75)

    # Temperature drift
    sql_temp = text("""
        SELECT s.id as sensor_id, s.zone_id, z.name as zone_name,
               z.min_temp_c, z.max_temp_c,
               AVG(CASE WHEN sr.reading_timestamp < :q1_end THEN sr.temperature_c END) as q1_avg,
               AVG(CASE WHEN sr.reading_timestamp >= :q4_start THEN sr.temperature_c END) as q4_avg
        FROM sensors s
        JOIN sensor_readings sr ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE s.sensor_type = 'temperature'
          AND sr.temperature_c IS NOT NULL
          AND sr.is_missing = 0
        GROUP BY s.id, s.zone_id, z.name, z.min_temp_c, z.max_temp_c
    """)
    rows = [dict(r._mapping) for r in db.execute(sql_temp, {"q1_end": q1_end, "q4_start": q4_start})]
    n = _create_drift_alarms(db, counter, rows, "temperature")

    # Humidity drift
    sql_hum = text("""
        SELECT s.id as sensor_id, s.zone_id, z.name as zone_name,
               z.min_humidity_pct, z.max_humidity_pct,
               AVG(CASE WHEN sr.reading_timestamp < :q1_end THEN sr.humidity_pct END) as q1_avg,
               AVG(CASE WHEN sr.reading_timestamp >= :q4_start THEN sr.humidity_pct END) as q4_avg
        FROM sensors s
        JOIN sensor_readings sr ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE s.sensor_type = 'humidity'
          AND sr.humidity_pct IS NOT NULL
          AND sr.is_missing = 0
        GROUP BY s.id, s.zone_id, z.name, z.min_humidity_pct, z.max_humidity_pct
    """)
    rows = [dict(r._mapping) for r in db.execute(sql_hum, {"q1_end": q1_end, "q4_start": q4_start})]
    n += _create_drift_alarms(db, counter, rows, "humidity")

    return n


def _create_drift_alarms(db: Session, counter: dict, rows: list[dict],
                         sensor_type: str) -> int:
    n = 0
    for row in rows:
        q1 = row.get("q1_avg")
        q4 = row.get("q4_avg")
        if q1 is None or q4 is None:
            continue
        delta = abs(q4 - q1)
        if sensor_type == "temperature":
            zone_range = row["max_temp_c"] - row["min_temp_c"]
        else:
            zone_range = row["max_humidity_pct"] - row["min_humidity_pct"]
        threshold = zone_range * DRIFT_THRESHOLD_FACTOR
        if delta > threshold:
            sensor_id = row["sensor_id"]
            zone_id = row["zone_id"]
            alarm_id = counter["alarm_id"]
            counter["alarm_id"] += 1
            unit = "°C" if sensor_type == "temperature" else "%"
            alarm = Alarm(
                id=alarm_id,
                alarm_type="sensor_drift",
                severity="warning",
                zone_id=zone_id,
                sensor_id=sensor_id,
                start_timestamp=datetime(2026, 10, 1),
                end_timestamp=datetime(2026, 10, 22),
                description=(f"Sensor {sensor_id} ({sensor_type}) shows drift "
                             f"of {delta:.1f}{unit} from baseline in "
                             f"{row['zone_name']}"),
                recommended_action="Recalibrate or replace sensor",
                status="active",
                source="detection",
            )
            db.add(alarm)
            db.flush()
            _link_inventory(db, alarm)
            n += 1

            # Update sensor status
            sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()
            if sensor:
                sensor.status = "drift"
    return n


def _detect_incompatible_inventory(db: Session, counter: dict) -> int:
    """Detect inventory lots assigned to zones whose type is not compatible
    with the product's storage requirements — scenario #1."""
    lots = db.query(InventoryLot).all()
    requirements = {
        r.product_category: r for r in db.query(StorageRequirement).all()
    }
    zones = {z.id: z for z in db.query(Zone).all()}

    n = 0
    for lot in lots:
        req = requirements.get(lot.product_category)
        if not req:
            continue
        zone = zones.get(lot.zone_id)
        if not zone:
            continue
        if zone.zone_type not in req.compatible_zone_types:
            alarm_id = counter["alarm_id"]
            counter["alarm_id"] += 1
            alarm = Alarm(
                id=alarm_id,
                alarm_type="inventory_incompatible_zone",
                severity="critical",
                zone_id=zone.id,
                sensor_id=None,
                start_timestamp=lot.arrival_date,
                end_timestamp=lot.departure_date or datetime(2026, 12, 31, 23, 59, 59),
                description=(f"Inventory lot {lot.id} ({lot.product_name}, "
                             f"{lot.product_category}) assigned to "
                             f"incompatible zone {zone.name} "
                             f"(type {zone.zone_type}, requires "
                             f"{req.compatible_zone_types})"),
                recommended_action=("Relocate inventory to a compatible "
                                    "zone immediately"),
                status="active",
                source="detection",
            )
            db.add(alarm)
            db.flush()
            # Directly link the lot
            db.add(AlarmInventoryLot(
                alarm_id=alarm.id,
                inventory_lot_id=lot.id,
            ))
            n += 1
    return n


# ═══════════════════════════════════════════════════════════════════════════
#  Inspections & Remediations
# ═══════════════════════════════════════════════════════════════════════════

def _generate_inspections_and_remediations(db: Session) -> tuple[int, int]:
    """Create pending inspections for critical/warning alarms and pending
    remediations for critical alarms."""
    alarms = db.query(Alarm).filter(Alarm.source == "detection").all()
    max_insp = db.query(func.max(Inspection.id)).scalar() or 0
    max_rem = db.query(func.max(Remediation.id)).scalar() or 0
    insp_id = max_insp + 1
    rem_id = max_rem + 1
    n_insp = 0
    n_rem = 0
    rng = np.random.default_rng(42)

    for alarm in alarms:
        if alarm.severity in ("critical", "warning"):
            inspector = INSPECTORS[int(rng.integers(0, len(INSPECTORS)))]
            db.add(Inspection(
                id=insp_id,
                alarm_id=alarm.id,
                inspector_name=inspector,
                inspection_timestamp=alarm.start_timestamp + timedelta(hours=1),
                status="pending",
                findings=None,
                notes="Auto-generated pending inspection",
            ))
            n_insp += 1
            insp_id += 1

        if alarm.severity == "critical":
            remediator = REMEDIATORS[int(rng.integers(0, len(REMEDIATORS)))]
            action_map = {
                "temperature_violation": "adjust_temperature",
                "humidity_violation": "adjust_humidity",
                "inventory_incompatible_zone": "relocate_inventory",
                "sensor_outage": "replace_sensor",
                "sensor_drift": "recalibrate_sensor",
            }
            action_type = action_map.get(alarm.alarm_type, "manual_review")
            db.add(Remediation(
                id=rem_id,
                alarm_id=alarm.id,
                inspection_id=None,
                action_type=action_type,
                description=f"Auto-generated remediation for {alarm.alarm_type}",
                performed_by=remediator,
                performed_at=alarm.start_timestamp + timedelta(hours=2),
                status="pending",
            ))
            n_rem += 1
            rem_id += 1

    return n_insp, n_rem
