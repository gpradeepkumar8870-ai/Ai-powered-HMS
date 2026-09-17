"""
Doctor-facing routes: dashboard stats, patient list, and prescription writing.
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime

from utils.db import get_db
from utils.auth_utils import token_required, role_required
from utils.billing_utils import auto_generate_consultation_bill

doctor_bp = Blueprint("doctors", __name__, url_prefix="/api/doctors")


@doctor_bp.route("/dashboard-stats", methods=["GET"])
@token_required
@role_required("doctor")
def dashboard_stats():
    db = get_db()
    doctor_id = ObjectId(g.user["user_id"])
    today = datetime.utcnow().strftime("%Y-%m-%d")

    stats = {
        "todays_appointments": db.appointments.count_documents({"doctor_id": doctor_id, "date": today}),
        "total_patients": len(db.appointments.find({"doctor_id": doctor_id}).distinct("patient_id")),
        "pending_appointments": db.appointments.count_documents({"doctor_id": doctor_id, "status": "scheduled"}),
        "completed_appointments": db.appointments.count_documents({"doctor_id": doctor_id, "status": "completed"}),
    }
    return jsonify({"success": True, "stats": stats})


@doctor_bp.route("/my-patients", methods=["GET"])
@token_required
@role_required("doctor")
def my_patients():
    db = get_db()
    doctor_id = ObjectId(g.user["user_id"])
    patient_ids = db.appointments.find({"doctor_id": doctor_id}).distinct("patient_id")
    patients = list(db.users.find({"_id": {"$in": patient_ids}}, {"password": 0}))
    for p in patients:
        p["_id"] = str(p["_id"])
    return jsonify({"success": True, "patients": patients})


@doctor_bp.route("/prescriptions", methods=["POST"])
@token_required
@role_required("doctor")
def write_prescription():
    data = request.get_json(silent=True) or {}
    required = ["patient_id", "diagnosis", "medicines"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    db = get_db()
    doc = {
        "patient_id": ObjectId(data["patient_id"]),
        "doctor_id": ObjectId(g.user["user_id"]),
        "appointment_id": data.get("appointment_id"),
        "diagnosis": data["diagnosis"],
        "medicines": data["medicines"],   # list of {name, dosage, frequency, duration}
        "notes": data.get("notes", ""),
        "created_at": datetime.utcnow(),
    }
    result = db.prescriptions.insert_one(doc)

    if data.get("appointment_id"):
        db.appointments.update_one({"_id": ObjectId(data["appointment_id"])}, {"$set": {"status": "completed"}})
        auto_generate_consultation_bill(db, data["appointment_id"])

    return jsonify({"success": True, "message": "Prescription saved", "prescription_id": str(result.inserted_id)}), 201
