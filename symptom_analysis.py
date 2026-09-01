"""
Loads the trained Random Forest model and exposes:
  - predict_disease(selected_symptoms) -> top-3 predictions + recommended specialist
  - assess_risk_level(...)             -> rule-based emergency triage score
  - chatbot_reply(message)             -> lightweight rule-based assistant

If the trained model artifacts are missing (i.e. train_model.py has not been
run yet), the module transparently falls back to a rule-based symptom
matcher so the API never breaks a fresh checkout.
"""
import os
import json
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "model")
DATASET_PATH = os.path.join(BASE_DIR, "dataset", "symptoms_dataset.csv")

_model = None
_encoder = None
_symptom_columns = None
_specialist_map = None


def _load_artifacts():
    global _model, _encoder, _symptom_columns, _specialist_map
    try:
        _model = joblib.load(os.path.join(MODEL_DIR, "disease_model.pkl"))
        _encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
        with open(os.path.join(MODEL_DIR, "symptom_columns.json")) as f:
            _symptom_columns = json.load(f)
        with open(os.path.join(MODEL_DIR, "disease_specialist_map.json")) as f:
            _specialist_map = json.load(f)
        return True
    except FileNotFoundError:
        return False


_MODEL_READY = _load_artifacts()

# Canonical symptom list shown on the frontend checkbox form
ALL_SYMPTOMS = [
    "fever", "cough", "headache", "fatigue", "sore_throat", "shortness_of_breath",
    "chest_pain", "nausea", "vomiting", "abdominal_pain", "diarrhea", "joint_pain",
    "rash", "dizziness", "loss_of_appetite", "runny_nose", "body_ache",
]

# Symptom combinations treated as red-flag / emergency indicators
EMERGENCY_SYMPTOMS = {"chest_pain", "shortness_of_breath"}


def predict_disease(selected_symptoms):
    """
    selected_symptoms: list[str] of symptom keys present in ALL_SYMPTOMS.
    Returns: {"predictions": [{"disease": ..., "confidence": ..., "specialist": ...}], "risk_level": ...}
    """
    selected = set(s.strip().lower().replace(" ", "_") for s in selected_symptoms)

    if _MODEL_READY:
        vector = [[1 if col in selected else 0 for col in _symptom_columns]]
        probabilities = _model.predict_proba(vector)[0]
        top_indices = probabilities.argsort()[::-1][:3]

        predictions = []
        for idx in top_indices:
            if probabilities[idx] <= 0:
                continue
            disease_name = _encoder.inverse_transform([idx])[0]
            predictions.append({
                "disease": disease_name,
                "confidence": round(float(probabilities[idx]) * 100, 1),
                "specialist": _specialist_map.get(disease_name, "General Physician"),
            })

        if not predictions:
            predictions = [{"disease": "Unable to determine — insufficient symptoms",
                             "confidence": 0.0, "specialist": "General Physician"}]
    else:
        # Fallback rule-based overlap matcher (used only if the model hasn't been trained yet)
        predictions = _rule_based_fallback(selected)

    risk_level = assess_risk_level(selected)

    return {"predictions": predictions, "risk_level": risk_level}


