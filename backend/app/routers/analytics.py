"""Analytics API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.analytics import (
    get_kpi_summary, get_temperature_trend, get_humidity_trend,
    get_occupancy_trend, get_door_event_stats, get_alert_metrics,
    get_alarm_distribution, get_sensor_health, get_inventory_impact,
    get_compliance_by_zone, get_zone_summary,
)

router = APIRouter()


@router.get("/kpis")
def kpis(db: Session = Depends(get_db)):
    return get_kpi_summary(db)


@router.get("/trends/temperature")
def temp_trend(zone_id: int | None = Query(None), hours: int = Query(48, le=500),
               db: Session = Depends(get_db)):
    return get_temperature_trend(db, zone_id, hours)


@router.get("/trends/humidity")
def hum_trend(zone_id: int | None = Query(None), hours: int = Query(48, le=500),
              db: Session = Depends(get_db)):
    return get_humidity_trend(db, zone_id, hours)


@router.get("/trends/occupancy")
def occ_trend(zone_id: int | None = Query(None), hours: int = Query(48, le=500),
              db: Session = Depends(get_db)):
    return get_occupancy_trend(db, zone_id, hours)


@router.get("/door-event-stats")
def door_stats(zone_id: int | None = Query(None), db: Session = Depends(get_db)):
    return get_door_event_stats(db, zone_id)


@router.get("/alert-metrics")
def alert_metrics(db: Session = Depends(get_db)):
    return get_alert_metrics(db)


@router.get("/alarm-distribution")
def alarm_dist(db: Session = Depends(get_db)):
    return get_alarm_distribution(db)


@router.get("/sensor-health")
def sensor_health(db: Session = Depends(get_db)):
    return get_sensor_health(db)


@router.get("/inventory-impact")
def inv_impact(db: Session = Depends(get_db)):
    return get_inventory_impact(db)


@router.get("/compliance-by-zone")
def compliance(db: Session = Depends(get_db)):
    return get_compliance_by_zone(db)


@router.get("/zone-summary/{zone_id}")
def zone_summary(zone_id: int, db: Session = Depends(get_db)):
    return get_zone_summary(db, zone_id)
