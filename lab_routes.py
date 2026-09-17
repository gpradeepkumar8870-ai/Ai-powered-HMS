"""
Laboratory routes: upload lab reports (PDF/image) tied to a patient, and
list/download reports.
"""
import os
from flask import Blueprint, request, jsonify, g, send_from_directory
from bson import ObjectId
from datetime import datetime
from werkzeug.utils import secure_filename

from utils.db import get_db
from utils.auth_utils import token_required, role_required
from config import Config

lab_bp = Blueprint("lab", __name__, url_prefix="/api/lab")


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


@lab_bp.route("/reports", methods=["POST"])
@token_required
@role_required("admin", "doctor")
def upload_report():
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file part in the request"}), 400
    file = request.files["file"]
    patient_id = request.form.get("patient_id")
    test_name = request.form.get("test_name", "Lab Test")

    if not patient_id:
        return jsonify({"success": False, "message": "patient_id is required"}), 400
    if file.filename == "" or not _allowed(file.filename):
        return jsonify({"success": False, "message": "Invalid or missing file (allowed: pdf, png, jpg, jpeg)"}), 400

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(f"{patient_id}_{datetime.utcnow().timestamp()}_{file.filename}")
    filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
    file.save(filepath)

    db = get_db()
    doc = {
        "patient_id": ObjectId(patient_id),
        "test_name": test_name,
        "filename": filename,
        "uploaded_by": ObjectId(g.user["user_id"]),
        "created_at": datetime.utcnow(),
    }
    result = db.lab_reports.insert_one(doc)
    return jsonify({"success": True, "message": "Report uploaded", "report_id": str(result.inserted_id)}), 201


@lab_bp.route("/reports/<filename>", methods=["GET"])
@token_required
def download_report(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename, as_attachment=True)


@lab_bp.route("/reports", methods=["GET"])
@token_required
def list_reports():
    db = get_db()
    query = {}
    if g.user["role"] == "patient":
        query["patient_id"] = ObjectId(g.user["user_id"])
    else:
        patient_id = request.args.get("patient_id")
        if patient_id:
            query["patient_id"] = ObjectId(patient_id)

    reports = list(db.lab_reports.find(query).sort("created_at", -1))
    for r in reports:
        r["_id"] = str(r["_id"])
        r["patient_id"] = str(r["patient_id"])
        r["uploaded_by"] = str(r["uploaded_by"])
    return jsonify({"success": True, "reports": reports})
