"""Automated data validation for WarehouseGuard AI.

Checks primary keys, foreign keys, duplicates, allowed values, date ordering,
lifecycle transitions, inventory relationships and the four required negative
scenarios.
"""
from __future__ import annotations

from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session


# Allowed values for enum-like columns
ALLOWED_VALUES = {
    "sensors.sensor_type": ["temperature", "humidity", "occupancy", "door"],
    "sensors.status": ["active", "drift", "offline"],
    "zones.zone_type": ["ambient", "cold_storage", "frozen", "hazardous"],
    "inventory_lots.status": ["stored", "departed", "expired"],
    "alarms.severity": ["critical", "warning", "info"],
    "alarms.status": ["active", "acknowledged", "resolved"],
    "alarms.source": ["preexisting", "detection"],
    "inspections.status": ["pending", "scheduled", "completed", "cancelled"],
    "remediations.status": ["pending", "in_progress", "completed"],
}

ALARM_TYPES = [
    "temperature_violation", "humidity_violation", "prolonged_door_open",
    "abnormal_occupancy", "sensor_outage", "sensor_drift",
    "inventory_incompatible_zone",
]


def run_validation(db: Session) -> dict:
    """Run all validation checks and return a structured report."""
    checks = []
    checks.extend(_check_primary_keys(db))
    checks.extend(_check_foreign_keys(db))
    checks.extend(_check_duplicates(db))
    checks.extend(_check_allowed_values(db))
    checks.extend(_check_date_ordering(db))
    checks.extend(_check_lifecycle_transitions(db))
    checks.extend(_check_inventory_relationships(db))
    checks.extend(_check_negative_scenarios(db))

    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    warnings = sum(1 for c in checks if c["status"] == "warning")

    return {
        "total_checks": len(checks),
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "checks": checks,
    }


def _ok(name: str, detail: str = "") -> dict:
    return {"check": name, "status": "pass", "detail": detail}


def _fail(name: str, detail: str) -> dict:
    return {"check": name, "status": "fail", "detail": detail}


def _warn(name: str, detail: str) -> dict:
    return {"check": name, "status": "warning", "detail": detail}


# ═══════════════════════════════════════════════════════════════════════════
#  Primary keys
# ═══════════════════════════════════════════════════════════════════════════

def _check_primary_keys(db: Session) -> list[dict]:
    results = []
    tables = ["warehouses", "zones", "sensors", "sensor_readings",
              "door_events", "inventory_lots", "storage_requirements",
              "alarms", "inspections", "remediations",
              "alarm_inventory_lots", "sensor_zone_mappings",
              "ground_truth_anomalies"]

    for t in tables:
        dup = db.execute(text(f"SELECT id, COUNT(*) c FROM {t} GROUP BY id HAVING c > 1")).fetchall()
        if dup:
            results.append(_fail(f"PK uniqueness: {t}",
                                 f"{len(dup)} duplicate IDs found: {[r[0] for r in dup[:5]]}"))
        else:
            results.append(_ok(f"PK uniqueness: {t}"))
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Foreign keys
# ═══════════════════════════════════════════════════════════════════════════

