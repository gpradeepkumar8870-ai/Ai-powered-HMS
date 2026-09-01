"""
AI module routes: symptom-based disease prediction, patient risk triage,
and the rule-based hospital chatbot.
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from datetime import datetime

from utils.db import get_db
from utils.auth_utils import token_required, role_required
from ai_module.symptom_analysis import predict_disease, chatbot_reply, ALL_SYMPTOMS, QUICK_START_SUGGESTIONS

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


@ai_bp.route("/symptoms", methods=["GET"])
@token_required
def get_symptom_list():
    """Returns the canonical symptom checklist for the frontend form."""
    return jsonify({"success": True, "symptoms": ALL_SYMPTOMS})


@ai_bp.route("/predict", methods=["POST"])
@token_required
@role_required("patient")
def predict():
    data = request.get_json(silent=True) or {}
    symptoms = data.get("symptoms", [])
    if not symptoms or not isinstance(symptoms, list):
        return jsonify({"success": False, "message": "Please select at least one symptom"}), 400

    result = predict_disease(symptoms)

    db = get_db()
    record = {
        "patient_id": ObjectId(g.user["user_id"]),
        "symptoms": symptoms,
        "predictions": result["predictions"],
        "risk_level": result["risk_level"],
        "created_at": datetime.utcnow(),
    }
    db.ai_predictions.insert_one(record)

    return jsonify({
        "success": True,
        "predictions": result["predictions"],
        "risk_level": result["risk_level"],
        "disclaimer": "This is an AI-generated suggestion, not a medical diagnosis. "
                       "Please consult the recommended specialist for confirmation.",
    })


@ai_bp.route("/chatbot", methods=["POST"])
@token_required
def chatbot():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "")
    if not message.strip():
        return jsonify({"success": False, "message": "Message cannot be empty"}), 400

    result = chatbot_reply(message)
    return jsonify({"success": True, "reply": result["reply"], "quick_replies": result["quick_replies"]})


@ai_bp.route("/chatbot/suggestions", methods=["GET"])
@token_required
def chatbot_suggestions():
    """Starter quick-reply chips shown when the chat window first opens."""
    return jsonify({"success": True, "suggestions": QUICK_START_SUGGESTIONS})


@ai_bp.route("/emergency-queue", methods=["GET"])
@token_required
@role_required("doctor", "admin")
def emergency_queue():
    """Patients whose most recent AI symptom check was flagged Emergency/High risk today."""
    db = get_db()
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    records = list(db.ai_predictions.find({
        "risk_level": {"$in": ["Emergency", "High"]},
        "created_at": {"$gte": today_start},
    }).sort("created_at", -1))

    for r in records:
        r["_id"] = str(r["_id"])
        patient = db.users.find_one({"_id": r["patient_id"]}, {"name": 1, "phone": 1})
        r["patient_id"] = str(r["patient_id"])
        r["patient_name"] = patient["name"] if patient else "Unknown"
        r["patient_phone"] = patient.get("phone", "") if patient else ""

    return jsonify({"success": True, "queue": records})
