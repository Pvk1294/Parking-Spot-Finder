# main.py — Python Parking API (FastAPI + SQLAlchemy)
import math
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import (create_engine, Column, Integer, String, Boolean, Float,
                        ForeignKey, Text, text, and_, or_)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/parking")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

# -------------------- ORM MODELS --------------------
class ParkingLot(Base):
    __tablename__ = "parking_lot"
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    spots = relationship("ParkingSpot", back_populates="lot", cascade="all, delete-orphan")

class ParkingSpot(Base):
    __tablename__ = "parking_spot"
    id = Column(Integer, primary_key=True)
    lot_id = Column(Integer, ForeignKey("parking_lot.id", ondelete="CASCADE"), nullable=False)
    number = Column(Text, nullable=False)
    type = Column(Text, nullable=False, default="car")
    is_available = Column(Boolean, nullable=False, default=True)

    lot = relationship("ParkingLot", back_populates="spots")
    reservations = relationship("Reservation", back_populates="spot", cascade="all, delete-orphan")

class Reservation(Base):
    __tablename__ = "reservation"
    id = Column(Integer, primary_key=True)
    spot_id = Column(Integer, ForeignKey("parking_spot.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(String, nullable=False)  # store as ISO string for simplicity
    end_time = Column(String, nullable=False)
    vehicle_plate = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")

    spot = relationship("ParkingSpot", back_populates="reservations")

# -------------------- SCHEMAS --------------------
class LotCreate(BaseModel):
    name: str
    latitude: float
    longitude: float

class LotRead(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    class Config:
        from_attributes = True

class SpotCreate(BaseModel):
    number: str
    type: str = Field(default="car", pattern="^(car|bike|ev)$")

class SpotRead(BaseModel):
    id: int
    lot_id: int
    number: str
    type: str
    is_available: bool
    class Config:
        from_attributes = True

class ReserveCreate(BaseModel):
    spot_id: int
    start_time: datetime
    end_time: datetime
    vehicle_plate: str

    @validator("end_time")
    def check_order(cls, v, values):
        st = values.get("start_time")
        if st and v <= st:
            raise ValueError("end_time must be after start_time")
        return v

class ReservationRead(BaseModel):
    id: int
    spot_id: int
    start_time: datetime
    end_time: datetime
    vehicle_plate: str
    status: str
    class Config:
        from_attributes = True

# -------------------- UTILS --------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# -------------------- APP --------------------
app = FastAPI(title="Python Parking API", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

# --- Lots ---
@app.post("/lots", response_model=LotRead, status_code=201)
def create_lot(payload: LotCreate, db: Session = Depends(get_db)):
    lot = ParkingLot(name=payload.name, latitude=payload.latitude, longitude=payload.longitude)
    db.add(lot)
    db.commit()
    db.refresh(lot)
    return lot

@app.get("/lots", response_model=List[LotRead])
def list_lots(db: Session = Depends(get_db)):
    return db.query(ParkingLot).all()

# --- Spots ---
@app.post("/lots/{lot_id}/spots", response_model=SpotRead, status_code=201)
def create_spot(lot_id: int, payload: SpotCreate, db: Session = Depends(get_db)):
    lot = db.get(ParkingLot, lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    # ensure unique per lot
    exists = db.query(ParkingSpot).filter(
        ParkingSpot.lot_id == lot_id,
        ParkingSpot.number == payload.number
    ).first()
    if exists:
        raise HTTPException(409, "Spot number already exists in this lot")
    spot = ParkingSpot(lot_id=lot_id, number=payload.number, type=payload.type, is_available=True)
    db.add(spot)
    db.commit()
    db.refresh(spot)
    return spot

@app.get("/spots", response_model=List[SpotRead])
def list_spots(only_available: bool = Query(False), db: Session = Depends(get_db)):
    q = db.query(ParkingSpot)
    if only_available:
        q = q.filter(ParkingSpot.is_available.is_(True))
    return q.all()

@app.post("/spots/{spot_id}/release", response_model=SpotRead)
def release_spot(spot_id: int, db: Session = Depends(get_db)):
    spot = db.get(ParkingSpot, spot_id)
    if not spot:
        raise HTTPException(404, "Spot not found")
    spot.is_available = True
    db.commit()
    db.refresh(spot)
    return spot

# Nearby search (available spots)
class SpotNearby(SpotRead):
    distance_m: float

@app.get("/spots/search", response_model=List[SpotNearby])
def search_spots(
    lat: float,
    lng: float,
    radius_m: int = Query(1000, ge=1, le=20000),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # fetch candidate lots first to reduce work
    lots = db.query(ParkingLot).all()
    lot_ids_in_radius = []
    for lot in lots:
        d = haversine_m(lat, lng, lot.latitude, lot.longitude)
        if d <= radius_m * 1.5:  # slight buffer
            lot_ids_in_radius.append(lot.id)
    if not lot_ids_in_radius:
        return []

    spots = db.query(ParkingSpot).filter(
        ParkingSpot.is_available.is_(True),
        ParkingSpot.lot_id.in_(lot_ids_in_radius)
    ).all()

    # attach distance from lot center
    results = []
    # pre-map lots
    lot_map = {l.id: l for l in lots}
    for s in spots:
        L = lot_map[s.lot_id]
        d = haversine_m(lat, lng, L.latitude, L.longitude)
        if d <= radius_m:
            results.append({
                "id": s.id, "lot_id": s.lot_id, "number": s.number, "type": s.type,
                "is_available": s.is_available, "distance_m": round(d, 2)
            })
    results.sort(key=lambda x: x["distance_m"])
    return results[:limit]

# --- Reservations ---
@app.post("/reservations", response_model=ReservationRead, status_code=201)
def create_reservation(payload: ReserveCreate, db: Session = Depends(get_db)):
    spot = db.get(ParkingSpot, payload.spot_id)
    if not spot:
        raise HTTPException(404, "Spot not found")

    # Prevent overlap with active reservations
    st = payload.start_time
    et = payload.end_time
    overlap = db.query(Reservation).filter(
        Reservation.spot_id == payload.spot_id,
        Reservation.status == "active",
        or_(
            and_(Reservation.start_time <= et.isoformat(), Reservation.end_time > st.isoformat()),
        )
    ).first()
    if overlap:
        raise HTTPException(409, "Spot already reserved for the selected time range")

    r = Reservation(
        spot_id=payload.spot_id,
        start_time=payload.start_time.isoformat(),
        end_time=payload.end_time.isoformat(),
        vehicle_plate=payload.vehicle_plate,
        status="active"
    )
    # mark spot unavailable
    spot.is_available = False
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

@app.post("/reservations/{reservation_id}/end", response_model=ReservationRead)
def end_reservation(reservation_id: int, db: Session = Depends(get_db)):
    r = db.get(Reservation, reservation_id)
    if not r:
        raise HTTPException(404, "Reservation not found")
    if r.status != "active":
        raise HTTPException(400, "Reservation already ended or cancelled")
    r.status = "ended"

    # free the spot
    spot = db.get(ParkingSpot, r.spot_id)
    if spot:
        spot.is_available = True
    db.commit()
    db.refresh(r)
    return r