def _check_foreign_keys(db: Session) -> list[dict]:
    results = []
    fk_checks = [
        ("zones.warehouse_id → warehouses",
         "SELECT COUNT(*) FROM zones z LEFT JOIN warehouses w ON z.warehouse_id = w.id WHERE w.id IS NULL"),
        ("sensors.zone_id → zones",
         "SELECT COUNT(*) FROM sensors s LEFT JOIN zones z ON s.zone_id = z.id WHERE z.id IS NULL"),
        ("sensor_readings.sensor_id → sensors",
         "SELECT COUNT(*) FROM sensor_readings sr LEFT JOIN sensors s ON sr.sensor_id = s.id WHERE s.id IS NULL"),
        ("door_events.zone_id → zones",
         "SELECT COUNT(*) FROM door_events de LEFT JOIN zones z ON de.zone_id = z.id WHERE z.id IS NULL"),
        ("door_events.sensor_id → sensors",
         "SELECT COUNT(*) FROM door_events de LEFT JOIN sensors s ON de.sensor_id = s.id WHERE s.id IS NULL"),
        ("inventory_lots.zone_id → zones",
         "SELECT COUNT(*) FROM inventory_lots il LEFT JOIN zones z ON il.zone_id = z.id WHERE z.id IS NULL"),
        ("alarms.zone_id → zones",
         "SELECT COUNT(*) FROM alarms a LEFT JOIN zones z ON a.zone_id = z.id WHERE z.id IS NULL"),
        ("alarm_inventory_lots.alarm_id → alarms",
         "SELECT COUNT(*) FROM alarm_inventory_lots ail LEFT JOIN alarms a ON ail.alarm_id = a.id WHERE a.id IS NULL"),
        ("alarm_inventory_lots.inventory_lot_id → inventory_lots",
         "SELECT COUNT(*) FROM alarm_inventory_lots ail LEFT JOIN inventory_lots il ON ail.inventory_lot_id = il.id WHERE il.id IS NULL"),
        ("inspections.alarm_id → alarms",
         "SELECT COUNT(*) FROM inspections i LEFT JOIN alarms a ON i.alarm_id = a.id WHERE a.id IS NULL"),
        ("remediations.alarm_id → alarms",
         "SELECT COUNT(*) FROM remediations r LEFT JOIN alarms a ON r.alarm_id = a.id WHERE a.id IS NULL"),
        ("sensor_zone_mappings.sensor_id → sensors",
         "SELECT COUNT(*) FROM sensor_zone_mappings szm LEFT JOIN sensors s ON szm.sensor_id = s.id WHERE s.id IS NULL"),
        ("sensor_zone_mappings.zone_id → zones",
         "SELECT COUNT(*) FROM sensor_zone_mappings szm LEFT JOIN zones z ON szm.zone_id = z.id WHERE z.id IS NULL"),
    ]

    for name, sql in fk_checks:
        count = db.execute(text(sql)).scalar()
        if count:
            results.append(_fail(f"FK integrity: {name}", f"{count} orphaned rows"))
        else:
            results.append(_ok(f"FK integrity: {name}"))
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Duplicates
# ═══════════════════════════════════════════════════════════════════════════

def _check_duplicates(db: Session) -> list[dict]:
    results = []
    dup_checks = [
        ("storage_requirements.product_category",
         "SELECT product_category, COUNT(*) c FROM storage_requirements GROUP BY product_category HAVING c > 1"),
        ("sensor_readings (sensor_id, reading_timestamp)",
         "SELECT sensor_id, reading_timestamp, COUNT(*) c FROM sensor_readings GROUP BY sensor_id, reading_timestamp HAVING c > 1 LIMIT 5"),
        ("alarm_inventory_lots (alarm_id, inventory_lot_id)",
         "SELECT alarm_id, inventory_lot_id, COUNT(*) c FROM alarm_inventory_lots GROUP BY alarm_id, inventory_lot_id HAVING c > 1"),
    ]

    for name, sql in dup_checks:
        dup = db.execute(text(sql)).fetchall()
        if dup:
            results.append(_fail(f"Duplicate: {name}", f"{len(dup)} duplicates found"))
        else:
            results.append(_ok(f"Duplicate: {name}"))
    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Allowed values
# ═══════════════════════════════════════════════════════════════════════════

def _check_allowed_values(db: Session) -> list[dict]:
    results = []

    for col, allowed in ALLOWED_VALUES.items():
        table, column = col.split(".")
        placeholders = ", ".join(f"'{v}'" for v in allowed)
        sql = f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({placeholders})"
        count = db.execute(text(sql)).scalar()
        if count:
            results.append(_fail(f"Allowed values: {col}",
                                 f"{count} rows with invalid values (allowed: {allowed})"))
        else:
            results.append(_ok(f"Allowed values: {col}"))

    # Check alarm_type
    placeholders = ", ".join(f"'{v}'" for v in ALARM_TYPES)
    count = db.execute(text(
        f"SELECT COUNT(*) FROM alarms WHERE alarm_type NOT IN ({placeholders})"
    )).scalar()
    if count:
        results.append(_fail("Allowed values: alarms.alarm_type",
                             f"{count} rows with invalid alarm types"))
    else:
        results.append(_ok("Allowed values: alarms.alarm_type"))

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Date ordering
# ═══════════════════════════════════════════════════════════════════════════

