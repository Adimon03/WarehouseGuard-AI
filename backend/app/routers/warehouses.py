"""Warehouse API routes."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.database import get_db
from app.models import Warehouse, Zone, Sensor, InventoryLot
from app.schemas import WarehouseOut

router = APIRouter()


@router.get("/", response_model=list[WarehouseOut])
def list_warehouses(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.execute(text("""
        SELECT w.*, (
            SELECT COUNT(*) FROM zones z WHERE z.warehouse_id = w.id
        ) as zone_count
        FROM warehouses w
        ORDER BY w.id
        LIMIT :limit OFFSET :offset
    """), {"limit": limit, "offset": offset}).fetchall()
    return [{"id": r.id, "name": r.name, "location": r.location,
             "total_area_sqm": r.total_area_sqm, "manager": r.manager,
             "created_at": r.created_at, "zone_count": r.zone_count} for r in rows]


@router.get("/{warehouse_id}", response_model=WarehouseOut)
def get_warehouse(warehouse_id: int, db: Session = Depends(get_db)):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Warehouse not found")
    zone_count = db.query(func.count(Zone.id)).filter(Zone.warehouse_id == warehouse_id).scalar()
    return {"id": wh.id, "name": wh.name, "location": wh.location,
            "total_area_sqm": wh.total_area_sqm, "manager": wh.manager,
            "created_at": wh.created_at, "zone_count": zone_count}
