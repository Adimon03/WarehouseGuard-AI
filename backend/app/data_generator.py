"""Synthetic data generator for WarehouseGuard AI.

Uses a fixed seed (20261022) for full reproducibility.  Generates warehouses,
zones, sensors, readings (1M in full mode), door events, inventory lots and
storage requirements with proper referential integrity.

Anomalies are injected during generation and recorded in the ground-truth
table so that detection precision/recall can be evaluated afterwards.
"""
from __future__ import annotations

import json
import math
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models import (
    Warehouse, Zone, Sensor, SensorZoneMapping, SensorReading, DoorEvent,
    StorageRequirement, InventoryLot, Alarm, AlarmInventoryLot,
    Inspection, Remediation, GroundTruthAnomaly,
)

SEED = 20261022

# ── Dataset configurations ──────────────────────────────────────────────────

FULL_CONFIG = {
    "n_warehouses": 10,
    "n_zones_per_wh": 10,
    "n_sensors_per_zone": 5,       # → 500 sensors total
    "n_readings_per_sensor": 2000, # → 1 000 000 readings
    "n_inventory_lots": 10_000,
}

STARTER_CONFIG = {
    "n_warehouses": 3,
    "n_zones_per_wh": 5,
    "n_sensors_per_zone": 3,
    "n_readings_per_sensor": 400,
    "n_inventory_lots": 500,
}

# Sensor type cycle per zone (order matters for deterministic generation).
# Door and humidity placed early so they appear even in starter (3-sensor) mode.
SENSOR_TYPES = ["temperature", "humidity", "door", "occupancy", "temperature"]

# Zone type baseline conditions
ZONE_TYPES = ["ambient", "cold_storage", "frozen", "hazardous"]

ZONE_CONDITIONS = {
    "ambient":      {"min_temp": 18,  "max_temp": 24,  "min_hum": 35, "max_hum": 55},
    "cold_storage": {"min_temp": 2,   "max_temp": 8,   "min_hum": 40, "max_hum": 60},
    "frozen":       {"min_temp": -25, "max_temp": -18, "min_hum": 30, "max_hum": 50},
    "hazardous":    {"min_temp": 15,  "max_temp": 25,  "min_hum": 30, "max_hum": 45},
}

WAREHOUSE_NAMES = [
    "Northgate Distribution Centre", "Southfield Logistics Hub", "Eastport Storage Facility",
    "Westend Cargo Terminal", "Central Valley Depot", "Harbourside Warehouse",
    "Mountain Ridge Distribution", "Riverside Storage Complex", "Lakeside Fulfilment Centre",
    "Summit Logistics Park", "Pioneer Storage Depot", "Frontier Cargo Hub",
    "Heritage Distribution Site", "Apex Logistics Terminal", "Meridian Warehouse",
]

WAREHOUSE_LOCATIONS = [
    "Manchester, UK", "Birmingham, UK", "Leeds, UK", "Bristol, UK", "Liverpool, UK",
    "Newcastle, UK", "Sheffield, UK", "Glasgow, UK", "Cardiff, UK", "Belfast, UK",
    "Southampton, UK", "Coventry, UK", "Nottingham, UK", "Aberdeen, UK", "Plymouth, UK",
]

MANAGERS = [
    "James Carter", "Sarah Mitchell", "David Thompson", "Emma Wilson", "Michael Brown",
    "Jessica Davies", "Thomas Wright", "Rachel Evans", "Christopher Hall", "Olivia Roberts",
    "Daniel Hughes", "Sophie Clarke", "Andrew Walker", "Hannah Phillips", "Matthew Stewart",
]

SENSOR_MANUFACTURERS = ["Sensitech", "Testo", "Honeywell", "Vaisala", "Omron", "Emerson"]
SENSOR_MODELS = ["SM-100", "TH-200", "OC-300", "DR-400", "THX-500", "OMN-600"]

