# Database Schema

## Entity Relationship

```
Warehouse (10)
  └── Zone (100)
        ├── Sensor (500)
        │     ├── SensorZoneMapping (M:N)
        │     └── SensorReading (1,000,000)
        ├── DoorEvent
        └── InventoryLot (10,000)

StorageRequirement (10) — standalone, referenced by InventoryLot.product_category

Alarm
  ├── AlarmInventoryLot (M:N with InventoryLot)
  ├── Inspection
  └── Remediation
        └── Inspection (optional FK)

GroundTruthAnomaly — isolated, for evaluation only
```

## Key Constraints

- All PKs are deterministic integers (seed 20261022)
- Foreign keys enforced via SQLAlchemy ORM and SQLite PRAGMA
- `sensor_zone_mappings.justification` NULL = anomaly (negative scenario #2)
- `sensor_readings.is_missing = 1` = sensor outage (must NOT be treated as normal)
- `alarms.source = "preexisting"` = data-generator alarm; `"detection"` = auto-generated
- `ground_truth_anomalies` is never referenced by detection logic

## Reproducibility

Generating the dataset twice with seed 20261022 produces identical row counts and data.
