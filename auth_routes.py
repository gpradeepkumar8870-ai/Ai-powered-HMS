"""
Authentication routes: register, login, and "who am I" profile check.
Supports three roles: admin, doctor, patient.
"""
from flask import Blueprint, request, jsonify, g
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

from utils.db import get_db
from utils.auth_utils import hash_password, verify_password, generate_token, token_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    required = ["name", "email", "password", "role"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"success": False, "message": f"Missing fields: {', '.join(missing)}"}), 400

    role = data["role"].lower()
    if role not in ("patient", "doctor", "admin"):
        return jsonify({"success": False, "message": "Invalid role"}), 400

    # Doctor/Admin sign-ups typically go through an admin-managed flow in a real
    # deployment; here we allow self-registration for demo/viva convenience but
    # doctors are created as 'pending' until an admin approves them.
    db = get_db()
    if db.users.find_one({"email": data["email"].lower().strip()}):
        return jsonify({"success": False, "message": "An account with this email already exists"}), 409

    user_doc = {
        "name": data["name"].strip(),
        "email": data["email"].lower().strip(),
        "password": hash_password(data["password"]),
        "role": role,
        "phone": data.get("phone", ""),
        "created_at": datetime.utcnow(),
        "status": "pending" if role == "doctor" else "active",
    }

    if role == "patient":
        user_doc.update({
            "age": data.get("age"),
            "gender": data.get("gender"),
            "blood_group": data.get("blood_group"),
            "address": data.get("address", ""),
        })
    elif role == "doctor":
        user_doc.update({
            "department": data.get("department", "General Physician"),
            "qualification": data.get("qualification", ""),
            "experience_years": data.get("experience_years", 0),
            "consultation_fee": data.get("consultation_fee", 300),
        })

    result = db.users.insert_one(user_doc)

    if role == "doctor":
        return jsonify({
            "success": True,
            "message": "Registration submitted. Your account is pending admin approval.",
        }), 201

    token = generate_token(result.inserted_id, role, user_doc["name"])
    return jsonify({
        "success": True,
        "message": "Registration successful",
        "token": token,
        "user": {"id": str(result.inserted_id), "name": user_doc["name"], "role": role, "email": user_doc["email"]},
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").lower().strip()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400

    db = get_db()
    user = db.users.find_one({"email": email})
    if not user or not verify_password(password, user["password"]):
        return jsonify({"success": False, "message": "Invalid email or password"}), 401

    if user["role"] == "doctor" and user.get("status") == "pending":
        return jsonify({"success": False, "message": "Your account is awaiting admin approval"}), 403

    if user.get("status") == "blocked":
        return jsonify({"success": False, "message": "Your account has been blocked. Contact hospital admin."}), 403

    token = generate_token(user["_id"], user["role"], user["name"])
    return jsonify({
        "success": True,
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "role": user["role"],
            "email": user["email"],
        },
    })


@auth_bp.route("/me", methods=["GET"])
@token_required
def me():
    db = get_db()
    try:
        user = db.users.find_one({"_id": ObjectId(g.user["user_id"])}, {"password": 0})
    except InvalidId:
        return jsonify({"success": False, "message": "Invalid user"}), 400
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    user["_id"] = str(user["_id"])
    return jsonify({"success": True, "user": user})
