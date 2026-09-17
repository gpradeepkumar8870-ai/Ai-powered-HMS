"""
Shared billing helpers used by both the appointment routes and the doctor
prescription route, so a consultation bill is generated exactly once,
automatically, the moment an appointment is marked 'completed'.
"""
from datetime import datetime
from bson import ObjectId


def auto_generate_consultation_bill(db, appointment):
    """
    Creates a pending bill for a completed appointment's consultation fee,
    unless one already exists for that appointment (idempotent — safe to
    call from multiple places without creating duplicate bills).

    `appointment` may be a dict already fetched from the DB, or just an
    ObjectId/str appointment_id (it will be fetched).
    """
    if not isinstance(appointment, dict):
        appointment = db.appointments.find_one({"_id": ObjectId(appointment)})
    if not appointment:
        return None

    existing = db.billing.find_one({"appointment_id": str(appointment["_id"])})
    if existing:
        return existing["_id"]

    doctor = db.users.find_one({"_id": appointment["doctor_id"]}, {"name": 1, "department": 1})
    doctor_name = doctor["name"] if doctor else "Doctor"
    department = appointment.get("department") or (doctor.get("department") if doctor else "General")

    fee = appointment.get("fee", 300)
    bill_doc = {
        "patient_id": appointment["patient_id"],
        "appointment_id": str(appointment["_id"]),
        "items": [
            {"description": f"Consultation — Dr. {doctor_name} ({department})", "amount": fee},
        ],
        "amount": fee,
        "status": "pending",
        "auto_generated": True,
        "created_at": datetime.utcnow(),
    }
    result = db.billing.insert_one(bill_doc)
    return result.inserted_id
