"""
Full reset utility — wipes EVERY collection in the AI-HMS database and
deletes all uploaded lab report files, so you can start completely fresh.

This is destructive and irreversible. It will ask for a typed confirmation
before doing anything, unless you pass --yes to skip the prompt (useful for
scripted/CI resets, but be careful with it).

Usage:
    python reset_database.py            # asks for confirmation first
    python reset_database.py --yes      # skips the confirmation prompt
    python reset_database.py --keep-seed --yes   # wipes then re-seeds demo accounts
"""
import os
import sys
import shutil

from utils.db import init_db
from config import Config

SKIP_CONFIRM = "--yes" in sys.argv
RESEED_AFTER = "--keep-seed" in sys.argv

COLLECTIONS_TO_WIPE = [
    "users",
    "appointments",
    "prescriptions",
    "billing",
    "lab_reports",
    "ai_predictions",
]


def confirm():
    if SKIP_CONFIRM:
        return True
    print("=" * 60)
    print("WARNING: This will PERMANENTLY delete ALL data in the AI-HMS")
    print("database — every patient, doctor, admin, appointment,")
    print("prescription, bill, lab report, and AI symptom check.")
    print("All uploaded lab report files will also be deleted from disk.")
    print("This cannot be undone.")
    print("=" * 60)
    answer = input("Type RESET to confirm, or anything else to cancel: ").strip()
    return answer == "RESET"


def reset():
    if not confirm():
        print("Cancelled. No changes made.")
        return

    db = init_db()

    print("\nWiping collections...")
    for name in COLLECTIONS_TO_WIPE:
        result = db[name].delete_many({})
        print(f"  {name}: removed {result.deleted_count} document(s)")

    print("\nDeleting uploaded lab report files...")
    upload_dir = Config.UPLOAD_FOLDER
    if os.path.isdir(upload_dir):
        removed = 0
        for filename in os.listdir(upload_dir):
            if filename == ".gitkeep":
                continue
            filepath = os.path.join(upload_dir, filename)
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    removed += 1
            except OSError:
                pass
        print(f"  Removed {removed} file(s) from {upload_dir}")
    else:
        print(f"  Upload folder not found at {upload_dir} — nothing to remove.")

    print("\nDatabase reset complete. The system is now completely empty.")

    if RESEED_AFTER:
        print("\nRe-seeding demo accounts (admin / doctors / patient)...")
        import seed_data  # noqa: F401 — running this module seeds on import
    else:
        print("Run 'python seed_data.py' if you'd like demo admin/doctor/patient")
        print("accounts to start with, or register fresh accounts through the UI.")


if __name__ == "__main__":
    reset()
