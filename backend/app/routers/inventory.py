"""Inventory API routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import InventoryLot, Zone, StorageRequirement

router = APIRouter()


@router.get("/")
def list_inventory(
    zone_id: int | None = Query(None),
    product_category: str | None = Query(None),
    status: str | None = Query(None),
    incompatible_only: bool = Query(False),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    where = ["1=1"]
    params: dict = {"limit": limit, "offset": offset}

    if zone_id:
        where.append("il.zone_id = :zone_id")
        params["zone_id"] = zone_id
    if product_category:
        where.append("il.product_category = :product_category")
        params["product_category"] = product_category
    if status:
        where.append("il.status = :status")
        params["status"] = status

    where_clause = " AND ".join(where)

    if incompatible_only:
        sql = f"""
            SELECT il.*, z.name as zone_name, z.zone_type,
                   sr.compatible_zone_types
            FROM inventory_lots il
            JOIN zones z ON il.zone_id = z.id
            JOIN storage_requirements sr ON il.product_category = sr.product_category
            WHERE {where_clause}
              AND z.zone_type NOT IN (SELECT value FROM json_each(sr.compatible_zone_types))
            ORDER BY il.id
            LIMIT :limit OFFSET :offset
        """
    else:
        sql = f"""
            SELECT il.id, il.zone_id, il.product_name, il.product_category,
                   il.quantity, il.unit, il.batch_number, il.arrival_date,
                   il.departure_date, il.status,
                   z.name as zone_name, z.zone_type
            FROM inventory_lots il
            JOIN zones z ON il.zone_id = z.id
            WHERE {where_clause}
            ORDER BY il.id
            LIMIT :limit OFFSET :offset
        """

    count_sql = f"""
        SELECT COUNT(*) FROM inventory_lots il JOIN zones z ON il.zone_id = z.id
        WHERE {where_clause}
    """
    total = db.execute(text(count_sql), params).scalar()

    rows = db.execute(text(sql), params).fetchall()
    data = []
    for r in rows:
        data.append({
            "id": r[0], "zone_id": r[1], "product_name": r[2],
            "product_category": r[3], "quantity": r[4], "unit": r[5],
            "batch_number": r[6], "arrival_date": str(r[7]),
            "departure_date": str(r[8]) if r[8] else None, "status": r[9],
            "zone_name": r[10] if len(r) > 10 else None,
            "zone_type": r[11] if len(r) > 11 else None,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + limit < total,
        "data": data,
    }


@router.get("/{lot_id}")
def get_inventory_lot(lot_id: int, db: Session = Depends(get_db)):
    lot = db.query(InventoryLot).filter(InventoryLot.id == lot_id).first()
    if not lot:
        raise HTTPException(status_code=404, detail="Inventory lot not found")
    zone = db.query(Zone).filter(Zone.id == lot.zone_id).first()
    req = db.query(StorageRequirement).filter(
        StorageRequirement.product_category == lot.product_category).first()
    return {
        "id": lot.id, "zone_id": lot.zone_id,
        "zone_name": zone.name if zone else None,
        "zone_type": zone.zone_type if zone else None,
        "product_name": lot.product_name,
        "product_category": lot.product_category,
        "quantity": lot.quantity, "unit": lot.unit,
        "batch_number": lot.batch_number,
        "arrival_date": str(lot.arrival_date),
        "departure_date": str(lot.departure_date) if lot.departure_date else None,
        "status": lot.status,
        "compatible_zone_types": req.compatible_zone_types if req else [],
        "is_compatible": (zone.zone_type in req.compatible_zone_types)
                         if zone and req else True,
    }