PRODUCT_CATALOG = {
    "Pharmaceuticals": {
        "products": ["Insulin Vials", "Antibiotic Tablets", "Vaccine Doses", "Pain Relief Capsules", "Blood Plasma"],
        "min_temp": 2, "max_temp": 8, "min_hum": 30, "max_hum": 60,
        "dwell_limit": 365, "zone_types": ["cold_storage"],
    },
    "Frozen Foods": {
        "products": ["Frozen Vegetables", "Ice Cream Tub", "Frozen Pizza", "Frozen Berries", "Frozen Fish Fillets"],
        "min_temp": -25, "max_temp": -18, "min_hum": 30, "max_hum": 50,
        "dwell_limit": 180, "zone_types": ["frozen"],
    },
    "Electronics": {
        "products": ["Laptop Batteries", "Circuit Boards", "USB Cables", "LED Displays", "Power Adapters"],
        "min_temp": 15, "max_temp": 25, "min_hum": 30, "max_hum": 50,
        "dwell_limit": 90, "zone_types": ["ambient"],
    },
    "Chemicals": {
        "products": ["Cleaning Solvent", "Industrial Lubricant", "Paint Thinner", "Adhesive Resin", "Degreaser"],
        "min_temp": 15, "max_temp": 25, "min_hum": 30, "max_hum": 45,
        "dwell_limit": 365, "zone_types": ["hazardous"],
    },
    "Dry Goods": {
        "products": ["Cereal Boxes", "Rice Sacks", "Pasta Cartons", "Flour Bags", "Coffee Beans"],
        "min_temp": 18, "max_temp": 24, "min_hum": 35, "max_hum": 55,
        "dwell_limit": 120, "zone_types": ["ambient"],
    },
    "Beverages": {
        "products": ["Water Bottles", "Soda Cans", "Juice Cartons", "Energy Drinks", "Tea Boxes"],
        "min_temp": 15, "max_temp": 22, "min_hum": 35, "max_hum": 50,
        "dwell_limit": 90, "zone_types": ["ambient"],
    },
    "Fresh Produce": {
        "products": ["Organic Apples", "Fresh Spinach", "Green Grapes", "Cherry Tomatoes", "Romaine Lettuce"],
        "min_temp": 2, "max_temp": 8, "min_hum": 40, "max_hum": 70,
        "dwell_limit": 14, "zone_types": ["cold_storage"],
    },
    "Dairy": {
        "products": ["Milk Gallons", "Cheddar Cheese", "Greek Yogurt", "Butter Blocks", "Cream Cheese"],
        "min_temp": 2, "max_temp": 6, "min_hum": 40, "max_hum": 60,
        "dwell_limit": 21, "zone_types": ["cold_storage"],
    },
    "Industrial Parts": {
        "products": ["Steel Bearings", "Copper Wire Spools", "Aluminium Plates", "Rubber Gaskets", "Brass Fittings"],
        "min_temp": 15, "max_temp": 25, "min_hum": 30, "max_hum": 50,
        "dwell_limit": 365, "zone_types": ["ambient"],
    },
    "Medical Devices": {
        "products": ["Surgical Masks", "Bandage Rolls", "Syringe Packs", "Glove Boxes", "Cotton Swabs"],
        "min_temp": 15, "max_temp": 25, "min_hum": 30, "max_hum": 50,
        "dwell_limit": 365, "zone_types": ["ambient"],
    },
}

# Timeline constants
READING_START = datetime(2026, 10, 1, 0, 0, 0)
READING_INTERVAL_MIN = 15

# Anomaly injection rates (fraction of sensors affected)
ANOMALY_RATES = {
    "temperature_excursion": 0.05,
    "humidity_excursion": 0.05,
    "sensor_drift": 0.03,
    "sensor_outage": 0.03,
    "abnormal_occupancy": 0.04,
    "prolonged_door": 0.05,
}

INSPECTORS = ["Alice Chen", "Bob Patel", "Carol Smith", "David Osei", "Elena Rossi", "Frank Mueller"]
REMEDIATORS = ["George Lee", "Hannah Park", "Ivan Petrov", "Julia Costa"]


