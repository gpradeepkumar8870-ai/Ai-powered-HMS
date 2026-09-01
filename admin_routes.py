"""
Admin-facing routes: hospital-wide dashboard stats, doctor approval/management,
patient management, department management, and analytics for Chart.js.
"""
import os
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime, timedelta

from utils.db import get_db
from utils.auth_utils import token_required, role_required
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.route("/dashboard-stats", methods=["GET"])
@token_required
@role_required("admin")
def dashboard_stats():
    db = get_db()
    stats = {
        "total_patients": db.users.count_documents({"role": "patient"}),
        "total_doctors": db.users.count_documents({"role": "doctor", "status": "active"}),
        "pending_doctor_approvals": db.users.count_documents({"role": "doctor", "status": "pending"}),
        "total_appointments": db.appointments.count_documents({}),
        "todays_appointments": db.appointments.count_documents({"date": datetime.utcnow().strftime("%Y-%m-%d")}),
        "total_departments": len(db.users.distinct("department", {"role": "doctor", "status": "active"})),
        "revenue_total": sum(b.get("amount", 0) for b in db.billing.find({"status": "paid"})),
        "pending_bills": db.billing.count_documents({"status": "pending"}),
    }
    return jsonify({"success": True, "stats": stats})


@admin_bp.route("/analytics/appointments-trend", methods=["GET"])
@token_required
@role_required("admin")
def appointments_trend():
    """Last 7 days appointment counts, for a Chart.js line/bar chart."""
    db = get_db()
    labels, counts = [], []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        labels.append(day)
        counts.append(db.appointments.count_documents({"date": day}))
    return jsonify({"success": True, "labels": labels, "counts": counts})


@admin_bp.route("/analytics/department-load", methods=["GET"])
@token_required
@role_required("admin")
def department_load():
    """Appointment count grouped by department, for a Chart.js pie/doughnut chart."""
    db = get_db()
    pipeline = [{"$group": {"_id": "$department", "count": {"$sum": 1}}}]
    results = list(db.appointments.aggregate(pipeline))
    return jsonify({
        "success": True,
        "labels": [r["_id"] or "Unassigned" for r in results],
        "counts": [r["count"] for r in results],
    })


@admin_bp.route("/doctors", methods=["GET"])
@token_required
@role_required("admin")
def list_all_doctors():
    db = get_db()
    status = request.args.get("status")
    query = {"role": "doctor"}
    if status:
        query["status"] = status
    doctors = list(db.users.find(query, {"password": 0}))
    for d in doctors:
        d["_id"] = str(d["_id"])
    return jsonify({"success": True, "doctors": doctors})


@admin_bp.route("/doctors/<doctor_id>/approve", methods=["PATCH"])
@token_required
@role_required("admin")
def approve_doctor(doctor_id):
    db = get_db()
    result = db.users.update_one({"_id": ObjectId(doctor_id), "role": "doctor"}, {"$set": {"status": "active"}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Doctor not found"}), 404
    return jsonify({"success": True, "message": "Doctor approved"})


@admin_bp.route("/doctors/<doctor_id>/block", methods=["PATCH"])
@token_required
@role_required("admin")
def block_doctor(doctor_id):
    db = get_db()
    result = db.users.update_one({"_id": ObjectId(doctor_id), "role": "doctor"}, {"$set": {"status": "blocked"}})
    if result.matched_count == 0:
        return jsonify({"success": False, "message": "Doctor not found"}), 404
    return jsonify({"success": True, "message": "Doctor blocked"})


@admin_bp.route("/doctors/<doctor_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def remove_doctor(doctor_id):
    db = get_db()
    result = db.users.delete_one({"_id": ObjectId(doctor_id), "role": "doctor"})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Doctor not found"}), 404
    return jsonify({"success": True, "message": "Doctor removed"})


@admin_bp.route("/patients", methods=["GET"])
@token_required
@role_required("admin")
def list_all_patients():
    db = get_db()
    patients = list(db.users.find({"role": "patient"}, {"password": 0}))
    for p in patients:
        p["_id"] = str(p["_id"])
    return jsonify({"success": True, "patients": patients})


@admin_bp.route("/patients/<patient_id>", methods=["DELETE"])
@token_required
@role_required("admin")
def remove_patient(patient_id):
    db = get_db()
    patient_obj_id = ObjectId(patient_id)

    result = db.users.delete_one({"_id": patient_obj_id, "role": "patient"})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "Patient not found"}), 404

    # Cascade-delete every record tied to this patient so no orphaned data remains.
    db.appointments.delete_many({"patient_id": patient_obj_id})
    db.prescriptions.delete_many({"patient_id": patient_obj_id})
    db.billing.delete_many({"patient_id": patient_obj_id})
    db.ai_predictions.delete_many({"patient_id": patient_obj_id})

    lab_reports = list(db.lab_reports.find({"patient_id": patient_obj_id}))
    for report in lab_reports:
        filepath = os.path.join(Config.UPLOAD_FOLDER, report.get("filename", ""))
        if report.get("filename") and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass  # File already gone or inaccessible — don't block the record deletion
    db.lab_reports.delete_many({"patient_id": patient_obj_id})

    return jsonify({"success": True, "message": "Patient and all associated records removed"})


@admin_bp.route("/departments", methods=["GET"])
@token_required
def list_departments():
    db = get_db()
    departments = db.users.distinct("department", {"role": "doctor", "status": "active"})
    counts = []
    for dept in departments:
        counts.append({
            "name": dept,
            "doctor_count": db.users.count_documents({"role": "doctor", "department": dept, "status": "active"}),
        })
    return jsonify({"success": True, "departments": counts})
