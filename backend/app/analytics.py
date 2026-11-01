"""Analytics and KPI calculations for WarehouseGuard AI."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models import (
    Alarm, SensorReading, Sensor, Zone, InventoryLot,
    AlarmInventoryLot, Inspection, Remediation, GroundTruthAnomaly,
    DoorEvent, StorageRequirement, SensorZoneMapping, Warehouse,
)


# ═══════════════════════════════════════════════════════════════════════════
#  KPI Summary
# ═══════════════════════════════════════════════════════════════════════════

def get_kpi_summary(db: Session) -> dict:
    """Calculate all executive KPIs in a single pass."""
    total_wh = db.query(func.count(Warehouse.id)).scalar() or 0
    total_zones = db.query(func.count(Zone.id)).scalar() or 0
    total_sensors = db.query(func.count(Sensor.id)).scalar() or 0
    total_readings = db.query(func.count(SensorReading.id)).scalar() or 0
    total_inventory = db.query(func.count(InventoryLot.id)).scalar() or 0
    total_alarms = db.query(func.count(Alarm.id)).scalar() or 0
    active_alarms = db.query(func.count(Alarm.id)).filter(Alarm.status == "active").scalar() or 0
    critical_alarms = db.query(func.count(Alarm.id)).filter(
        Alarm.severity == "critical", Alarm.status == "active").scalar() or 0
    acknowledged = db.query(func.count(Alarm.id)).filter(Alarm.status == "acknowledged").scalar() or 0
    resolved = db.query(func.count(Alarm.id)).filter(Alarm.status == "resolved").scalar() or 0

    # Environmental compliance rate
    total_env_readings = db.query(func.count(SensorReading.id)).filter(
        SensorReading.is_missing == False,
        (SensorReading.temperature_c.isnot(None)) | (SensorReading.humidity_pct.isnot(None))
    ).scalar() or 0

    violating_sql = text("""
        SELECT COUNT(*) FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        JOIN zones z ON s.zone_id = z.id
        WHERE sr.is_missing = 0
          AND (
            (sr.temperature_c IS NOT NULL AND
             (sr.temperature_c < z.min_temp_c OR sr.temperature_c > z.max_temp_c))
            OR
            (sr.humidity_pct IS NOT NULL AND
             (sr.humidity_pct < z.min_humidity_pct OR sr.humidity_pct > z.max_humidity_pct))
          )
    """)
    violating = db.execute(violating_sql).scalar() or 0
    compliance_rate = ((total_env_readings - violating) / total_env_readings * 100) if total_env_readings > 0 else 100.0

    # Sensor availability
    missing = db.query(func.count(SensorReading.id)).filter(SensorReading.is_missing == True).scalar() or 0
    availability = ((total_readings - missing) / total_readings * 100) if total_readings > 0 else 100.0
    missing_pct = (missing / total_readings * 100) if total_readings > 0 else 0.0

    # Affected inventory
    affected_inv = db.query(func.count(func.distinct(AlarmInventoryLot.inventory_lot_id))).scalar() or 0

    # Open inspections and remediations
    open_insp = db.query(func.count(Inspection.id)).filter(
        Inspection.status.in_(["pending", "scheduled"])).scalar() or 0
    open_rem = db.query(func.count(Remediation.id)).filter(
        Remediation.status.in_(["pending", "in_progress"])).scalar() or 0

    # MTTA / MTTR
    mtta_sql = text("""
        SELECT AVG((julianday(acknowledged_at) - julianday(created_at)) * 24)
        FROM alarms WHERE acknowledged_at IS NOT NULL
    """)
    mtta = db.execute(mtta_sql).scalar()
    mttr_sql = text("""
        SELECT AVG((julianday(resolved_at) - julianday(created_at)) * 24)
        FROM alarms WHERE resolved_at IS NOT NULL
    """)
    mttr = db.execute(mttr_sql).scalar()

    return {
        "total_warehouses": total_wh,
        "total_zones": total_zones,
        "total_sensors": total_sensors,
        "total_readings": total_readings,
        "total_inventory_lots": total_inventory,
        "total_alarms": total_alarms,
        "active_alarms": active_alarms,
        "critical_alarms": critical_alarms,
        "acknowledged_alarms": acknowledged,
        "resolved_alarms": resolved,
        "environmental_compliance_rate": round(compliance_rate, 2),
        "sensor_availability": round(availability, 2),
        "missing_reading_pct": round(missing_pct, 2),
        "affected_inventory_lots": affected_inv,
        "open_inspections": open_insp,
        "open_remediations": open_rem,
        "mean_time_to_acknowledge_hours": round(mtta, 2) if mtta else None,
        "mean_time_to_resolve_hours": round(mttr, 2) if mttr else None,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Trend data
# ═══════════════════════════════════════════════════════════════════════════

def get_temperature_trend(db: Session, zone_id: Optional[int] = None,
                          hours: int = 24) -> list[dict]:
    """Hourly average temperature with min/max band."""
    where = ["sr.temperature_c IS NOT NULL", "sr.is_missing = 0"]
    params: dict = {}
    if zone_id:
        where.append("s.zone_id = :zone_id")
        params["zone_id"] = zone_id

    sql = text(f"""
        SELECT strftime('%Y-%m-%d %H:00', sr.reading_timestamp) as hour,
               ROUND(AVG(sr.temperature_c), 2) as avg_temp,
               ROUND(MIN(sr.temperature_c), 2) as min_temp,
               ROUND(MAX(sr.temperature_c), 2) as max_temp,
               COUNT(*) as reading_count
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE {' AND '.join(where)}
        GROUP BY hour
        ORDER BY hour
        LIMIT :limit
    """)
    params["limit"] = hours
    rows = db.execute(sql, params).fetchall()
    return [{"timestamp": r[0], "avg": r[1], "min": r[2], "max": r[3], "count": r[4]}
            for r in rows]


def get_humidity_trend(db: Session, zone_id: Optional[int] = None,
                       hours: int = 24) -> list[dict]:
    """Hourly average humidity with min/max band."""
    where = ["sr.humidity_pct IS NOT NULL", "sr.is_missing = 0"]
    params: dict = {}
    if zone_id:
        where.append("s.zone_id = :zone_id")
        params["zone_id"] = zone_id

    sql = text(f"""
        SELECT strftime('%Y-%m-%d %H:00', sr.reading_timestamp) as hour,
               ROUND(AVG(sr.humidity_pct), 2) as avg_hum,
               ROUND(MIN(sr.humidity_pct), 2) as min_hum,
               ROUND(MAX(sr.humidity_pct), 2) as max_hum,
               COUNT(*) as reading_count
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE {' AND '.join(where)}
        GROUP BY hour
        ORDER BY hour
        LIMIT :limit
    """)
    params["limit"] = hours
    rows = db.execute(sql, params).fetchall()
    return [{"timestamp": r[0], "avg": r[1], "min": r[2], "max": r[3], "count": r[4]}
            for r in rows]


def get_occupancy_trend(db: Session, zone_id: Optional[int] = None,
                        hours: int = 24) -> list[dict]:
    """Hourly average occupancy."""
    where = ["sr.occupancy_count IS NOT NULL", "sr.is_missing = 0"]
    params: dict = {}
    if zone_id:
        where.append("s.zone_id = :zone_id")
        params["zone_id"] = zone_id

    sql = text(f"""
        SELECT strftime('%Y-%m-%d %H:00', sr.reading_timestamp) as hour,
               ROUND(AVG(sr.occupancy_count), 1) as avg_occ,
               MAX(sr.occupancy_count) as max_occ,
               COUNT(*) as reading_count
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE {' AND '.join(where)}
        GROUP BY hour
        ORDER BY hour
        LIMIT :limit
    """)
    params["limit"] = hours
    rows = db.execute(sql, params).fetchall()
    return [{"timestamp": r[0], "avg": r[1], "max": r[2], "count": r[3]}
            for r in rows]


def get_door_event_stats(db: Session, zone_id: Optional[int] = None) -> dict:
    """Door event statistics."""
    query = db.query(DoorEvent)
    if zone_id:
        query = query.filter(DoorEvent.zone_id == zone_id)

    total = query.count()
    prolonged = query.filter(DoorEvent.duration_seconds > 1800).count()
    avg_duration = db.query(func.avg(DoorEvent.duration_seconds)).filter(
        DoorEvent.duration_seconds.isnot(None)).scalar()

    # Door events by hour of day
    sql = text("""
        SELECT strftime('%H', event_timestamp) as hour, COUNT(*) as count,
               ROUND(AVG(duration_seconds), 1) as avg_duration
        FROM door_events
        GROUP BY hour
        ORDER BY hour
    """)
    hourly = db.execute(sql).fetchall()

    return {
        "total_events": total,
        "prolonged_events": prolonged,
        "avg_duration_seconds": round(avg_duration, 1) if avg_duration else 0,
        "hourly": [{"hour": r[0], "count": r[1], "avg_duration": r[2]}
                   for r in hourly],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Alert metrics (precision / recall / F1)
# ═══════════════════════════════════════════════════════════════════════════

def get_alert_metrics(db: Session) -> dict:
    """Calculate precision, recall and F1-score of detection against ground
    truth.

    Matching strategy: for each ground-truth anomaly (excluding
    alarm_missing_inventory_link which is a validation issue), determine its
    zone_id and timestamp, then check whether a detection-sourced alarm
    exists for the same zone and alarm_type with an overlapping time window.
    """
    # Load ground truth (exclude validation-only anomalies)
    gt_rows = db.execute(text("""
        SELECT gt.id, gt.anomaly_type, gt.entity_type, gt.entity_id,
          CASE
            WHEN gt.entity_type = 'sensor_reading'
              THEN (SELECT s.zone_id FROM sensor_readings sr
                    JOIN sensors s ON sr.sensor_id = s.id
                    WHERE sr.id = gt.entity_id)
            WHEN gt.entity_type = 'door_event'
              THEN (SELECT zone_id FROM door_events WHERE id = gt.entity_id)
            WHEN gt.entity_type = 'inventory_lot'
              THEN (SELECT zone_id FROM inventory_lots WHERE id = gt.entity_id)
            WHEN gt.entity_type = 'alarm'
              THEN (SELECT zone_id FROM alarms WHERE id = gt.entity_id)
          END as zone_id,
          CASE
            WHEN gt.entity_type = 'sensor_reading'
              THEN (SELECT reading_timestamp FROM sensor_readings WHERE id = gt.entity_id)
            WHEN gt.entity_type = 'door_event'
              THEN (SELECT event_timestamp FROM door_events WHERE id = gt.entity_id)
            WHEN gt.entity_type = 'inventory_lot'
              THEN (SELECT arrival_date FROM inventory_lots WHERE id = gt.entity_id)
            WHEN gt.entity_type = 'alarm'
              THEN (SELECT start_timestamp FROM alarms WHERE id = gt.entity_id)
          END as event_ts
        FROM ground_truth_anomalies gt
        WHERE gt.anomaly_type != 'alarm_missing_inventory_link'
    """)).fetchall()

    # Load detection alarms
    det_alarms = db.execute(text("""
        SELECT id, alarm_type, zone_id, start_timestamp, end_timestamp
        FROM alarms WHERE source = 'detection'
    """)).fetchall()

    # Match
    tp = 0
    matched_alarm_ids: set[int] = set()

    for gt in gt_rows:
        gt_zone = gt[4]
        gt_ts = gt[5]
        gt_type = gt[1]
        if gt_zone is None or gt_ts is None:
            continue

        for alarm in det_alarms:
            a_id, a_type, a_zone, a_start, a_end = alarm
            if a_id in matched_alarm_ids:
                continue
            if a_type != gt_type:
                continue
            if a_zone != gt_zone:
                continue
            a_end_val = a_end or datetime(2026, 12, 31, 23, 59, 59)
            # Check time overlap
            if a_start <= gt_ts <= a_end_val:
                tp += 1
                matched_alarm_ids.add(a_id)
                break

    total_gt = len(gt_rows)
    total_detected = len(det_alarms)
    fp = total_detected - len(matched_alarm_ids)
    fn = total_gt - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "total_ground_truth": total_gt,
        "total_detected": total_detected,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Additional dashboard analytics
# ═══════════════════════════════════════════════════════════════════════════

def get_alarm_distribution(db: Session) -> dict:
    """Alarm counts grouped by type and severity."""
    by_type = db.execute(text("""
        SELECT alarm_type, COUNT(*) as count
        FROM alarms GROUP BY alarm_type ORDER BY count DESC
    """)).fetchall()

    by_severity = db.execute(text("""
        SELECT severity, COUNT(*) as count
        FROM alarms GROUP BY severity ORDER BY count DESC
    """)).fetchall()

    by_status = db.execute(text("""
        SELECT status, COUNT(*) as count
        FROM alarms GROUP BY status
    """)).fetchall()

    return {
        "by_type": [{"type": r[0], "count": r[1]} for r in by_type],
        "by_severity": [{"severity": r[0], "count": r[1]} for r in by_severity],
        "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
    }


def get_sensor_health(db: Session) -> dict:
    """Sensor health summary."""
    by_status = db.execute(text("""
        SELECT status, COUNT(*) as count
        FROM sensors GROUP BY status
    """)).fetchall()

    by_type = db.execute(text("""
        SELECT sensor_type, status, COUNT(*) as count
        FROM sensors GROUP BY sensor_type, status
        ORDER BY sensor_type, status
    """)).fetchall()

    # Sensor availability per sensor
    availability = db.execute(text("""
        SELECT s.id, s.sensor_type, s.status,
               COUNT(sr.id) as total,
               SUM(CASE WHEN sr.is_missing = 1 THEN 1 ELSE 0 END) as missing,
               ROUND(100.0 * SUM(CASE WHEN sr.is_missing = 0 THEN 1 ELSE 0 END) / COUNT(sr.id), 2) as availability
        FROM sensors s
        LEFT JOIN sensor_readings sr ON sr.sensor_id = s.id
        GROUP BY s.id
        ORDER BY availability ASC
        LIMIT 20
    """)).fetchall()

    return {
        "by_status": [{"status": r[0], "count": r[1]} for r in by_status],
        "by_type_status": [{"sensor_type": r[0], "status": r[1], "count": r[2]}
                           for r in by_type],
        "lowest_availability": [
            {"sensor_id": r[0], "sensor_type": r[1], "status": r[2],
             "total_readings": r[3], "missing": r[4], "availability": r[5]}
            for r in availability
        ],
    }


def get_inventory_impact(db: Session) -> dict:
    """Inventory impact analysis."""
    # Affected lots by alarm type
    by_alarm_type = db.execute(text("""
        SELECT a.alarm_type, COUNT(DISTINCT ail.inventory_lot_id) as lot_count
        FROM alarm_inventory_lots ail
        JOIN alarms a ON ail.alarm_id = a.id
        GROUP BY a.alarm_type
        ORDER BY lot_count DESC
    """)).fetchall()

    # Affected lots by severity
    by_severity = db.execute(text("""
        SELECT a.severity, COUNT(DISTINCT ail.inventory_lot_id) as lot_count
        FROM alarm_inventory_lots ail
        JOIN alarms a ON ail.alarm_id = a.id
        GROUP BY a.severity
    """)).fetchall()

    # Top affected products
    by_product = db.execute(text("""
        SELECT il.product_category, il.product_name,
               COUNT(DISTINCT ail.alarm_id) as alarm_count
        FROM alarm_inventory_lots ail
        JOIN inventory_lots il ON ail.inventory_lot_id = il.id
        GROUP BY il.product_category, il.product_name
        ORDER BY alarm_count DESC
        LIMIT 10
    """)).fetchall()

    # Zones with most affected inventory
    by_zone = db.execute(text("""
        SELECT z.name, z.zone_type, COUNT(DISTINCT ail.inventory_lot_id) as lot_count
        FROM alarm_inventory_lots ail
        JOIN alarms a ON ail.alarm_id = a.id
        JOIN zones z ON a.zone_id = z.id
        GROUP BY z.name, z.zone_type
        ORDER BY lot_count DESC
        LIMIT 10
    """)).fetchall()

    return {
        "by_alarm_type": [{"alarm_type": r[0], "lot_count": r[1]} for r in by_alarm_type],
        "by_severity": [{"severity": r[0], "lot_count": r[1]} for r in by_severity],
        "top_products": [{"product_category": r[0], "product_name": r[1],
                          "alarm_count": r[2]} for r in by_product],
        "top_zones": [{"zone_name": r[0], "zone_type": r[1],
                       "lot_count": r[2]} for r in by_zone],
    }


def get_compliance_by_zone(db: Session) -> list[dict]:
    """Environmental compliance rate per zone."""
    rows = db.execute(text("""
        SELECT z.id, z.name, z.zone_type,
               COUNT(sr.id) as total,
               SUM(CASE
                    WHEN sr.temperature_c IS NOT NULL AND
                         (sr.temperature_c < z.min_temp_c OR sr.temperature_c > z.max_temp_c)
                    THEN 1
                    WHEN sr.humidity_pct IS NOT NULL AND
                         (sr.humidity_pct < z.min_humidity_pct OR sr.humidity_pct > z.max_humidity_pct)
                    THEN 1
                    ELSE 0
                   END) as violations
        FROM zones z
        JOIN sensors s ON s.zone_id = z.id
        JOIN sensor_readings sr ON sr.sensor_id = s.id
        WHERE sr.is_missing = 0
        GROUP BY z.id, z.name, z.zone_type
        ORDER BY violations DESC
    """)).fetchall()

    return [
        {"zone_id": r[0], "zone_name": r[1], "zone_type": r[2],
         "total_readings": r[3], "violations": r[4],
         "compliance_rate": round((r[3] - r[4]) / r[3] * 100, 2) if r[3] > 0 else 100.0}
        for r in rows
    ]


def get_zone_summary(db: Session, zone_id: int) -> dict:
    """Detailed metrics for a single zone."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        return {}

    sensor_count = db.query(func.count(Sensor.id)).filter(Sensor.zone_id == zone_id).scalar() or 0
    inventory_count = db.query(func.count(InventoryLot.id)).filter(InventoryLot.zone_id == zone_id).scalar() or 0
    alarm_count = db.query(func.count(Alarm.id)).filter(Alarm.zone_id == zone_id).scalar() or 0
    active_alarm_count = db.query(func.count(Alarm.id)).filter(
        Alarm.zone_id == zone_id, Alarm.status == "active").scalar() or 0

    readings_sql = text("""
        SELECT COUNT(*),
               SUM(CASE WHEN is_missing = 1 THEN 1 ELSE 0 END),
               MIN(reading_timestamp), MAX(reading_timestamp)
        FROM sensor_readings sr
        JOIN sensors s ON sr.sensor_id = s.id
        WHERE s.zone_id = :zone_id
    """)
    r = db.execute(readings_sql, {"zone_id": zone_id}).fetchone()

    return {
        "zone_id": zone.id,
        "zone_name": zone.name,
        "zone_type": zone.zone_type,
        "warehouse_id": zone.warehouse_id,
        "sensor_count": sensor_count,
        "inventory_count": inventory_count,
        "alarm_count": alarm_count,
        "active_alarm_count": active_alarm_count,
        "total_readings": r[0] if r else 0,
        "missing_readings": r[1] if r else 0,
        "first_reading": str(r[2]) if r and r[2] else None,
        "last_reading": str(r[3]) if r and r[3] else None,
    }
