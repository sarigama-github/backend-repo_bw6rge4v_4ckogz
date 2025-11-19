import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr

from database import db, create_document, get_documents

app = FastAPI(title="Pictiv.Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Models
# -----------------------------
class ServiceItem(BaseModel):
    key: str = Field(..., description="Unique key for service")
    name: str
    description: str
    deliverables: List[str]
    duration: str
    price: Optional[str] = None
    addons: List[str] = []


class BookingRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: str
    service_key: str
    date: str
    time: str
    location: str
    notes: Optional[str] = None
    contact_via_whatsapp: bool = True


class InquiryRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    subject: str
    message: str


class Announcement(BaseModel):
    key: str = Field(..., description="Unique key for announcement")
    title: str
    message: str
    tag: Optional[str] = Field(default=None, description="e.g., Offer, Update")
    active: bool = True


# -----------------------------
# Utility seed data
# -----------------------------
DEFAULT_SERVICES: List[ServiceItem] = [
    ServiceItem(
        key="wedding_day",
        name="Wedding Day Package",
        description="Full-day coverage capturing rituals, candid moments, and couple portraits.",
        deliverables=[
            "600+ edited photographs",
            "Online gallery",
            "Highlight reel",
            "Optional premium album",
        ],
        duration="8-12 hours",
        price="On request",
        addons=["Extra photographer", "Same-day edit", "Drone coverage"],
    ),
    ServiceItem(
        key="pre_wedding",
        name="Pre-Wedding Shoot",
        description="A styled, cinematic session to celebrate your story.",
        deliverables=[
            "60+ edited photographs",
            "2 outfit changes",
            "Location guidance",
        ],
        duration="3-4 hours",
        price="On request",
        addons=["Short video reel", "Makeup artist"],
    ),
    ServiceItem(
        key="maternity",
        name="Maternity Package",
        description="Elegant, serene portraits celebrating motherhood.",
        deliverables=[
            "40+ edited photographs",
            "Private online gallery",
            "Wardrobe guidance",
        ],
        duration="2-3 hours",
        price="On request",
        addons=["Outdoor location", "Printed enlargements"],
    ),
    ServiceItem(
        key="portrait",
        name="Makeup & Portrait Session",
        description="Fine portraiture with a focus on expression and detail.",
        deliverables=[
            "20+ edited photographs",
            "Retouched close-ups",
            "Backdrop and lighting setup",
        ],
        duration="1-2 hours",
        price="On request",
        addons=["Professional makeup", "Studio wardrobe"],
    ),
    ServiceItem(
        key="event",
        name="Event Coverage",
        description="Thoughtful documentation of family and social gatherings.",
        deliverables=["Edited photo set", "Highlights gallery"],
        duration="As needed",
        price="Hourly / On request",
        addons=["Additional photographer"],
    ),
]

DEFAULT_ANNOUNCEMENTS: List[Announcement] = [
    Announcement(
        key="festive_offer",
        title="Festive Offer",
        message="Seasonal packages with complimentary reels on select bookings.",
        tag="Offer",
        active=True,
    ),
    Announcement(
        key="studio_update",
        title="Studio Update",
        message="Now accepting limited winter wedding bookings in Nashik.",
        tag="Update",
        active=True,
    ),
]


def ensure_services_seeded() -> None:
    if db is None:
        return
    try:
        existing = list(db["service"].find({}, {"key": 1}))
        if not existing:
            for s in DEFAULT_SERVICES:
                create_document("service", s.dict())
    except Exception:
        pass


def ensure_announcements_seeded() -> None:
    if db is None:
        return
    try:
        existing = list(db["announcement"].find({}, {"key": 1}))
        if not existing:
            for a in DEFAULT_ANNOUNCEMENTS:
                create_document("announcement", a.dict())
    except Exception:
        pass


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def read_root():
    return {"message": "Pictiv.Studio API running"}


@app.get("/api/services")
def list_services():
    ensure_services_seeded()
    try:
        records = get_documents("service")
        services = []
        for r in records:
            r.pop("_id", None)
            services.append(r)
        return {"items": services}
    except Exception as e:
        return {"items": [s.dict() for s in DEFAULT_SERVICES], "fallback": True, "error": str(e)[:120]}


@app.get("/api/announcements")
def list_announcements():
    ensure_announcements_seeded()
    try:
        records = get_documents("announcement")
        anns = []
        for r in records:
            if r.get("active", True):
                r.pop("_id", None)
                anns.append(r)
        return {"items": anns}
    except Exception as e:
        return {"items": [a.dict() for a in DEFAULT_ANNOUNCEMENTS], "fallback": True, "error": str(e)[:120]}


@app.post("/api/bookings")
def create_booking(booking: BookingRequest):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        booking_id = create_document("booking", booking.dict())
        msg = (
            f"New Booking Request - Pictiv.Studio%0A"
            f"Name: {booking.full_name}%0A"
            f"Phone: {booking.phone}%0A"
            f"Service: {booking.service_key}%0A"
            f"Date: {booking.date} {booking.time}%0A"
            f"Location: {booking.location}%0A"
            f"Notes: {booking.notes or '-'}"
        )
        whatsapp_number = os.getenv("STUDIO_WHATSAPP", "+919999999999")
        wa_link = f"https://wa.me/{whatsapp_number.replace('+','')}?text={msg}"
        return {"id": booking_id, "status": "received", "whatsapp": wa_link}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inquiries")
def create_inquiry(inquiry: InquiryRequest):
    if db is None:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        inquiry_id = create_document("inquiry", inquiry.dict())
        return {"id": inquiry_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