def _rule_based_fallback(selected):
    import csv
    scores = {}
    specialists = {}
    with open(DATASET_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            disease = row["disease"]
            specialists[disease] = row["specialist"]
            row_symptoms = {k for k, v in row.items() if k not in ("disease", "specialist") and v == "1"}
            overlap = len(row_symptoms & selected)
            if overlap:
                scores[disease] = max(scores.get(disease, 0), overlap)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    total = sum(s for _, s in ranked) or 1
    return [
        {"disease": d, "confidence": round(s / total * 100, 1), "specialist": specialists.get(d, "General Physician")}
        for d, s in ranked
    ] or [{"disease": "Unable to determine — insufficient symptoms", "confidence": 0.0, "specialist": "General Physician"}]


def assess_risk_level(selected_symptoms):
    """Simple rule-based triage: returns 'Emergency' | 'High' | 'Moderate' | 'Low'."""
    selected = set(selected_symptoms)
    if selected & EMERGENCY_SYMPTOMS:
        return "Emergency"
    if len(selected) >= 6:
        return "High"
    if len(selected) >= 3:
        return "Moderate"
    return "Low"


# --------------------------------------------------------------------------
# Rule-based hospital chatbot — keyword/intent matching with scored ranking
# and contextual quick-reply suggestions for a more guided conversation.
# --------------------------------------------------------------------------

# Shown as starter chips the moment the chat window opens
QUICK_START_SUGGESTIONS = [
    "Book an appointment",
    "Check my symptoms",
    "View my bills",
    "Talk to a doctor",
]

_INTENTS = [
    {
        "id": "greeting",
        "keywords": ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"],
        "reply": "Hello! I'm the AI-HMS assistant 🤖. I can help with appointments, prescriptions, "
                 "lab reports, billing, or general symptom guidance. What do you need today?",
        "quick_replies": ["Book an appointment", "Check my symptoms", "View my bills", "Contact reception"],
    },
    {
        "id": "book_appointment",
        "keywords": ["book", "schedule appointment", "new appointment", "see a doctor", "consult"],
        "reply": "Sure! Go to Dashboard → Appointments → Book New. Pick a department, choose a doctor, "
                 "and select a free date/time slot. You'll see the consultation fee before confirming.",
        "quick_replies": ["Which departments are available?", "Cancel an appointment", "View my bills"],
    },
    {
        "id": "reschedule_cancel",
        "keywords": ["cancel appointment", "reschedule", "change my appointment", "cancel my booking"],
        "reply": "You can cancel any upcoming appointment from Dashboard → Appointments — look for the "
                 "'Cancel' button next to it. To reschedule, cancel the old slot and book a new one "
                 "at your preferred time.",
        "quick_replies": ["Book an appointment"],
    },
    {
        "id": "departments",
        "keywords": ["department", "specialist", "cardiologist", "dermatologist", "which doctor",
                     "orthopedic", "neurologist", "gastroenterologist", "pulmonologist", "ent"],
        "reply": "We have General Physician, Cardiologist, Dermatologist, Pulmonologist, Neurologist, "
                 "Gastroenterologist, Orthopedic, ENT Specialist, and Endocrinologist departments. "
                 "Not sure which one you need? Try the AI Symptom Checker — it'll recommend one for you.",
        "quick_replies": ["Check my symptoms", "Book an appointment"],
    },
    {
        "id": "billing",
        "keywords": ["fee", "cost", "bill", "payment", "price", "invoice", "how much", "charge"],
        "reply": "Consultation fees vary by doctor and are shown before you confirm a booking. "
                 "All your bills — pending and paid — are listed under Dashboard → Billing, where "
                 "you can also pay a pending bill directly.",
        "quick_replies": ["View my bills", "Book an appointment"],
    },
    {
        "id": "lab_reports",
        "keywords": ["report", "lab", "test result", "blood test", "scan"],
        "reply": "Lab reports are uploaded by our laboratory team and appear under "
                 "Dashboard → Medical History → Lab Reports as soon as they're ready, with a "
                 "download link for each one.",
        "quick_replies": ["View my bills", "Talk to a doctor"],
    },
    {
        "id": "prescription",
        "keywords": ["prescription", "medicine", "medication", "dosage", "drug"],
        "reply": "Your prescriptions — diagnosis, medicines, dosage, and duration — are listed under "
                 "Dashboard → Prescriptions, updated right after your doctor saves them.",
        "quick_replies": ["Check my symptoms", "Book an appointment"],
    },
    {
        "id": "emergency",
        "keywords": ["emergency", "urgent", "chest pain", "can't breathe", "cannot breathe",
                     "severe bleeding", "unconscious", "heart attack", "stroke"],
        "reply": "⚠️ If this is a medical emergency, please call your local emergency number or go to "
                 "the nearest emergency room right now. This chatbot can't provide emergency care — "
                 "your safety comes first.",
        "quick_replies": [],
    },
    {
        "id": "symptom_checker",
        "keywords": ["symptom", "sick", "unwell", "fever", "pain", "not feeling well", "cough", "headache"],
        "reply": "I'm sorry to hear that. Open the AI Symptom Checker from your dashboard — select what "
                 "you're experiencing and it will suggest possible conditions, a risk level, and the "
                 "right specialist to consult.",
        "quick_replies": ["Check my symptoms", "Book an appointment"],
    },
    {
        "id": "hours",
        "keywords": ["timing", "opd hours", "visiting hours", "open", "working hours", "what time"],
        "reply": "OPD consultation slots run 9:00 AM – 5:00 PM (with a lunch break 12:00–2:00 PM), "
                 "Monday to Saturday. Exact available slots for a doctor are shown when you book.",
        "quick_replies": ["Book an appointment"],
    },
    {
        "id": "talk_to_doctor",
        "keywords": ["talk to a doctor", "talk to doctor", "speak to doctor", "human", "real person",
                     "contact reception", "agent", "talk to someone"],
        "reply": "I can point you in the right direction, but for anything beyond this chat, please "
                 "book an appointment to consult a doctor directly, or contact hospital reception "
                 "during OPD hours for anything administrative.",
        "quick_replies": ["Book an appointment"],
    },
    {
        "id": "profile_account",
        "keywords": ["update profile", "change password", "forgot password", "my account", "edit details"],
        "reply": "You can update your name, phone, age, gender, blood group, and address from your "
                 "profile settings. Password reset isn't self-service yet in this version — please "
                 "contact hospital admin for account issues.",
        "quick_replies": [],
    },
    {
        "id": "thanks",
        "keywords": ["thank", "thanks", "thank you", "appreciate it"],
        "reply": "You're very welcome! Let me know if there's anything else I can help with. 🙂",
        "quick_replies": ["Book an appointment", "Check my symptoms"],
    },
    {
        "id": "goodbye",
        "keywords": ["bye", "goodbye", "see you", "that's all"],
        "reply": "Take care, and feel better soon! Come back anytime you need help. 👋",
        "quick_replies": [],
    },
    {
        "id": "capabilities",
        "keywords": ["what can you do", "who are you", "help me", "what is this"],
        "reply": "I'm the AI-HMS assistant. I can help you book or cancel appointments, check symptoms "
                 "with our AI model, find prescriptions, view lab reports, and answer billing questions "
                 "— all without leaving the chat.",
        "quick_replies": ["Book an appointment", "Check my symptoms", "View my bills"],
    },
]

_DEFAULT_REPLY = {
    "reply": "I'm not totally sure I follow — I can help with booking appointments, viewing "
             "prescriptions, checking lab reports, billing questions, or general symptom guidance. "
             "Could you rephrase, or pick one of the options below?",
    "quick_replies": ["Book an appointment", "Check my symptoms", "View my bills", "Talk to a doctor"],
}


def chatbot_reply(message: str) -> dict:
    """Returns {'reply': str, 'quick_replies': list[str]} using scored keyword matching."""
    text = (message or "").lower().strip()
    if not text:
        return _DEFAULT_REPLY

    best_intent, best_score = None, 0
    for intent in _INTENTS:
        score = sum(1 for kw in intent["keywords"] if kw in text)
        if score > best_score:
            best_score, best_intent = score, intent

    if best_intent:
        return {"reply": best_intent["reply"], "quick_replies": best_intent["quick_replies"]}
    return _DEFAULT_REPLY
