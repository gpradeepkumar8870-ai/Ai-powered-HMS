"""
Patient-facing routes: profile, doctor directory, prescriptions,
medical history, and lab report listing.
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId

from utils.db import get_db
from utils.auth_utils import token_required, role_required

patient_bp = Blueprint("patients", __name__, url_prefix="/api/patients")


@patient_bp.route("/doctors", methods=["GET"])
@token_required
def list_doctors():
    """Public directory of approved, active doctors (any logged-in role can view)."""
    db = get_db()
    query = {"role": "doctor", "status": "active"}
    department = request.args.get("department")
    if department:
        query["department"] = department

    doctors = list(db.users.find(query, {"password": 0}))
    for d in doctors:
        d["_id"] = str(d["_id"])
    return jsonify({"success": True, "doctors": doctors})


@patient_bp.route("/prescriptions", methods=["GET"])
@token_required
@role_required("patient")
def my_prescriptions():
    db = get_db()
    prescriptions = list(db.prescriptions.find({"patient_id": ObjectId(g.user["user_id"])}).sort("created_at", -1))
    for p in prescriptions:
        p["_id"] = str(p["_id"])
        p["patient_id"] = str(p["patient_id"])
        p["doctor_id"] = str(p["doctor_id"])
        doctor = db.users.find_one({"_id": ObjectId(p["doctor_id"])}, {"name": 1, "department": 1})
        p["doctor_name"] = doctor["name"] if doctor else "Unknown"
    return jsonify({"success": True, "prescriptions": prescriptions})


@patient_bp.route("/medical-history", methods=["GET"])
@token_required
def medical_history():
    """Patients see their own; doctors/admin can pass ?patient_id= to view a specific patient."""
    db = get_db()
    if g.user["role"] == "patient":
        patient_id = g.user["user_id"]
    else:
        patient_id = request.args.get("patient_id")
        if not patient_id:
            return jsonify({"success": False, "message": "patient_id is required"}), 400

    prescriptions = list(db.prescriptions.find({"patient_id": ObjectId(patient_id)}).sort("created_at", -1))
    lab_reports = list(db.lab_reports.find({"patient_id": ObjectId(patient_id)}).sort("created_at", -1))
    appointments = list(db.appointments.find({"patient_id": ObjectId(patient_id), "status": "completed"}).sort("date", -1))
    ai_checks = list(db.ai_predictions.find({"patient_id": ObjectId(patient_id)}).sort("created_at", -1).limit(10))

    for group in (prescriptions, lab_reports, appointments, ai_checks):
        for doc in group:
            doc["_id"] = str(doc["_id"])
            doc["patient_id"] = str(doc["patient_id"])
            if "doctor_id" in doc:
                doc["doctor_id"] = str(doc["doctor_id"])

    return jsonify({
        "success": True,
        "prescriptions": prescriptions,
        "lab_reports": lab_reports,
        "past_appointments": appointments,
        "ai_symptom_checks": ai_checks,
    })


@patient_bp.route("/profile", methods=["PUT"])
@token_required
@role_required("patient")
def update_profile():
    data = request.get_json(silent=True) or {}
    allowed_fields = {"name", "phone", "age", "gender", "blood_group", "address"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    if not updates:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400

    db = get_db()
    db.users.update_one({"_id": ObjectId(g.user["user_id"])}, {"$set": updates})
    return jsonify({"success": True, "message": "Profile updated"})