# ═══════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════

def generate_dataset(db: Session, full: bool = True) -> dict:
    """Generate the complete dataset into *db*.

    Returns a summary dict with row counts.
    """
    from app.database import reset_db
    reset_db()

    rng = np.random.default_rng(SEED)
    cfg = FULL_CONFIG if full else STARTER_CONFIG

    summary: dict = {}

    # 1. Storage requirements (independent of warehouses)
    _gen_storage_requirements(db)

    # 2. Warehouses
    warehouses = _gen_warehouses(db, rng, cfg)
    summary["warehouses"] = len(warehouses)

    # 3. Zones
    zones = _gen_zones(db, rng, cfg, warehouses)
    summary["zones"] = len(zones)

    # 4. Sensors
    sensors, sensor_zone_map = _gen_sensors(db, rng, cfg, zones)
    summary["sensors"] = len(sensors)

    # 5. Sensor-zone mappings (includes negative scenario #2)
    _gen_sensor_zone_mappings(db, rng, sensors, sensor_zone_map)

    # 6. Sensor readings (with anomaly injection)
    ground_truth, reading_ids = _gen_readings(db, rng, cfg, sensors, zones)
    summary["sensor_readings"] = sum(len(ids) for ids in reading_ids.values())

    # 7. Door events (with prolonged open anomaly)
    gt_door = _gen_door_events(db, rng, cfg, zones, sensors, ground_truth)
    summary["door_events"] = len(gt_door) + sum(
        1 for _ in db.query(DoorEvent).all()
    )

    # 8. Inventory lots (with negative scenario #1)
    inventory = _gen_inventory(db, rng, cfg, zones, ground_truth, READING_START)
    summary["inventory_lots"] = len(inventory)

    # 9. Pre-existing alarms for negative scenario #4
    _gen_pre_existing_alarms(db, rng, zones, inventory, ground_truth)

    # 10. Persist ground truth
    _persist_ground_truth(db, ground_truth)
    summary["ground_truth_anomalies"] = len(ground_truth)

    db.commit()
    summary["door_events"] = db.query(DoorEvent).count()
    summary["inventory_lots"] = db.query(InventoryLot).count()
    return summary


# ═══════════════════════════════════════════════════════════════════════════
#  Entity generators
# ═══════════════════════════════════════════════════════════════════════════

def _gen_storage_requirements(db: Session):
    for idx, (category, info) in enumerate(PRODUCT_CATALOG.items(), start=1):
        db.add(StorageRequirement(
            id=idx,
            product_category=category,
            min_temp_c=info["min_temp"],
            max_temp_c=info["max_temp"],
            min_humidity_pct=info["min_hum"],
            max_humidity_pct=info["max_hum"],
            dwell_time_limit_days=info["dwell_limit"],
            compatible_zone_types=info["zone_types"],
        ))
    db.flush()


def _gen_warehouses(db, rng, cfg) -> list[Warehouse]:
    warehouses = []
    for i in range(1, cfg["n_warehouses"] + 1):
        wh = Warehouse(
            id=i,
            name=WAREHOUSE_NAMES[i - 1],
            location=WAREHOUSE_LOCATIONS[i - 1],
            total_area_sqm=float(rng.uniform(5000, 25000)),
            manager=MANAGERS[(i - 1) % len(MANAGERS)],
            created_at=datetime(2025, 12, 1) + timedelta(days=int(i)),
        )
        db.add(wh)
        warehouses.append(wh)
    db.flush()
    return warehouses


