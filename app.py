"""
AI-Powered Hospital Management System — Flask application entry point.

Run:
    python app.py

Make sure MongoDB is running and ai_module/train_model.py has been run at
least once (it ships pre-trained artifacts, so this is optional on a fresh
checkout).
"""
from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from utils.db import init_db

from routes.auth_routes import auth_bp
from routes.patient_routes import patient_bp
from routes.doctor_routes import doctor_bp
from routes.admin_routes import admin_bp
from routes.appointment_routes import appt_bp
from routes.ai_routes import ai_bp
from routes.billing_routes import billing_bp
from routes.lab_routes import lab_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)  # Allow the static frontend (served separately) to call this API

    init_db()

    app.register_blueprint(auth_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(appt_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(lab_bp)

    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({"success": True, "message": "AI-HMS API is running"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.FLASK_DEBUG, port=Config.FLASK_PORT, host="0.0.0.0")
