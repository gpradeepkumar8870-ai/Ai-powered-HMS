# AI-Powered Hospital Management System (AI-HMS)

An intelligent, full-stack Hospital Management System that combines conventional
hospital administration (patients, doctors, appointments, billing, lab reports)
with an AI/ML module for symptom-based disease prediction, specialist
recommendation, and patient risk triage.

**Tech Stack**
| Layer        | Technology                                   |
|--------------|-----------------------------------------------|
| Frontend     | HTML5, CSS3, JavaScript, Bootstrap 5           |
| Backend      | Python (Flask)                                 |
| Database     | MongoDB (PyMongo)                              |
| AI / ML      | Scikit-learn, Pandas, NumPy                    |
| Charts       | Chart.js                                       |
| Auth         | JWT (PyJWT) + bcrypt password hashing          |

---

## 1. Project Structure

```
AI-HMS/
├── backend/
│   ├── app.py                     # Flask app entry point
│   ├── config.py                  # Environment-based configuration
│   ├── seed_data.py                # Seeds demo admin/doctor/patient accounts
│   ├── requirements.txt
│   ├── .env.example
│   ├── routes/
│   │   ├── auth_routes.py         # Register / login / profile
│   │   ├── patient_routes.py      # Doctor directory, prescriptions, history
│   │   ├── doctor_routes.py       # Doctor dashboard, patients, prescriptions
│   │   ├── admin_routes.py        # Admin dashboard, doctor/patient mgmt, analytics
│   │   ├── appointment_routes.py  # Booking, listing, status updates
│   │   ├── ai_routes.py           # AI symptom prediction + chatbot + emergency queue
│   │   ├── billing_routes.py      # Bill generation & payment status
│   │   └── lab_routes.py          # Lab report upload/download
│   ├── ai_module/
│   │   ├── train_model.py         # Trains the Random Forest disease-prediction model
│   │   ├── symptom_analysis.py    # Prediction, risk triage, and chatbot logic
│   │   ├── dataset/symptoms_dataset.csv
│   │   └── model/                 # Pre-trained model artifacts (.pkl / .json)
│   └── utils/
│       ├── db.py                  # MongoDB connection + indexes
│       └── auth_utils.py          # Password hashing, JWT issue/verify, decorators
│
└── frontend/
    ├── index.html                 # Landing page
    ├── login.html / register.html
    ├── css/style.css
    ├── js/api.js                  # Central fetch() wrapper for all API calls
    ├── js/auth.js                 # Session/auth guard helpers
    ├── js/chatbot.js              # Floating AI chatbot widget
    ├── patient/                   # Patient portal (dashboard, appointments, etc.)
    ├── doctor/                    # Doctor portal
    └── admin/                     # Admin portal (with Chart.js analytics)
```

---

## 2. Setup Instructions

### Prerequisites
- Python 3.10+
- MongoDB running locally (`mongodb://localhost:27017/`) or a MongoDB Atlas URI
- A modern browser

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate   
or use .\venv\Scripts\Activate.ps1     # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env            # edit values if needed (Mongo URI, JWT secret)

# (Optional — pre-trained model artifacts are already included)
python ai_module/train_model.py

# Seed demo accounts (admin / doctors / patient)
python seed_data.py

# Start the API server
python app.py
```
The API runs at **http://localhost:5000**.

### Frontend Setup
The frontend is static HTML/CSS/JS — no build step required. Serve it with
any static file server, e.g.:
```bash
cd frontend
python -m http.server 8080
```
Then open **http://localhost:8080** in your browser.

> `js/api.js` points to `http://localhost:5000/api` by default — update
> `API_BASE_URL` there if you deploy the backend elsewhere.

### Demo Login Credentials (after running `seed_data.py`)
| Role    | Email                        | Password     |
|---------|-------------------------------|--------------|
| Admin   | admin@aihms.com               | Admin@123    |
| Doctor  | ananya.sharma@aihms.com       | Doctor@123   |
| Patient | patient@aihms.com             | Patient@123  |

---

## 3. Core Modules

### 3.1 Authentication & Roles
- JWT-based stateless authentication (`PyJWT`), passwords hashed with `bcrypt`.
- Three roles: **Admin**, **Doctor**, **Patient** — each with a dedicated
  dashboard and route-level access control (`@token_required`, `@role_required`).
- Doctor self-registrations are created with `status: pending` and require
  admin approval before login is permitted.

### 3.2 AI Module (`ai_module/`)
- **Disease Prediction**: A `RandomForestClassifier` (Scikit-learn) trained on
  a binary symptom-disease matrix (`dataset/symptoms_dataset.csv`) predicts the
  top-3 most likely conditions from a patient's selected symptoms, along with
  a confidence score and the recommended specialist/department.
