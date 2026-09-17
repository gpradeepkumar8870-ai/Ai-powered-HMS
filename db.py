"""
MongoDB connection helper.
A single PyMongo client is created and reused across the whole app
(Flask app factory calls init_db() once at startup).
"""
from pymongo import MongoClient, ASCENDING
from config import Config

_client = None
_db = None


def init_db():
    """Create the Mongo client/db and make sure useful indexes exist."""
    global _client, _db
    _client = MongoClient(Config.MONGO_URI)
    _db = _client[Config.DB_NAME]

    _db.users.create_index([("email", ASCENDING)], unique=True)
    _db.appointments.create_index([("patient_id", ASCENDING)])
    _db.appointments.create_index([("doctor_id", ASCENDING)])
    _db.prescriptions.create_index([("patient_id", ASCENDING)])
    _db.lab_reports.create_index([("patient_id", ASCENDING)])
    _db.billing.create_index([("patient_id", ASCENDING)])

    return _db


def get_db():
    """Return the active database handle (call init_db() first)."""
    if _db is None:
        return init_db()
    return _db
