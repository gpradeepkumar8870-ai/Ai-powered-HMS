"""
Appointment booking & management, usable by patients, doctors, and admins
(each sees a filtered slice depending on role).
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime

from utils.db import get_db
from utils.auth_utils import token_required, role_required
from utils.billing_utils import auto_generate_consultation_bill

appt_bp = Blueprint("appointments", __name__, url_prefix="/api/appointments")


def _serialize(appt):
    appt["_id"] = str(appt["_id"])
    appt["patient_id"] = str(appt["patient_id"])
    appt["doctor_id"] = str(appt["doctor_id"])
    return appt


@appt_bp.route("", methods=["POST"])
@token_required
@role_required("patient")
def book_appointment():
    data = request.get_json(silent=True) or {}
    required = ["doctor_id", "date", "time_slot"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    db = get_db()
    doctor = db.users.find_one({"_id": ObjectId(data["doctor_id"]), "role": "doctor"})
    if not doctor:
        return jsonify({"success": False, "message": "Doctor not found"}), 404

    # Prevent double-booking the same doctor/date/slot
    clash = db.appointments.find_one({
        "doctor_id": ObjectId(data["doctor_id"]),
        "date": data["date"],
        "time_slot": data["time_slot"],
        "status": {"$in": ["scheduled", "confirmed"]},
    })
    if clash:
        return jsonify({"success": False, "message": "This slot is already booked. Please choose another."}), 409

    appt_doc = {
        "patient_id": ObjectId(g.user["user_id"]),
        "doctor_id": ObjectId(data["doctor_id"]),
        "department": doctor.get("department", "General Physician"),
        "date": data["date"],
        "time_slot": data["time_slot"],
        "reason": data.get("reason", ""),
        "status": "scheduled",
        "fee": doctor.get("consultation_fee", 300),
        "created_at": datetime.utcnow(),
    }
    result = db.appointments.insert_one(appt_doc)
    appt_doc["_id"] = result.inserted_id
    return jsonify({"success": True, "message": "Appointment booked successfully", "appointment": _serialize(appt_doc)}), 201


@appt_bp.route("", methods=["GET"])
@token_required
def list_appointments():
    db = get_db()
    role, uid = g.user["role"], g.user["user_id"]

    query = {}
    if role == "patient":
        query["patient_id"] = ObjectId(uid)
    elif role == "doctor":
        query["doctor_id"] = ObjectId(uid)
    # admin sees all

    status = request.args.get("status")
    if status:
        query["status"] = status

    appts = list(db.appointments.find(query).sort("date", 1))

    # Enrich with patient/doctor names for display convenience
    for a in appts:
        patient = db.users.find_one({"_id": a["patient_id"]}, {"name": 1})
        doctor = db.users.find_one({"_id": a["doctor_id"]}, {"name": 1, "department": 1})
        a["patient_name"] = patient["name"] if patient else "Unknown"
        a["doctor_name"] = doctor["name"] if doctor else "Unknown"

    return jsonify({"success": True, "appointments": [_serialize(a) for a in appts]})


@appt_bp.route("/<appt_id>/status", methods=["PATCH"])
@token_required
@role_required("doctor", "admin")
def update_status(appt_id):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("confirmed", "completed", "cancelled", "no-show"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    db = get_db()
    appt = db.appointments.find_one({"_id": ObjectId(appt_id)})
    if not appt:
        return jsonify({"success": False, "message": "Appointment not found"}), 404

    db.appointments.update_one({"_id": ObjectId(appt_id)}, {"$set": {"status": new_status}})

    if new_status == "completed":
        appt["status"] = "completed"
        auto_generate_consultation_bill(db, appt)

    return jsonify({"success": True, "message": "Appointment status updated"})


@appt_bp.route("/<appt_id>", methods=["DELETE"])
@token_required
def cancel_appointment(appt_id):
    db = get_db()
    appt = db.appointments.find_one({"_id": ObjectId(appt_id)})
    if not appt:
        return jsonify({"success": False, "message": "Appointment not found"}), 404

    if g.user["role"] == "patient" and str(appt["patient_id"]) != g.user["user_id"]:
        return jsonify({"success": False, "message": "You can only cancel your own appointments"}), 403

    db.appointments.update_one({"_id": ObjectId(appt_id)}, {"$set": {"status": "cancelled"}})
    return jsonify({"success": True, "message": "Appointment cancelled"})
