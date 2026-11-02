"""
WarehouseGuard AI — End-to-end runner.

Usage:
    python run.py                    # starter dataset
    python run.py --full             # full dataset (1M readings)
    python run.py --export-only      # just export CSV/JSON from existing DB
"""
import sys
import os
import csv
import json
import argparse

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")

from app.database import SessionLocal
from app.data_generator import generate_dataset, compute_checksums
from app.anomaly_detection import run_detection
from app.validation import run_validation
from app.analytics import get_kpi_summary, get_alert_metrics

EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(EXPORT_DIR, exist_ok=True)

TABLES = [
    "warehouses", "zones", "sensors", "sensor_readings",
    "door_events", "storage_requirements", "inventory_lots",
    "alarms", "alarm_inventory_lots", "inspections", "remediations",
    "sensor_zone_mappings", "ground_truth_anomalies",
]


def export_csv(db, table):
    """Export a table to CSV."""
    from sqlalchemy import text
    rows = db.execute(text(f"SELECT * FROM {table}")).fetchall()
    if not rows:
        return 0
    path = os.path.join(EXPORT_DIR, f"{table}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(rows[0]._fields)
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row])
    return len(rows)


def export_ground_truth(db):
    """Export ground truth to CSV and JSON."""
    from sqlalchemy import text
    rows = db.execute(text("SELECT * FROM ground_truth_anomalies")).fetchall()
    if not rows:
        return

    cols = rows[0]._fields
    data = [dict(zip(cols, [str(v) if v is not None else None for v in row])) for row in rows]

    csv_path = os.path.join(EXPORT_DIR, "ground_truth.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows(data)

    json_path = os.path.join(EXPORT_DIR, "ground_truth.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"  Ground truth exported: {len(data)} anomalies → ground_truth.csv + ground_truth.json")


def export_validation_summary(db):
    """Export validation report to JSON."""
    report = run_validation(db)
    path = os.path.join(EXPORT_DIR, "validation_summary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Validation: {report['passed']} passed, {report['failed']} failed, {report['warnings']} warnings → validation_summary.json")
    return report


def check_reproducibility(full=False):
    """Regenerate twice with same seed and compare row counts."""
    print("\n=== Reproducibility Check ===")
    db1 = SessionLocal()
    generate_dataset(db1, full=full)
    c1 = compute_checksums(db1)
    db1.close()

    db2 = SessionLocal()
    generate_dataset(db2, full=full)
    c2 = compute_checksums(db2)
    db2.close()

    all_match = True
    for key in c1:
        status = "OK" if c1[key] == c2[key] else "MISMATCH"
        if c1[key] != c2[key]:
            all_match = False
        print(f"  {key}: {c1[key]} vs {c2[key]} → {status}")

    if all_match:
        print("  ✓ Reproducibility verified — all row counts match")
    else:
        print("  ✗ Reproducibility FAILED — row counts differ")
    return all_match


def main():
    parser = argparse.ArgumentParser(description="WarehouseGuard AI runner")
    parser.add_argument("--full", action="store_true", help="Generate full dataset (1M readings)")
    parser.add_argument("--export-only", action="store_true", help="Only export from existing DB")
    args = parser.parse_args()

    db = SessionLocal()

    if not args.export_only:
        # Step 1-6: Generate data
        print("=== Data Generation ===")
        full = args.full
        print(f"  Mode: {'full (1M readings)' if full else 'starter'}")
        summary = generate_dataset(db, full=full)
        for k, v in summary.items():
            print(f"  {k}: {v}")

        # Step 7: Run detection (business logic)
        print("\n=== Anomaly Detection ===")
        det = run_detection(db)
        print(f"  Alarms created: {det['alarms_created']}")
        print(f"  Inspections: {det['inspections_created']}")
        print(f"  Remediations: {det['remediations_created']}")
        for k, v in det['by_type'].items():
            print(f"    {k}: {v}")

    # Step 8: Validation
    print("\n=== Validation ===")
    report = export_validation_summary(db)
    for check in report["checks"]:
        if check["status"] != "pass":
            print(f"  [{check['status'].upper()}] {check['check']}: {check['detail'][:100]}")

    # Step 9: Export CSV/JSON
    print("\n=== Exporting CSV/JSON ===")
    for table in TABLES:
        try:
            count = export_csv(db, table)
            print(f"  {table}.csv: {count} rows")
        except Exception as e:
            print(f"  {table}.csv: ERROR - {e}")

    export_ground_truth(db)

    # Analytics summary
    print("\n=== Analytics Summary ===")
    kpis = get_kpi_summary(db)
    print(f"  Environmental compliance: {kpis['environmental_compliance_rate']}%")
    print(f"  Sensor availability: {kpis['sensor_availability']}%")
    print(f"  Active alarms: {kpis['active_alarms']}")
    print(f"  Critical alarms: {kpis['critical_alarms']}")
    print(f"  Affected inventory: {kpis['affected_inventory_lots']}")

    metrics = get_alert_metrics(db)
    print(f"  Detection precision: {metrics['precision']}")
    print(f"  Detection recall: {metrics['recall']}")
    print(f"  Detection F1: {metrics['f1_score']}")

    db.close()

    # Step 10: Reproducibility
    if not args.export_only:
        check_reproducibility(full=args.full)

    print("\n=== Done ===")
    print(f"  Exports saved to: {os.path.abspath(EXPORT_DIR)}")


if __name__ == "__main__":
    main()
