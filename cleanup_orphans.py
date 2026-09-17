"""
One-time cleanup utility: sweeps up any orphaned records left behind from
patient deletions that happened *before* the cascade-delete fix was added
to admin_routes.py. Safe to run any time — it only removes records whose
patient_id no longer matches an existing user, and only reports what it
finds if you run it with --dry-run first.

Usage:
    python cleanup_orphans.py            # actually deletes orphaned records
    python cleanup_orphans.py --dry-run   # just reports what WOULD be deleted
"""
import sys
from utils.db import init_db

DRY_RUN = "--dry-run" in sys.argv


def find_orphaned_patient_ids(db):
    """Returns the set of patient_ids referenced in other collections that
    no longer have a matching user in db.users."""
    referenced_ids = set()
    for collection in ("appointments", "prescriptions", "billing", "ai_predictions", "lab_reports"):
        referenced_ids.update(db[collection].distinct("patient_id"))

    existing_ids = set(db.users.distinct("_id", {"role": "patient"}))
    return referenced_ids - existing_ids


def cleanup():
    db = init_db()
    orphaned_ids = find_orphaned_patient_ids(db)

    if not orphaned_ids:
        print("No orphaned records found. Everything is clean.")
        return

    print(f"Found {len(orphaned_ids)} orphaned patient_id(s) with leftover data:\n")

    total_removed = 0
    for pid in orphaned_ids:
        counts = {
            "appointments": db.appointments.count_documents({"patient_id": pid}),
            "prescriptions": db.prescriptions.count_documents({"patient_id": pid}),
            "billing": db.billing.count_documents({"patient_id": pid}),
            "ai_predictions": db.ai_predictions.count_documents({"patient_id": pid}),
            "lab_reports": db.lab_reports.count_documents({"patient_id": pid}),
        }
        print(f"  patient_id={pid} -> {counts}")
        total_removed += sum(counts.values())

        if not DRY_RUN:
            db.appointments.delete_many({"patient_id": pid})
            db.prescriptions.delete_many({"patient_id": pid})
            db.billing.delete_many({"patient_id": pid})
            db.ai_predictions.delete_many({"patient_id": pid})
            db.lab_reports.delete_many({"patient_id": pid})

    print()
    if DRY_RUN:
        print(f"DRY RUN — no changes made. {total_removed} orphaned record(s) would be deleted.")
        print("Re-run without --dry-run to actually delete them.")
    else:
        print(f"Cleanup complete. Removed {total_removed} orphaned record(s).")


if __name__ == "__main__":
    cleanup()