- **Risk Triage**: A rule-based function flags `Emergency` / `High` /
  `Moderate` / `Low` risk based on symptom severity (e.g. chest pain or
  shortness of breath immediately flags Emergency), surfaced to doctors/admins
  via an **AI-Flagged Emergency Queue**.
- **Chatbot**: A lightweight keyword-matching assistant that helps patients
  with appointment booking, prescriptions, lab reports, billing FAQs, and
  routes them to the symptom checker for clinical questions.
- Retrain any time with `python ai_module/train_model.py` after editing the
  dataset CSV — no code changes required.

### 3.3 Hospital Operations
- **Appointments**: booking with doctor/date/slot clash prevention, status
  lifecycle (`scheduled → confirmed → completed / cancelled / no-show`).
- **Prescriptions**: doctors record diagnosis + structured medicine list
  (name, dosage, frequency, duration); visible to the patient instantly.
- **Lab Reports**: PDF/image upload by admin/doctor, tied to a patient,
  downloadable from the patient's Medical History page.
- **Billing**: itemised bill generation, pending/paid status tracking.
- **Analytics**: Chart.js-powered 7-day appointment trend and department load
  charts on the Admin dashboard and Reports page.

---

## 4. API Overview

| Area          | Example Endpoints                                              |
|---------------|------------------------------------------------------------------|
| Auth          | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Appointments  | `POST /api/appointments`, `GET /api/appointments`, `PATCH /api/appointments/<id>/status` |
| AI            | `POST /api/ai/predict`, `POST /api/ai/chatbot`, `GET /api/ai/emergency-queue` |
| Patients      | `GET /api/patients/doctors`, `GET /api/patients/prescriptions`, `GET /api/patients/medical-history` |
| Doctors       | `GET /api/doctors/dashboard-stats`, `POST /api/doctors/prescriptions` |
| Admin         | `GET /api/admin/dashboard-stats`, `PATCH /api/admin/doctors/<id>/approve` |
| Billing       | `POST /api/billing`, `PATCH /api/billing/<id>/pay`               |
| Lab           | `POST /api/lab/reports`, `GET /api/lab/reports/<filename>`       |

All protected endpoints require an `Authorization: Bearer <token>` header,
obtained from `/api/auth/login`.

---

## 5. Viva / Presentation Notes

- **Why Random Forest?** Handles non-linear symptom-disease relationships
  well, is fast to train/retrain on a small dataset, and naturally outputs
  class probabilities (used as the confidence score) — easy to explain to an
  evaluator compared to a black-box deep learning model.
- **Why MongoDB?** Patient records, prescriptions, and AI predictions are
  naturally document-shaped and vary in structure (e.g. medicines list,
  AI prediction arrays) — a schema-less store avoids rigid migrations while
  still supporting indexes for query performance.
- **Security**: bcrypt password hashing, JWT expiry, role-based route guards,
  and doctor-approval workflow to prevent unauthorized clinical accounts.
- **Extensibility**: the AI module is decoupled (`ai_module/`) so the model
  can be swapped for a more advanced classifier or a real clinical dataset
  without touching the Flask routes or frontend.

---

## 6. Disclaimer
The AI symptom checker provides **suggestions only** and is explicitly labeled
as such in the UI — it is not a substitute for professional medical diagnosis.

---

## 7. One-Time Cleanup Utility

If patients were deleted before the cascade-delete fix was added to
`admin_routes.py`, their appointments/prescriptions/bills/lab reports may
still be sitting in the database as orphaned records. Run this once to sweep
them up:

```bash
cd backend
python cleanup_orphans.py --dry-run   # see what would be deleted, no changes made
python cleanup_orphans.py             # actually deletes the orphaned records
```

Going forward, deleting a patient from Admin → Manage Patients automatically
cascades to all their related records — this script is only needed to clean
up anything left over from before that fix.

---

## 8. Full Reset (Start Completely Fresh)

To wipe **everything** — every user, appointment, prescription, bill, lab
report, and AI symptom check — and start the system from a blank slate:

```bash
cd backend
python reset_database.py
```

It will ask you to type `RESET` to confirm before deleting anything (this
cannot be undone). It also deletes every uploaded lab report file from disk.

Useful variants:
```bash
# Wipe everything, then immediately re-seed the demo admin/doctor/patient accounts
python reset_database.py --keep-seed

# Skip the confirmation prompt (careful — use only in scripts/automation)
python reset_database.py --yes
```

After a plain reset (no `--keep-seed`), the system has **zero** accounts —
you'll need to register a new admin/doctor/patient through the UI, or run
`python seed_data.py` separately to bring back the demo logins.