def _check_date_ordering(db: Session) -> list[dict]:
    results = []

    # Sensor installed < calibrated
    count = db.execute(text(
        "SELECT COUNT(*) FROM sensors WHERE last_calibrated_at < installed_at"
    )).scalar()
    results.append(_ok("Date order: sensor calibrated after installed")
                   if count == 0
                   else _fail("Date order: sensor calibrated after installed",
                             f"{count} sensors calibrated before installation"))

    # Inventory arrival < departure
    count = db.execute(text(
        "SELECT COUNT(*) FROM inventory_lots WHERE departure_date IS NOT NULL AND departure_date < arrival_date"
    )).scalar()
    results.append(_ok("Date order: inventory departure after arrival")
                   if count == 0
                   else _fail("Date order: inventory departure after arrival",
                             f"{count} lots departed before arrival"))

    # Alarm start <= end
    count = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE end_timestamp IS NOT NULL AND end_timestamp < start_timestamp"
    )).scalar()
    results.append(_ok("Date order: alarm end after start")
                   if count == 0
                   else _fail("Date order: alarm end after start",
                             f"{count} alarms end before start"))

    # Alarm acknowledged_at >= start
    count = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE acknowledged_at IS NOT NULL AND acknowledged_at < start_timestamp"
    )).scalar()
    results.append(_ok("Date order: alarm acknowledged after start")
                   if count == 0
                   else _fail("Date order: alarm acknowledged after start",
                             f"{count} alarms acknowledged before start"))

    # Alarm resolved_at >= acknowledged_at
    count = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE resolved_at IS NOT NULL AND acknowledged_at IS NOT NULL AND resolved_at < acknowledged_at"
    )).scalar()
    results.append(_ok("Date order: alarm resolved after acknowledged")
                   if count == 0
                   else _fail("Date order: alarm resolved after acknowledged",
                             f"{count} alarms resolved before acknowledged"))

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Lifecycle transitions
# ═══════════════════════════════════════════════════════════════════════════

def _check_lifecycle_transitions(db: Session) -> list[dict]:
    results = []

    # If acknowledged_at is set, status should be acknowledged or resolved
    count = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE acknowledged_at IS NOT NULL AND status = 'active'"
    )).scalar()
    results.append(_ok("Lifecycle: acknowledged alarm not active")
                   if count == 0
                   else _fail("Lifecycle: acknowledged alarm not active",
                             f"{count} active alarms have acknowledged_at set"))

    # If resolved_at is set, status should be resolved
    count = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE resolved_at IS NOT NULL AND status != 'resolved'"
    )).scalar()
    results.append(_ok("Lifecycle: resolved alarm status correct")
                   if count == 0
                   else _fail("Lifecycle: resolved alarm status correct",
                             f"{count} non-resolved alarms have resolved_at set"))

    # Inspection lifecycle: completed inspections should have findings
    count = db.execute(text(
        "SELECT COUNT(*) FROM inspections WHERE status = 'completed' AND findings IS NULL"
    )).scalar()
    results.append(_warn("Lifecycle: completed inspection without findings",
                         f"{count} completed inspections missing findings")
                   if count > 0
                   else _ok("Lifecycle: completed inspection has findings"))

    # Remediation lifecycle: completed remediations should exist for critical alarms
    count = db.execute(text("""
        SELECT COUNT(DISTINCT a.id) FROM alarms a
        WHERE a.severity = 'critical' AND a.source = 'detection'
          AND NOT EXISTS (SELECT 1 FROM remediations r WHERE r.alarm_id = a.id)
    """)).scalar()
    results.append(_warn("Lifecycle: critical alarm without remediation",
                         f"{count} critical alarms without remediation")
                   if count > 0
                   else _ok("Lifecycle: critical alarm has remediation"))

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Inventory relationships
# ═══════════════════════════════════════════════════════════════════════════

def _check_inventory_relationships(db: Session) -> list[dict]:
    results = []

    # Alarms with affected zone should link to inventory if lots exist
    unlinked = db.execute(text("""
        SELECT a.id, a.zone_id, a.alarm_type
        FROM alarms a
        WHERE a.alarm_type IN
              ('temperature_violation', 'humidity_violation',
               'prolonged_door_open', 'abnormal_occupancy', 'sensor_outage')
          AND NOT EXISTS (
            SELECT 1 FROM alarm_inventory_lots ail WHERE ail.alarm_id = a.id
          )
          AND EXISTS (
            SELECT 1 FROM inventory_lots il
            WHERE il.zone_id = a.zone_id
              AND il.arrival_date <= COALESCE(a.end_timestamp, '2026-12-31')
              AND (il.departure_date IS NULL OR il.departure_date >= a.start_timestamp)
          )
        LIMIT 50
    """)).fetchall()

    if unlinked:
        results.append(_fail(
            "Inventory: alarms without inventory linkage",
            f"{len(unlinked)} alarms have inventory in their zone/time window but "
            f"no AlarmInventoryLot entries. IDs: {[r[0] for r in unlinked[:5]]}"
        ))
    else:
        results.append(_ok("Inventory: alarms with inventory linkage"))

    # Check storage requirement compatibility
    incompatible = db.execute(text("""
        SELECT il.id, il.product_category, z.zone_type, sr.compatible_zone_types
        FROM inventory_lots il
        JOIN zones z ON il.zone_id = z.id
        JOIN storage_requirements sr ON il.product_category = sr.product_category
        WHERE z.zone_type NOT IN (
            SELECT value FROM json_each(sr.compatible_zone_types)
        )
        LIMIT 50
    """)).fetchall()

    if incompatible:
        results.append(_fail(
            "Inventory: incompatible zone assignment",
            f"{len(incompatible)} inventory lots in incompatible zones. "
            f"Lot IDs: {[r[0] for r in incompatible[:5]]}"
        ))
    else:
        results.append(_ok("Inventory: compatible zone assignment"))

    return results