def _gen_zones(db, rng, cfg, warehouses) -> list[Zone]:
    zones = []
    zone_id = 1
    for wh in warehouses:
        for j in range(cfg["n_zones_per_wh"]):
            zt = ZONE_TYPES[(zone_id - 1) % len(ZONE_TYPES)]
            cond = ZONE_CONDITIONS[zt]
            mid_temp = (cond["min_temp"] + cond["max_temp"]) / 2
            mid_hum = (cond["min_hum"] + cond["max_hum"]) / 2
            zone = Zone(
                id=zone_id,
                warehouse_id=wh.id,
                name=f"Zone-{wh.id:02d}-{j + 1:02d}",
                zone_type=zt,
                area_sqm=float(rng.uniform(200, 1200)),
                max_occupancy=int(rng.integers(20, 100)),
                min_temp_c=cond["min_temp"],
                max_temp_c=cond["max_temp"],
                min_humidity_pct=cond["min_hum"],
                max_humidity_pct=cond["max_hum"],
            )
            db.add(zone)
            zones.append(zone)
            zone_id += 1
    db.flush()
    return zones


def _gen_sensors(db, rng, cfg, zones) -> tuple[list[Sensor], dict]:
    """Return (sensors, sensor_zone_map) where sensor_zone_map maps
    sensor_id → zone_id for quick lookup."""
    sensors = []
    sensor_zone_map = {}
    sensor_id = 1
    install_base = datetime(2025, 9, 1)

    for zone in zones:
        n = min(cfg["n_sensors_per_zone"], len(SENSOR_TYPES))
        for k in range(n):
            stype = SENSOR_TYPES[k % len(SENSOR_TYPES)]
            installed = install_base + timedelta(days=int(rng.integers(0, 30)))
            calibrated = installed + timedelta(days=int(rng.integers(30, 60)))
            sensor = Sensor(
                id=sensor_id,
                zone_id=zone.id,
                sensor_type=stype,
                status="active",
                manufacturer=SENSOR_MANUFACTURERS[int(rng.integers(0, len(SENSOR_MANUFACTURERS)))],
                model=SENSOR_MODELS[int(rng.integers(0, len(SENSOR_MODELS)))],
                installed_at=installed,
                last_calibrated_at=calibrated,
            )
            db.add(sensor)
            sensors.append(sensor)
            sensor_zone_map[sensor_id] = zone.id
            sensor_id += 1
    db.flush()
    return sensors, sensor_zone_map


