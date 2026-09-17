"""
Billing routes: generate & list bills, mark as paid.
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime

from utils.db import get_db
from utils.auth_utils import token_required, role_required

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


@billing_bp.route("", methods=["POST"])
@token_required
@role_required("admin", "doctor")
def create_bill():
    data = request.get_json(silent=True) or {}
    required = ["patient_id", "items"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    items = data["items"]  # list of {description, amount}
    total = sum(float(i.get("amount", 0)) for i in items)

    db = get_db()
    doc = {
        "patient_id": ObjectId(data["patient_id"]),
        "appointment_id": data.get("appointment_id"),
        "items": items,
        "amount": total,
        "status": "pending",
        "created_at": datetime.utcnow(),
    }
    result = db.billing.insert_one(doc)
    return jsonify({"success": True, "message": "Bill generated", "bill_id": str(result.inserted_id), "amount": total}), 201


@billing_bp.route("", methods=["GET"])
@token_required
def list_bills():
    db = get_db()
    query = {}

    if g.user["role"] == "patient":
        query["patient_id"] = ObjectId(g.user["user_id"])
    elif g.user["role"] == "doctor":
        # Doctors only see billing for patients they've actually treated,
        # scoped via that doctor's appointment history.
        doctor_id = ObjectId(g.user["user_id"])
        patient_ids = db.appointments.find({"doctor_id": doctor_id}).distinct("patient_id")
        query["patient_id"] = {"$in": patient_ids}
    # admin sees all bills (no filter)

    status = request.args.get("status")
    if status:
        query["status"] = status

    bills = list(db.billing.find(query).sort("created_at", -1))
    for b in bills:
        b["_id"] = str(b["_id"])
        b["patient_id"] = str(b["patient_id"])
        patient = db.users.find_one({"_id": ObjectId(b["patient_id"])}, {"name": 1})
        b["patient_name"] = patient["name"] if patient else "Unknown"
    return jsonify({"success": True, "bills": bills})


@billing_bp.route("/<bill_id>/pay", methods=["PATCH"])
@token_required
def mark_paid(bill_id):
    db = get_db()
    bill = db.billing.find_one({"_id": ObjectId(bill_id)})
    if not bill:
        return jsonify({"success": False, "message": "Bill not found"}), 404

    if g.user["role"] == "patient" and str(bill["patient_id"]) != g.user["user_id"]:
        return jsonify({"success": False, "message": "You can only pay your own bills"}), 403
    if g.user["role"] == "doctor":
        return jsonify({"success": False, "message": "Doctors cannot mark bills as paid"}), 403

    db.billing.update_one(
        {"_id": ObjectId(bill_id)},
        {"$set": {"status": "paid", "paid_at": datetime.utcnow()}},
    )
    return jsonify({"success": True, "message": "Bill marked as paid"})