# ═══════════════════════════════════════════════════════════════════════════
#  Negative scenarios
# ═══════════════════════════════════════════════════════════════════════════

def _check_negative_scenarios(db: Session) -> list[dict]:
    results = []

    # Scenario #1: Inventory lot assigned to incompatible zone
    count1 = db.execute(text("""
        SELECT COUNT(*) FROM inventory_lots il
        JOIN zones z ON il.zone_id = z.id
        JOIN storage_requirements sr ON il.product_category = sr.product_category
        WHERE z.zone_type NOT IN (
            SELECT value FROM json_each(sr.compatible_zone_types)
        )
    """)).scalar()
    if count1:
        results.append(_fail(
            "Negative #1: Inventory in incompatible zone",
            f"{count1} inventory lots assigned to incompatible zones detected"
        ))
    else:
        results.append(_ok("Negative #1: No incompatible inventory"))

    # Scenario #2: Sensor mapped to multiple zones without justification
    count2 = db.execute(text("""
        SELECT COUNT(DISTINCT sensor_id) FROM sensor_zone_mappings
        WHERE justification IS NULL AND is_primary = 0
    """)).scalar()
    # Count sensors with >1 mapping
    multi_count = db.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT sensor_id FROM sensor_zone_mappings
            GROUP BY sensor_id HAVING COUNT(*) > 1
        )
    """)).scalar()
    if count2:
        results.append(_fail(
            "Negative #2: Sensor mapped to multiple zones without justification",
            f"{count2} secondary sensor-zone mappings without justification "
            f"({multi_count} sensors have multiple zone mappings)"
        ))
    else:
        results.append(_ok("Negative #2: All multi-zone sensors have justification"))

    # Scenario #3: Missing readings detected (not treated as normal)
    missing_count = db.execute(text(
        "SELECT COUNT(*) FROM sensor_readings WHERE is_missing = 1"
    )).scalar()
    missing_alarms = db.execute(text(
        "SELECT COUNT(*) FROM alarms WHERE alarm_type = 'sensor_outage'"
    )).scalar()
    if missing_count > 0 and missing_alarms > 0:
        results.append(_ok(
            "Negative #3: Missing readings detected as anomalies",
            f"{missing_count} missing readings, {missing_alarms} sensor_outage alarms generated"
        ))
    elif missing_count > 0 and missing_alarms == 0:
        results.append(_fail(
            "Negative #3: Missing readings NOT detected",
            f"{missing_count} missing readings but 0 sensor_outage alarms — "
            f"missing readings treated as normal (BUG)"
        ))
    else:
        results.append(_ok("Negative #3: No missing readings"))

    # Scenario #4: Alarms not linked to affected inventory
    unlinked_count = db.execute(text("""
        SELECT COUNT(*) FROM alarms a
        WHERE a.alarm_type IN
              ('temperature_violation', 'humidity_violation',
               'prolonged_door_open', 'abnormal_occupancy', 'sensor_outage')
          AND NOT EXISTS (
            SELECT 1 FROM alarm_inventory_lots ail WHERE ail.alarm_id = a.id
          )
          AND EXISTS (
            SELECT 1 FROM inventory_lots il
            WHERE il.zone_id = a.zone_id
              AND il.arrival_date <= COALESCE(a.end_timestamp, '2026-12-31')
              AND (il.departure_date IS NULL OR il.departure_date >= a.start_timestamp)
          )
    """)).scalar()
    if unlinked_count:
        results.append(_fail(
            "Negative #4: Alarms without inventory linkage",
            f"{unlinked_count} alarms have affected inventory in their zone "
            f"but no AlarmInventoryLot entries"
        ))
    else:
        results.append(_ok("Negative #4: All alarms properly linked to inventory"))

    return results