def _gen_sensor_zone_mappings(db, rng, sensors, sensor_zone_map):
    """Create primary mappings for all sensors, then inject negative
    scenario #2: a few sensors mapped to multiple zones without justification."""
    for sensor in sensors:
        db.add(SensorZoneMapping(
            sensor_id=sensor.id,
            zone_id=sensor.zone_id,
            is_primary=True,
            justification="Primary zone assignment",
            assigned_at=sensor.installed_at,
        ))

    # Negative scenario #2: ~2% of sensors get a secondary zone mapping
    # with no justification
    n_multi = max(3, len(sensors) // 50)
    multi_sensor_ids = rng.choice(len(sensors), size=n_multi, replace=False)
    zone_ids = [s.zone_id for s in sensors]
    for idx in multi_sensor_ids:
        sensor = sensors[idx]
        # pick a different zone
        other_zones = [z for z in zone_ids if z != sensor.zone_id]
        if not other_zones:
            continue
        extra_zone = int(rng.choice(other_zones))
        db.add(SensorZoneMapping(
            sensor_id=sensor.id,
            zone_id=extra_zone,
            is_primary=False,
            justification=None,  # no justification → anomaly
            assigned_at=sensor.installed_at + timedelta(days=10),
        ))
    db.flush()


def _gen_readings(db, rng, cfg, sensors, zones) -> tuple[list, dict]:
    """Generate sensor readings with anomaly injection.

    Returns (ground_truth, reading_ids) where reading_ids maps sensor_id to
    a list of reading IDs (for ground-truth tracking).
    """
    zone_lookup = {z.id: z for z in zones}
    ground_truth: list[GroundTruthAnomaly] = []
    reading_ids: dict[int, list[int]] = {}

    reading_id = 1
    batch: list[dict] = []
    BATCH_SIZE = 10_000

    # Pre-select sensors for each anomaly type (deterministic via rng)
    sensor_arr = np.arange(len(sensors))
    rng.shuffle(sensor_arr)

    temp_sensors = [s for s in sensors if s.sensor_type == "temperature"]
    hum_sensors = [s for s in sensors if s.sensor_type == "humidity"]
    occ_sensors = [s for s in sensors if s.sensor_type == "occupancy"]
    door_sensors = [s for s in sensors if s.sensor_type == "door"]

    def _select(pool, frac):
        n = max(1, int(len(pool) * frac))
        idxs = rng.choice(len(pool), size=min(n, len(pool)), replace=False)
        return [pool[i] for i in idxs]

    anom_temp = _select(temp_sensors, ANOMALY_RATES["temperature_excursion"])
    anom_hum = _select(hum_sensors, ANOMALY_RATES["humidity_excursion"])
    anom_drift = _select(temp_sensors + hum_sensors, ANOMALY_RATES["sensor_drift"])
    anom_outage = _select(sensors, ANOMALY_RATES["sensor_outage"])
    anom_occ = _select(occ_sensors, ANOMALY_RATES["abnormal_occupancy"])
    anom_door = _select(door_sensors, ANOMALY_RATES["prolonged_door"])

    anomaly_sets = {
        "temperature_excursion": {s.id for s in anom_temp},
        "humidity_excursion": {s.id for s in anom_hum},
        "sensor_drift": {s.id for s in anom_drift},
        "sensor_outage": {s.id for s in anom_outage},
        "abnormal_occupancy": {s.id for s in anom_occ},
        "prolonged_door": {s.id for s in anom_door},
    }

    n_readings = cfg["n_readings_per_sensor"]

    for sensor in sensors:
        zone = zone_lookup[sensor.zone_id]
        mid_temp = (zone.min_temp_c + zone.max_temp_c) / 2
        temp_range = zone.max_temp_c - zone.min_temp_c
        mid_hum = (zone.min_humidity_pct + zone.max_humidity_pct) / 2
        hum_range = zone.max_humidity_pct - zone.min_humidity_pct

        timestamps = [READING_START + timedelta(minutes=READING_INTERVAL_MIN * i)
                      for i in range(n_readings)]

        sensor_reading_ids: list[int] = []

        for i, ts in enumerate(timestamps):
            # Determine if this reading is in an anomaly window
            is_anomaly = False
            temp_val = None
            hum_val = None
            occ_val = None
            door_val = None
            is_missing = False

            progress = i / n_readings  # 0..1 position in the time series

            # ── Generate base values ──────────────────────────────────────
            if sensor.sensor_type == "temperature":
                base = mid_temp + float(rng.normal(0, temp_range * 0.08))

                if sensor.id in anomaly_sets["temperature_excursion"]:
                    # Inject excursion in a 4-hour window starting at 40-60% of timeline
                    start_idx = int(n_readings * rng.uniform(0.4, 0.6))
                    excursion_len = int(rng.integers(8, 32))
                    if start_idx <= i < start_idx + excursion_len:
                        base = zone.max_temp_c + float(rng.uniform(3, 8))
                        is_anomaly = True

                if sensor.id in anomaly_sets["sensor_drift"]:
                    # Linear drift accumulating to ~10°C by end
                    drift = progress * 10
                    base += drift
                    if progress > 0.5:
                        is_anomaly = True

                temp_val = round(base, 2)

            elif sensor.sensor_type == "humidity":
                base = mid_hum + float(rng.normal(0, hum_range * 0.08))

                if sensor.id in anomaly_sets["humidity_excursion"]:
                    start_idx = int(n_readings * rng.uniform(0.4, 0.6))
                    excursion_len = int(rng.integers(8, 32))
                    if start_idx <= i < start_idx + excursion_len:
                        base = zone.max_humidity_pct + float(rng.uniform(5, 15))
                        is_anomaly = True

                if sensor.id in anomaly_sets["sensor_drift"]:
                    drift = progress * 8
                    base += drift
                    if progress > 0.5:
                        is_anomaly = True

                hum_val = round(base, 2)

            elif sensor.sensor_type == "occupancy":
                base = int(rng.integers(0, zone.max_occupancy + 1))

                if sensor.id in anomaly_sets["abnormal_occupancy"]:
                    start_idx = int(n_readings * rng.uniform(0.4, 0.6))
                    occ_len = int(rng.integers(4, 16))
                    if start_idx <= i < start_idx + occ_len:
                        base = zone.max_occupancy + int(rng.integers(5, 20))
                        is_anomaly = True

                occ_val = base

            elif sensor.sensor_type == "door":
                # Mostly closed, occasionally opens briefly
                base = "closed"
                if rng.random() < 0.05:
                    base = "open"
                door_val = base

            # ── Sensor outage: mark readings as missing ───────────────────
            if sensor.id in anomaly_sets["sensor_outage"]:
                outage_start = int(n_readings * rng.uniform(0.3, 0.5))
                outage_len = int(rng.integers(8, 64))
                if outage_start <= i < outage_start + outage_len:
                    is_missing = True
                    is_anomaly = True
                    if sensor.sensor_type == "temperature":
                        temp_val = None
                    elif sensor.sensor_type == "humidity":
                        hum_val = None
                    elif sensor.sensor_type == "occupancy":
                        occ_val = None
                    elif sensor.sensor_type == "door":
                        door_val = None

            rec = {
                "id": reading_id,
                "sensor_id": sensor.id,
                "reading_timestamp": ts,
                "temperature_c": temp_val,
                "humidity_pct": hum_val,
                "occupancy_count": occ_val,
                "door_state": door_val,
                "is_missing": is_missing,
                "is_anomaly_injected": is_anomaly,
            }
            batch.append(rec)
            sensor_reading_ids.append(reading_id)
            reading_id += 1

            if is_anomaly and not is_missing:
                gt = GroundTruthAnomaly(
                    anomaly_type=_anomaly_type_for(sensor, anomaly_sets),
                    entity_type="sensor_reading",
                    entity_id=reading_id - 1,
                    description=f"Injected anomaly in sensor {sensor.id} "
                                f"({sensor.sensor_type}) at {ts.isoformat()}",
                    true_severity=_severity_for(sensor, anomaly_sets),
                    injected_at=datetime.utcnow(),
                )
                ground_truth.append(gt)
            elif is_anomaly and is_missing:
                gt = GroundTruthAnomaly(
                    anomaly_type="sensor_outage",
                    entity_type="sensor_reading",
                    entity_id=reading_id - 1,
                    description=f"Sensor {sensor.id} outage at {ts.isoformat()}",
                    true_severity="warning",
                    injected_at=datetime.utcnow(),
                )
                ground_truth.append(gt)

            if len(batch) >= BATCH_SIZE:
                db.bulk_insert_mappings(SensorReading, batch)
                db.commit()
                batch.clear()

        reading_ids[sensor.id] = sensor_reading_ids

    if batch:
        db.bulk_insert_mappings(SensorReading, batch)
        db.commit()

    return ground_truth, reading_ids


def _anomaly_type_for(sensor, anomaly_sets):
    if sensor.id in anomaly_sets["temperature_excursion"]:
        return "temperature_violation"
    if sensor.id in anomaly_sets["humidity_excursion"]:
        return "humidity_violation"
    if sensor.id in anomaly_sets["sensor_drift"]:
        return "sensor_drift"
    if sensor.id in anomaly_sets["abnormal_occupancy"]:
        return "abnormal_occupancy"
    if sensor.id in anomaly_sets["prolonged_door"]:
        return "prolonged_door_open"
    return "unknown"


def _severity_for(sensor, anomaly_sets):
    if sensor.id in anomaly_sets["temperature_excursion"]:
        return "critical"
    if sensor.id in anomaly_sets["humidity_excursion"]:
        return "warning"
    if sensor.id in anomaly_sets["sensor_drift"]:
        return "warning"
    if sensor.id in anomaly_sets["abnormal_occupancy"]:
        return "warning"
    return "info"


def _gen_door_events(db, rng, cfg, zones, sensors, ground_truth) -> list:
    """Generate door events including prolonged open anomalies."""
    door_sensors = [s for s in sensors if s.sensor_type == "door"]
    zone_lookup = {z.id: z for z in zones}
    n_readings = cfg["n_readings_per_sensor"]
    event_id = 1
    events_created = []

    for sensor in door_sensors:
        zone = zone_lookup[sensor.zone_id]
        # Generate ~1 event per 4 hours of operation
        n_events = n_readings // 16  # every 4 hours
        event_times = [
            READING_START + timedelta(minutes=READING_INTERVAL_MIN * int(rng.integers(0, n_readings)))
            for _ in range(n_events)
        ]
        event_times.sort()

        prolonged = sensor.id in {s.id for s in door_sensors if
                                   rng.random() < ANOMALY_RATES["prolonged_door"]}

        for ts in event_times:
            if prolonged and rng.random() < 0.15:
                # Prolonged door open: 30-120 minutes
                duration = float(rng.uniform(1800, 7200))
                is_anom = True
            else:
                duration = float(rng.uniform(10, 120))
                is_anom = False

            db.add(DoorEvent(
                id=event_id,
                zone_id=zone.id,
                sensor_id=sensor.id,
                event_timestamp=ts,
                event_type="open",
                duration_seconds=duration,
                is_anomaly_injected=is_anom,
            ))
            events_created.append(event_id)
            event_id += 1

            if is_anom:
                ground_truth.append(GroundTruthAnomaly(
                    anomaly_type="prolonged_door_open",
                    entity_type="door_event",
                    entity_id=event_id - 1,
                    description=f"Prolonged door open in zone {zone.id} "
                                f"({duration/60:.0f} min) at {ts.isoformat()}",
                    true_severity="warning",
                    injected_at=datetime.utcnow(),
                ))

    db.flush()
    return events_created


def _gen_inventory(db, rng, cfg, zones, ground_truth, data_start) -> list[InventoryLot]:
    """Generate inventory lots with negative scenario #1 (incompatible zone)."""
    categories = list(PRODUCT_CATALOG.keys())
    inventory = []
    lot_id = 1
    end_time = data_start + timedelta(
        minutes=READING_INTERVAL_MIN * cfg["n_readings_per_sensor"])

    # Pre-compute zone types
    zone_types = {z.id: z.zone_type for z in zones}

    # Negative scenario #1: ~2% of lots assigned to incompatible zones
    n_incompatible = max(5, cfg["n_inventory_lots"] // 50)
    incompatible_lot_ids = set(int(x) for x in
                              rng.choice(cfg["n_inventory_lots"],
                                          size=min(n_incompatible, cfg["n_inventory_lots"]),
                                          replace=False))

    for i in range(cfg["n_inventory_lots"]):
        cat_idx = int(rng.integers(0, len(categories)))
        category = categories[cat_idx]
        info = PRODUCT_CATALOG[category]
        product_name = str(rng.choice(info["products"]))

        # Normally assign to a compatible zone
        compatible = [z for z in zones if z.zone_type in info["zone_types"]]
        if (i + 1) in incompatible_lot_ids:
            # Negative scenario #1: assign to an incompatible zone
            incompatible_zones = [z for z in zones if z.zone_type not in info["zone_types"]]
            if incompatible_zones:
                zone = incompatible_zones[int(rng.integers(0, len(incompatible_zones)))]
            else:
                zone = compatible[int(rng.integers(0, len(compatible)))] if compatible else zones[0]
        else:
            if compatible:
                zone = compatible[int(rng.integers(0, len(compatible)))]
            else:
                zone = zones[int(rng.integers(0, len(zones)))]

        arrival = data_start + timedelta(
            minutes=int(rng.integers(0, READING_INTERVAL_MIN * cfg["n_readings_per_sensor"])))
        is_departed = rng.random() < 0.6
        if is_departed:
            max_dwell_days = max(1, (end_time - arrival).days)
            dwell_days = int(rng.integers(1, min(info["dwell_limit"], max_dwell_days) + 1))
            departure = arrival + timedelta(days=dwell_days)
            status = "departed"
        else:
            departure = None
            # Check if expired based on dwell time
            dwell = (datetime.utcnow() - arrival).days
            status = "expired" if dwell > info["dwell_limit"] else "stored"

        lot = InventoryLot(
            id=lot_id,
            zone_id=zone.id,
            product_name=product_name,
            product_category=category,
            quantity=int(rng.integers(10, 1000)),
            unit="units",
            batch_number=f"LOT-{lot_id:06d}",
            arrival_date=arrival,
            departure_date=departure,
            status=status,
        )
        db.add(lot)
        inventory.append(lot)

        if (i + 1) in incompatible_lot_ids:
            ground_truth.append(GroundTruthAnomaly(
                anomaly_type="inventory_incompatible_zone",
                entity_type="inventory_lot",
                entity_id=lot_id,
                description=f"Inventory lot {lot_id} ({product_name}, {category}) "
                            f"assigned to incompatible zone {zone.id} "
                            f"(type {zone.zone_type}, requires {info['zone_types']})",
                true_severity="critical",
                injected_at=datetime.utcnow(),
            ))

        lot_id += 1

    db.flush()
    return inventory


def _gen_pre_existing_alarms(db, rng, zones, inventory, ground_truth):
    """Generate a few pre-existing alarms that are NOT linked to affected
    inventory (negative scenario #4).

    These simulate manually-created alarms where the inventory linkage was
    forgotten.  The validation module should flag them.
    """
    alarm_id = 1  # detection will start from a higher offset
    n_broken = 10

    for _ in range(n_broken):
        zone = zones[int(rng.integers(0, len(zones)))]
        ts = READING_START + timedelta(
            minutes=int(rng.integers(0, 10000)))

        alarm = Alarm(
            id=alarm_id,
            alarm_type="temperature_violation",
            severity=str(rng.choice(["critical", "warning"])),
            zone_id=zone.id,
            sensor_id=None,
            start_timestamp=ts,
            end_timestamp=ts + timedelta(hours=2),
            description=f"Temperature excursion detected in {zone.name} "
                        f"(manual entry — inventory linkage missing)",
            recommended_action="Verify zone temperature and relocate affected inventory.",
            status="active",
            source="preexisting",
            created_at=ts,
        )
        db.add(alarm)
        # Deliberately do NOT create AlarmInventoryLot entries → scenario #4

        ground_truth.append(GroundTruthAnomaly(
            anomaly_type="alarm_missing_inventory_link",
            entity_type="alarm",
            entity_id=alarm_id,
            description=f"Alarm {alarm_id} is not linked to any affected "
                        f"inventory lots despite inventory present in zone "
                        f"{zone.id}",
            true_severity="warning",
            injected_at=datetime.utcnow(),
        ))
        alarm_id += 1

    db.flush()


def _persist_ground_truth(db, ground_truth):
    for i, gt in enumerate(ground_truth, start=1):
        gt.id = i
    db.bulk_insert_mappings(GroundTruthAnomaly, [
        {
            "id": gt.id,
            "anomaly_type": gt.anomaly_type,
            "entity_type": gt.entity_type,
            "entity_id": gt.entity_id,
            "description": gt.description,
            "true_severity": gt.true_severity,
            "injected_at": gt.injected_at,
        }
        for gt in ground_truth
    ])
    db.flush()


# ═══════════════════════════════════════════════════════════════════════════
#  Reproducibility check
# ═══════════════════════════════════════════════════════════════════════════

def compute_checksums(db: Session) -> dict:
    """Compute row counts and checksums for reproducibility verification."""
    tables = [
        "warehouses", "zones", "sensors", "sensor_readings",
        "door_events", "inventory_lots", "storage_requirements",
        "sensor_zone_mappings", "ground_truth_anomalies",
    ]
    result = {}
    for t in tables:
        count = db.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        result[f"{t}_count"] = count
    return result
