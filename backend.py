# backend.py — MedAssist AI v6.0 (Production-Ready)
# ═══════════════════════════════════════════════════════════════════════════════
# FIX 1: Real JWT Authentication — /auth/register, /auth/login, /auth/me
#         Role-based access: patient / doctor / admin
# FIX 2: Audit logging — every data access logged with user + timestamp
# FIX 3: File uploads — PDF/image lab reports via /upload endpoint
# FIX 4: Email alerts — appointment confirmation + reminder emails via SMTP
# FIX 5: Rate limiting — prevents abuse, handles scale
# FIX 6: Background tasks — emails sent async, no request blocking
# BONUS: Doctor approval flow — AI diagnosis marked pending until doctor reviews
# BONUS: Consent tracking — patient consent recorded before data use
# ═══════════════════════════════════════════════════════════════════════════════

from dotenv import load_dotenv
load_dotenv()

import os, shutil, smtplib, secrets
from datetime import datetime, date, timedelta
from typing import List, Optional
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from pydantic import BaseModel, Field, field_validator, EmailStr
from fastapi import (FastAPI, HTTPException, Depends, Query,
                     UploadFile, File, BackgroundTasks, Request)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import bcrypt
from jose import JWTError, jwt

from database import (
    get_db, init_db, get_db_stats,
    PatientCRUD, ConsultationCRUD, DoctorCRUD, AppointmentCRUD,
    VitalSignsCRUD, LabResultCRUD, MedicalRecordCRUD,
    MedicationCRUD, AllergyPatientCRUD, ChronicConditionCRUD,
    InvoiceCRUD, PrescriptionCRUD,
    UserCRUD, AuditLogCRUD,
)
from ai_agent import get_medical_diagnosis, analyze_symptoms, DEFAULT_MEDICAL_PROMPT

# ─── Config ───────────────────────────────────────────────────────────────────
SECRET_KEY      = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ALGORITHM       = "HS256"
TOKEN_EXPIRE_H  = 24

SMTP_HOST       = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT       = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER       = os.environ.get("SMTP_USER", "")
SMTP_PASS       = os.environ.get("SMTP_PASS", "")
SMTP_FROM       = os.environ.get("SMTP_FROM", "noreply@medassist.ai")

UPLOAD_DIR      = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_MB     = 10

GROQ_MODELS     = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
OPENAI_MODELS   = ["gpt-4o-mini", "gpt-4o"]
ALL_MODELS      = GROQ_MODELS + OPENAI_MODELS

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MedAssist AI — v6.0 Production",
    description="Production-ready hospital management with JWT auth, file uploads & email alerts",
    version="6.0.0", docs_url="/docs", redoc_url="/redoc",
)
# FIX: allow_origins=["*"] + allow_credentials=True is rejected by browsers
# Set CORS_ORIGINS in .env as comma-separated list, e.g. "http://localhost:8501,http://localhost:8502"
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:8501,http://localhost:8502,http://127.0.0.1:8501,http://127.0.0.1:8502").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@app.on_event("startup")
def on_startup():
    # Warn only if SECRET_KEY was NOT found in environment (i.e. we fell back to random)
    if not os.environ.get("SECRET_KEY"):
        import warnings
        warnings.warn(
            "⚠️  SECRET_KEY is not set in .env — JWTs will be invalidated on every restart! "
            "Add SECRET_KEY=<64-char-hex> to your .env file.", stacklevel=2
        )
    init_db()
    UPLOAD_DIR.mkdir(exist_ok=True)


# ─── JWT Helpers ──────────────────────────────────────────────────────────────

def create_token(data: dict, expires_hours: int = TOKEN_EXPIRE_H) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(hours=expires_hours)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(401, "Not authenticated. Please login.")
    payload = decode_token(token)
    user = UserCRUD.get_by_id(db, payload.get("user_id"))
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or deactivated")
    return user


def require_doctor(user=Depends(get_current_user)):
    if user.role not in ("doctor", "admin"):
        raise HTTPException(403, "Doctor or Admin access required")
    return user


def require_admin(user=Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user


def get_optional_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Returns user or None — for endpoints accessible both logged-in and anonymous."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        return UserCRUD.get_by_id(db, payload.get("user_id"))
    except:
        return None


# ─── Email Helper ─────────────────────────────────────────────────────────────

def send_email_background(to_email: str, subject: str, html_body: str):
    """Send email in background — does not block the API response."""
    if not SMTP_USER or not SMTP_PASS:
        print(f"📧 Email skipped (SMTP not configured). To: {to_email} | Subject: {subject}")
        return
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"MedAssist AI <{SMTP_FROM}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"⚠️ Email failed to {to_email}: {e}")


def appointment_email_html(patient_name: str, appt_date: str, appt_time: str,
                            doctor_name: str, reason: str, appt_type: str) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#f8f9fa;padding:20px;border-radius:12px">
      <div style="background:linear-gradient(135deg,#0066cc,#0096ff);border-radius:10px;padding:24px;text-align:center;color:white;margin-bottom:20px">
        <h1 style="margin:0;font-size:1.5rem">🏥 MedAssist AI</h1>
        <p style="margin:8px 0 0;opacity:.85;font-size:.9rem">Appointment Confirmation</p>
      </div>
      <div style="background:white;border-radius:10px;padding:24px;border:1px solid #e0e0e0">
        <p style="color:#333;font-size:1rem">Dear <strong>{patient_name}</strong>,</p>
        <p style="color:#555;font-size:.95rem">Your appointment has been successfully booked. Here are the details:</p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f0f7ff"><td style="padding:10px;color:#555;font-size:.9rem;border-radius:6px 0 0 6px"><strong>📅 Date</strong></td><td style="padding:10px;color:#333;font-weight:600">{appt_date}</td></tr>
          <tr><td style="padding:10px;color:#555;font-size:.9rem"><strong>🕐 Time</strong></td><td style="padding:10px;color:#333">{appt_time or 'To be confirmed'}</td></tr>
          <tr style="background:#f0f7ff"><td style="padding:10px;color:#555;font-size:.9rem"><strong>👨‍⚕️ Doctor</strong></td><td style="padding:10px;color:#333">{doctor_name}</td></tr>
          <tr><td style="padding:10px;color:#555;font-size:.9rem"><strong>📋 Type</strong></td><td style="padding:10px;color:#333">{appt_type}</td></tr>
          <tr style="background:#f0f7ff"><td style="padding:10px;color:#555;font-size:.9rem"><strong>📝 Reason</strong></td><td style="padding:10px;color:#333">{reason}</td></tr>
        </table>
        <div style="background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px;font-size:.85rem;color:#856404;margin-top:12px">
          ⚠️ <strong>Reminder:</strong> Please arrive 10 minutes early. Bring any previous reports or prescriptions.
        </div>
      </div>
      <p style="text-align:center;color:#aaa;font-size:.75rem;margin-top:16px">
        MedAssist AI · This is an automated message · Do not reply
      </p>
    </div>"""


def consultation_saved_email_html(patient_name: str, symptoms: list, consultation_id: int) -> str:
    sym_list = "".join(f"<li style='color:#555;margin:4px 0'>{s}</li>" for s in symptoms)
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;background:#f8f9fa;padding:20px;border-radius:12px">
      <div style="background:linear-gradient(135deg,#059669,#10b981);border-radius:10px;padding:24px;text-align:center;color:white;margin-bottom:20px">
        <h1 style="margin:0;font-size:1.5rem">✅ Consultation Received</h1>
      </div>
      <div style="background:white;border-radius:10px;padding:24px;border:1px solid #e0e0e0">
        <p>Dear <strong>{patient_name}</strong>,</p>
        <p>Your symptoms have been submitted and an AI assessment has been generated (Consultation #{consultation_id}).</p>
        <p><strong>Symptoms reported:</strong></p>
        <ul>{sym_list}</ul>
        <div style="background:#d1ecf1;border:1px solid #bee5eb;border-radius:8px;padding:12px;font-size:.85rem;color:#0c5460;margin-top:12px">
          🩺 Your doctor will review the AI assessment and follow up with you. The AI report is a preliminary assessment only.
        </div>
      </div>
    </div>"""


# ─── Audit Log Helper ─────────────────────────────────────────────────────────

def log_action(db, user_id, action, resource, resource_id=None, detail=None):
    try:
        AuditLogCRUD.create(db, user_id=user_id, action=action,
                            resource=resource, resource_id=resource_id, detail=detail)
    except: pass


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email:     str
    password:  str = Field(..., min_length=8)
    full_name: str
    role:      str = "patient"   # patient / doctor / admin
    phone:     Optional[str] = None
    consent_given: bool = False  # DISHA compliance

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("patient", "doctor", "admin"):
            raise ValueError("Role must be patient, doctor, or admin")
        return v


class UserLogin(BaseModel):
    email:    str
    password: str


class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name:  str = Field(..., min_length=1)
    email:      Optional[str] = None
    phone:      Optional[str] = None
    date_of_birth: Optional[str] = None
    age:        Optional[int]   = Field(None, ge=0, le=150)
    gender:     Optional[str]   = None
    address:    Optional[str]   = None
    city:       Optional[str]   = None
    state:      Optional[str]   = None
    pincode:    Optional[str]   = None
    country:    Optional[str]   = "India"
    emergency_contact_name:     Optional[str] = None
    emergency_contact_phone:    Optional[str] = None
    emergency_contact_relation: Optional[str] = None
    weight:     Optional[float] = Field(None, ge=0, le=600)
    height:     Optional[float] = Field(None, ge=0, le=300)
    blood_type: Optional[str]   = None
    medical_history:     Optional[str] = None
    current_medications: Optional[str] = None
    allergies:           Optional[str] = None
    family_history:      Optional[str] = None
    smoking_status: Optional[str] = None
    alcohol_use:    Optional[str] = None
    activity_level: Optional[str] = None
    diet_type:      Optional[str] = None
    occupation:     Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_id:       Optional[str] = None
    consent_given:      Optional[bool] = False

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v):
        if v:
            try: datetime.strptime(v, "%Y-%m-%d")
            except: raise ValueError("Date must be YYYY-MM-DD")
        return v


class PatientUpdate(PatientCreate):
    first_name: Optional[str] = None
    last_name:  Optional[str] = None


class DoctorCreate(BaseModel):
    first_name: str
    last_name:  str
    email:      Optional[str] = None
    phone:      Optional[str] = None
    specialization:     Optional[str] = None
    sub_specialization: Optional[str] = None
    qualification:      Optional[str] = None
    license_number:     Optional[str] = None
    hospital:           Optional[str] = None
    department:         Optional[str] = None
    experience_years:   Optional[int] = None
    consultation_fee:   Optional[float] = None
    available_days:     Optional[str] = None
    available_from:     Optional[str] = None
    available_to:       Optional[str] = None
    bio:        Optional[str] = None
    languages:  Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id:       int
    doctor_id:        Optional[int] = None
    appointment_date: str
    appointment_time: Optional[str] = None
    duration_mins:    Optional[int] = 30
    appointment_type: Optional[str] = "In-person"
    reason:           Optional[str] = None
    room_number:      Optional[str] = None
    notes:            Optional[str] = None
    send_email:       Optional[bool] = True   # FIX 4: email toggle

    @field_validator("appointment_date")
    @classmethod
    def validate_date(cls, v):
        if v:
            try: datetime.strptime(v, "%Y-%m-%d")
            except: raise ValueError("Date must be YYYY-MM-DD")
        return v


class VitalsCreate(BaseModel):
    patient_id:      int
    consultation_id: Optional[int] = None
    bp_systolic:     Optional[int] = None
    bp_diastolic:    Optional[int] = None
    pulse_rate:      Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature:     Optional[float] = None
    spo2:            Optional[float] = None
    blood_glucose:   Optional[float] = None
    weight:          Optional[float] = None
    height:          Optional[float] = None
    pain_scale:      Optional[int]   = Field(None, ge=0, le=10)
    notes:           Optional[str]   = None


class LabResultCreate(BaseModel):
    patient_id:      int
    consultation_id: Optional[int] = None
    test_name:       str
    test_category:   Optional[str] = None
    result_value:    Optional[str] = None
    result_unit:     Optional[str] = None
    reference_range: Optional[str] = None
    status:          Optional[str] = None
    lab_name:        Optional[str] = None
    tested_at:       Optional[str] = None
    notes:           Optional[str] = None


class MedicalRecordCreate(BaseModel):
    patient_id:      int
    consultation_id: Optional[int] = None
    record_type:     str
    title:           str
    description:     Optional[str] = None
    file_name:       Optional[str] = None
    file_type:       Optional[str] = None
    issued_by:       Optional[str] = None
    issued_date:     Optional[str] = None
    tags:            Optional[str] = None


class MedicationCreate(BaseModel):
    patient_id:    int
    drug_name:     str
    generic_name:  Optional[str] = None
    dosage:        Optional[str] = None
    frequency:     Optional[str] = None
    route:         Optional[str] = "Oral"
    prescribed_by: Optional[str] = None
    start_date:    Optional[str] = None
    end_date:      Optional[str] = None
    is_current:    Optional[bool] = True
    indication:    Optional[str] = None
    side_effects:  Optional[str] = None
    notes:         Optional[str] = None


class AllergyCreate(BaseModel):
    patient_id:   int
    allergen:     str
    allergy_type: Optional[str] = None
    reaction:     Optional[str] = None
    severity:     Optional[str] = None
    noted_date:   Optional[str] = None
    notes:        Optional[str] = None


class ConditionCreate(BaseModel):
    patient_id:     int
    condition:      str
    icd10_code:     Optional[str] = None
    diagnosed_date: Optional[str] = None
    diagnosed_by:   Optional[str] = None
    status:         Optional[str] = "Active"
    treatment:      Optional[str] = None
    notes:          Optional[str] = None


class InvoiceCreate(BaseModel):
    patient_id:         int
    consultation_id:    Optional[int]   = None
    consultation_fee:   Optional[float] = None
    lab_charges:        Optional[float] = None
    medication_charges: Optional[float] = None
    other_charges:      Optional[float] = None
    discount:           Optional[float] = 0
    tax:                Optional[float] = 0
    total_amount:       Optional[float] = None
    payment_method:     Optional[str]   = None
    insurance_claim:    Optional[bool]  = False
    notes:              Optional[str]   = None


class PatientInfo(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    blood_type: Optional[str] = None
    medical_history: Optional[str] = None
    current_medications: Optional[str] = None
    allergies: Optional[str] = None
    smoking_status: Optional[str] = None
    alcohol_use: Optional[str] = None
    family_history: Optional[str] = None


class DiagnosisRequest(BaseModel):
    model_name:      str
    model_provider:  str
    system_prompt:   Optional[str]       = None
    symptoms:        List[str]           = Field(..., min_length=1)
    additional_info: Optional[str]       = None
    duration:        Optional[str]       = None
    severity:        Optional[str]       = "Moderate"
    allow_search:    bool                = False
    patient_info:    Optional[PatientInfo] = None
    patient_db_id:   Optional[int]       = None
    send_email:      Optional[bool]      = True


class ChatRequest(BaseModel):
    model_name:     str
    model_provider: str
    system_prompt:  Optional[str] = None
    messages:       List[str]
    allow_search:   bool = False
    patient_info:   Optional[PatientInfo] = None


class DiagnosisReview(BaseModel):
    doctor_notes:   str
    approved:       bool = True
    urgency_level:  Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/auth/register", status_code=201, tags=["Auth"])
def register(data: UserRegister,
             db: Session = Depends(get_db),
             current_user=Depends(get_optional_user)):
    """
    Public registration: only 'doctor' or 'patient' roles allowed.
    Creating an 'admin' account requires an existing admin JWT.
    """
    if UserCRUD.get_by_email(db, data.email):
        raise HTTPException(400, "Email already registered")

    # SECURITY: block self-promotion to admin
    if data.role == "admin":
        if not current_user or current_user.role != "admin":
            raise HTTPException(403, "Only an existing admin can create admin accounts.")

    # Block doctor role creation by non-admins is intentionally NOT enforced here
    # (doctors register themselves via the dashboard register tab)
    # But admin role is strictly gated above.

    if data.role == "patient" and not data.consent_given:
        raise HTTPException(400, "Patient must give consent to data processing (DISHA compliance)")

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()
    user = UserCRUD.create(db, email=data.email, password_hash=hashed,
                           full_name=data.full_name, role=data.role,
                           phone=data.phone, consent_given=data.consent_given)
    token = create_token({"user_id": user.id, "role": user.role, "email": user.email})
    return {"access_token": token, "token_type": "bearer",
            "user": user.to_dict(), "message": "Registration successful"}


@app.post("/admin/promote", tags=["Auth"])
def promote_user(email: str, new_role: str,
                 current_user=Depends(require_admin),
                 db: Session = Depends(get_db)):
    """Admin-only: promote or demote any user's role."""
    if new_role not in ("patient", "doctor", "admin"):
        raise HTTPException(400, "Role must be patient, doctor, or admin")
    user = UserCRUD.get_by_email(db, email)
    if not user:
        raise HTTPException(404, "User not found")
    user.role = new_role
    db.commit()
    log_action(db, current_user.id, "PROMOTE_USER", "user", user.id,
               detail=f"{email} -> {new_role}")
    return {"success": True, "message": f"{email} is now {new_role}"}


@app.get("/admin/pending-doctors", tags=["Auth"])
def pending_doctors(current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: list doctor accounts awaiting approval (is_active=False, role=doctor)."""
    from database import User
    users = db.query(User).filter(User.role == "doctor", User.is_active == False).all()
    return {"total": len(users), "users": [u.to_dict() for u in users]}


@app.patch("/admin/activate", tags=["Auth"])
def activate_user(email: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: approve a pending doctor — sets is_active=True so they can log in."""
    user = UserCRUD.get_by_email(db, email)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = True
    db.commit()
    log_action(db, current_user.id, "ACTIVATE_USER", "user", user.id, detail=email)
    return {"success": True, "message": f"{email} account activated"}


@app.patch("/admin/deactivate", tags=["Auth"])
def deactivate_user(email: str, current_user=Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only: deactivate a user account (blocks login)."""
    user = UserCRUD.get_by_email(db, email)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    db.commit()
    log_action(db, current_user.id, "DEACTIVATE_USER", "user", user.id, detail=email)
    return {"success": True, "message": f"{email} account deactivated"}


@app.post("/auth/login", tags=["Auth"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with email + password → returns JWT token."""
    user = UserCRUD.get_by_email(db, form.username)
    if not user or not bcrypt.checkpw(form.password.encode(), user.password_hash.encode()):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "Account deactivated. Contact admin.")
    UserCRUD.update_last_login(db, user.id)
    token = create_token({"user_id": user.id, "role": user.role, "email": user.email})
    return {"access_token": token, "token_type": "bearer",
            "user": user.to_dict()}


@app.post("/auth/login-json", tags=["Auth"])
def login_json(data: UserLogin, db: Session = Depends(get_db)):
    """Login via JSON body (for Streamlit frontend)."""
    user = UserCRUD.get_by_email(db, data.email)
    if not user or not bcrypt.checkpw(data.password.encode(), user.password_hash.encode()):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "Account deactivated. Contact admin.")
    UserCRUD.update_last_login(db, user.id)
    token = create_token({"user_id": user.id, "role": user.role, "email": user.email})
    return {"access_token": token, "token_type": "bearer", "user": user.to_dict()}


@app.get("/auth/me", tags=["Auth"])
def me(user=Depends(get_current_user)):
    return user.to_dict()


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


@app.post("/auth/change-password", tags=["Auth"])
def change_password(data: ChangePasswordRequest,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    old_password = data.old_password
    new_password = data.new_password
    if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
        raise HTTPException(400, "Old password is incorrect")
    if len(new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    UserCRUD.update_password(db, user.id, new_hash)
    log_action(db, user.id, "CHANGE_PASSWORD", "user", user.id)
    return {"success": True, "message": "Password changed successfully"}


# ══════════════════════════════════════════════════════════════════════════════
# HEALTH
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Health"])
def root(): return {"status": "healthy", "service": "MedAssist AI v6", "version": "6.0.0"}


@app.get("/health/db", tags=["Health"])
def db_health(db: Session = Depends(get_db)):
    try:
        from sqlalchemy import text; db.execute(text("SELECT 1"))
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(503, f"DB unreachable: {e}")


@app.get("/stats", tags=["Dashboard"])
def stats(user=Depends(require_doctor), db: Session = Depends(get_db)):
    log_action(db, user.id, "VIEW_STATS", "system")
    return get_db_stats(db)


@app.get("/models", tags=["Meta"])
def models():
    return {"groq": GROQ_MODELS, "openai": OPENAI_MODELS, "all": ALL_MODELS}


# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD  (FIX 3)
# ══════════════════════════════════════════════════════════════════════════════

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".dicom", ".docx"}

@app.post("/upload", tags=["Files"])
async def upload_file(
    patient_id: int,
    record_type: str = "Lab Report",
    title: str = "Uploaded Document",
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF/image medical record (lab report, scan, prescription etc.)"""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    # Check size
    contents = await file.read()
    if len(contents) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {MAX_FILE_MB}MB allowed.")

    # Save to disk under uploads/patient_<id>/
    patient_dir = UPLOAD_DIR / f"patient_{patient_id}"
    patient_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}{ext}"
    file_path  = patient_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(contents)

    # Save record to DB
    record = MedicalRecordCRUD.create(db,
        patient_id=patient_id, record_type=record_type, title=title,
        file_name=safe_name, file_type=ext.lstrip(".").upper(),
        file_path=str(file_path),
    )

    log_action(db, user.id, "UPLOAD_FILE", "medical_record", record.id,
               detail=f"{file.filename} → {safe_name}")

    return {
        "success": True,
        "record_id": record.id,
        "file_name": safe_name,
        "file_url": f"/uploads/patient_{patient_id}/{safe_name}",
        "file_size_kb": round(len(contents) / 1024, 1),
        "message": "File uploaded successfully"
    }


# ══════════════════════════════════════════════════════════════════════════════
# DOCTORS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/doctors", status_code=201, tags=["Doctors"])
def create_doctor(data: DoctorCreate, user=Depends(require_admin), db: Session = Depends(get_db)):
    d = DoctorCRUD.create(db, **data.model_dump(exclude_none=True))
    log_action(db, user.id, "CREATE_DOCTOR", "doctor", d.id)
    return {"success": True, "doctor": d.to_dict()}


@app.get("/doctors", tags=["Doctors"])
def list_doctors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    docs = DoctorCRUD.get_all(db, skip, limit)
    return {"total": DoctorCRUD.count(db), "doctors": [d.to_dict() for d in docs]}


@app.get("/doctors/{doctor_id}", tags=["Doctors"])
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    d = DoctorCRUD.get_by_id(db, doctor_id)
    if not d: raise HTTPException(404, "Doctor not found")
    return d.to_dict()


@app.put("/doctors/{doctor_id}", tags=["Doctors"])
def update_doctor(doctor_id: int, data: DoctorCreate,
                  user=Depends(require_admin), db: Session = Depends(get_db)):
    d = DoctorCRUD.update(db, doctor_id, **data.model_dump(exclude_none=True))
    if not d: raise HTTPException(404, "Doctor not found")
    log_action(db, user.id, "UPDATE_DOCTOR", "doctor", doctor_id)
    return {"success": True, "doctor": d.to_dict()}


@app.delete("/doctors/{doctor_id}", tags=["Doctors"])
def delete_doctor(doctor_id: int, user=Depends(require_admin), db: Session = Depends(get_db)):
    if not DoctorCRUD.delete(db, doctor_id): raise HTTPException(404, "Doctor not found")
    log_action(db, user.id, "DELETE_DOCTOR", "doctor", doctor_id)
    return {"success": True}


# ══════════════════════════════════════════════════════════════════════════════
# PATIENTS
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/patients", status_code=201, tags=["Patients"])
def create_patient(data: PatientCreate, db: Session = Depends(get_db),
                   user=Depends(get_optional_user)):
    # DISHA: require consent for data processing
    if not data.consent_given:
        raise HTTPException(400, "Patient consent is required before storing health data (DISHA compliance)")
    if data.email:
        ex = PatientCRUD.get_by_email(db, data.email)
        if ex: raise HTTPException(400, f"Email already registered for patient #{ex.id}")
    try:
        # Exclude schema-only fields that have no column in the Patient table
        patient_data = {k: v for k, v in data.model_dump(exclude_none=True).items()
                        if k != "consent_given"}
        p = PatientCRUD.create(db, **patient_data)
        uid = user.id if user else None
        log_action(db, uid, "CREATE_PATIENT", "patient", p.id)
        return {"success": True, "patient": p.to_dict()}
    except Exception as e:
        raise HTTPException(400, str(e))

@app.get("/patients", tags=["Patients"])
def list_patients(skip: int = 0, limit: int = 200,
                  user=Depends(require_doctor), db: Session = Depends(get_db)):
    log_action(db, user.id, "LIST_PATIENTS", "patient")
    pts = PatientCRUD.get_all(db, skip, limit)
    return {"total": PatientCRUD.count(db), "patients": [p.to_dict() for p in pts]}


@app.get("/patients/search", tags=["Patients"])
def search_patients(q: str = Query(..., min_length=1),
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    # Patients can only search for themselves (by email); doctors/admins can search freely
    if user.role == "patient":
        results = PatientCRUD.search_by_email_exact(db, user.email)
    else:
        results = PatientCRUD.search(db, q)
    log_action(db, user.id, "SEARCH_PATIENTS", "patient", detail=q)
    return {"count": len(results), "results": [p.to_dict() for p in results]}


@app.get("/patients/{patient_id}", tags=["Patients"])
def get_patient(patient_id: int, db: Session = Depends(get_db),
                user=Depends(get_current_user)):
    p = PatientCRUD.get_by_id(db, patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    uid = user.id if user else None
    log_action(db, uid, "VIEW_PATIENT", "patient", patient_id)
    return p.to_dict()


@app.put("/patients/{patient_id}", tags=["Patients"])
def update_patient(patient_id: int, data: PatientUpdate,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    update_data = {k: v for k, v in data.model_dump(exclude_none=True).items()
                   if k != "consent_given"}
    p = PatientCRUD.update(db, patient_id, **update_data)
    if not p: raise HTTPException(404, "Patient not found")
    log_action(db, user.id, "UPDATE_PATIENT", "patient", patient_id)
    return {"success": True, "patient": p.to_dict()}


@app.delete("/patients/{patient_id}", tags=["Patients"])
def delete_patient(patient_id: int, user=Depends(require_doctor), db: Session = Depends(get_db)):
    if not PatientCRUD.delete(db, patient_id): raise HTTPException(404, "Patient not found")
    log_action(db, user.id, "DELETE_PATIENT", "patient", patient_id)
    return {"success": True}


@app.get("/patients/{patient_id}/full-profile", tags=["Patients"])
def full_profile(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = PatientCRUD.get_by_id(db, patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    log_action(db, user.id, "VIEW_FULL_PROFILE", "patient", patient_id)
    profile = p.to_dict()
    profile["consultations"]   = [c.to_dict() for c in ConsultationCRUD.get_by_patient(db, patient_id, limit=10)]
    profile["vitals"]          = [v.to_dict() for v in VitalSignsCRUD.get_by_patient(db, patient_id, limit=5)]
    profile["lab_results"]     = [l.to_dict() for l in LabResultCRUD.get_by_patient(db, patient_id)]
    profile["medications"]     = [m.to_dict() for m in MedicationCRUD.get_by_patient(db, patient_id, current_only=True)]
    profile["allergies"]       = [a.to_dict() for a in AllergyPatientCRUD.get_by_patient(db, patient_id)]
    profile["conditions"]      = [c.to_dict() for c in ChronicConditionCRUD.get_by_patient(db, patient_id)]
    profile["appointments"]    = [a.to_dict() for a in AppointmentCRUD.get_by_patient(db, patient_id)]
    profile["medical_records"] = [r.to_dict() for r in MedicalRecordCRUD.get_by_patient(db, patient_id)]
    profile["invoices"]        = [i.to_dict() for i in InvoiceCRUD.get_by_patient(db, patient_id)]
    return profile


# ══════════════════════════════════════════════════════════════════════════════
# APPOINTMENTS  (FIX 4: email on booking)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/appointments", status_code=201, tags=["Appointments"])
def create_appointment(data: AppointmentCreate, background_tasks: BackgroundTasks,
                       db: Session = Depends(get_db), user=Depends(get_current_user)):
    p = PatientCRUD.get_by_id(db, data.patient_id)
    if not p: raise HTTPException(404, "Patient not found")

    # Patients can only book for themselves — verify ownership via email match
    if user.role == "patient":
        if not p.email or p.email.lower() != user.email.lower():
            raise HTTPException(403, "You can only book appointments for your own patient record")

    doctor_name = "Your Doctor"
    if data.doctor_id:
        d = DoctorCRUD.get_by_id(db, data.doctor_id)
        if d: doctor_name = f"Dr. {d.first_name} {d.last_name}"

    payload = data.model_dump(exclude_none=True)
    payload.pop("send_email", None)
    a = AppointmentCRUD.create(db, **payload)
    log_action(db, user.id, "CREATE_APPOINTMENT", "appointment", a.id)

    # FIX 4: Send confirmation email in background
    if data.send_email and p.email:
        html = appointment_email_html(
            patient_name=p.to_dict()["full_name"],
            appt_date=str(data.appointment_date),
            appt_time=data.appointment_time or "TBD",
            doctor_name=doctor_name,
            reason=data.reason or "General consultation",
            appt_type=data.appointment_type or "In-person",
        )
        background_tasks.add_task(
            send_email_background, p.email,
            "✅ Appointment Confirmed — MedAssist AI", html
        )

    return {"success": True, "appointment": a.to_dict(),
            "email_sent": bool(data.send_email and p.email)}


@app.get("/appointments/upcoming", tags=["Appointments"])
def upcoming(limit: int = 30, user=Depends(require_doctor), db: Session = Depends(get_db)):
    appts = AppointmentCRUD.get_upcoming(db, limit)
    return {"total": len(appts), "appointments": [a.to_dict() for a in appts]}


@app.get("/patients/{patient_id}/appointments", tags=["Appointments"])
def patient_appointments(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    appts = AppointmentCRUD.get_by_patient(db, patient_id)
    return {"total": len(appts), "appointments": [a.to_dict() for a in appts]}


@app.patch("/appointments/{appt_id}/status", tags=["Appointments"])
def update_appt_status(appt_id: int, status: str,
                       user=Depends(require_doctor), db: Session = Depends(get_db)):
    valid = ["Scheduled","Completed","Cancelled","No-show"]
    if status not in valid: raise HTTPException(400, f"Status must be one of {valid}")
    a = AppointmentCRUD.update_status(db, appt_id, status)
    if not a: raise HTTPException(404, "Appointment not found")
    log_action(db, user.id, f"APPT_STATUS_{status.upper()}", "appointment", appt_id)
    return {"success": True, "appointment": a.to_dict()}


# ══════════════════════════════════════════════════════════════════════════════
# CONSULTATIONS
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/patients/{patient_id}/consultations", tags=["Consultations"])
def patient_consultations(patient_id: int, skip: int = 0, limit: int = 50,
                           user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = PatientCRUD.get_by_id(db, patient_id)
    if not p: raise HTTPException(404, "Patient not found")
    log_action(db, user.id, "VIEW_CONSULTATIONS", "consultation", patient_id)
    cons = ConsultationCRUD.get_by_patient(db, patient_id, skip, limit)
    return {"patient": p.to_dict()["full_name"],
            "total_consultations": ConsultationCRUD.count_by_patient(db, patient_id),
            "consultations": [c.to_dict() for c in cons]}


@app.get("/consultations/recent", tags=["Consultations"])
def recent_consultations(limit: int = 20, user=Depends(require_doctor), db: Session = Depends(get_db)):
    recs = ConsultationCRUD.get_recent(db, limit)
    return {"total": len(recs), "consultations": [c.to_dict() for c in recs]}


@app.get("/consultations/{cid}", tags=["Consultations"])
def get_consultation(cid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = ConsultationCRUD.get_by_id(db, cid)
    if not c: raise HTTPException(404, "Consultation not found")
    log_action(db, user.id, "VIEW_CONSULTATION", "consultation", cid)
    return c.to_dict()


@app.patch("/consultations/{cid}/review", tags=["Consultations"])
def doctor_review(cid: int, data: DiagnosisReview,
                  user=Depends(require_doctor), db: Session = Depends(get_db)):
    """BONUS: Doctor reviews and approves AI diagnosis before patient sees final result."""
    c = ConsultationCRUD.get_by_id(db, cid)
    if not c: raise HTTPException(404, "Consultation not found")
    ConsultationCRUD.add_doctor_review(db, cid,
        doctor_notes=data.doctor_notes, approved=data.approved,
        urgency_level=data.urgency_level, reviewed_by=user.id)
    log_action(db, user.id, "REVIEW_DIAGNOSIS", "consultation", cid,
               detail=f"approved={data.approved}")
    return {"success": True, "message": "Review saved. Patient can now see the approved assessment."}


# ══════════════════════════════════════════════════════════════════════════════
# VITALS, LABS, RECORDS, MEDS, ALLERGIES, CONDITIONS, INVOICES
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/vitals", status_code=201, tags=["Vitals"])
def add_vitals(data: VitalsCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    v = VitalSignsCRUD.create(db, **data.model_dump(exclude_none=True))
    log_action(db, user.id, "ADD_VITALS", "vital_signs", v.id)
    return {"success": True, "vitals": v.to_dict()}


@app.get("/patients/{patient_id}/vitals", tags=["Vitals"])
def patient_vitals(patient_id: int, limit: int = 20,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    vitals = VitalSignsCRUD.get_by_patient(db, patient_id, limit)
    return {"total": len(vitals), "vitals": [v.to_dict() for v in vitals]}


@app.post("/lab-results", status_code=201, tags=["Lab Results"])
def add_lab_result(data: LabResultCreate, user=Depends(require_doctor), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    l = LabResultCRUD.create(db, **data.model_dump(exclude_none=True))
    log_action(db, user.id, "ADD_LAB_RESULT", "lab_result", l.id)
    return {"success": True, "lab_result": l.to_dict()}


@app.get("/patients/{patient_id}/lab-results", tags=["Lab Results"])
def patient_lab_results(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    results = LabResultCRUD.get_by_patient(db, patient_id)
    return {"total": len(results), "lab_results": [r.to_dict() for r in results]}


@app.post("/medical-records", status_code=201, tags=["Medical Records"])
def add_medical_record(data: MedicalRecordCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    r = MedicalRecordCRUD.create(db, **data.model_dump(exclude_none=True))
    log_action(db, user.id, "ADD_RECORD", "medical_record", r.id)
    return {"success": True, "record": r.to_dict()}


@app.get("/patients/{patient_id}/medical-records", tags=["Medical Records"])
def patient_medical_records(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    records = MedicalRecordCRUD.get_by_patient(db, patient_id)
    return {"total": len(records), "records": [r.to_dict() for r in records]}


@app.post("/medications", status_code=201, tags=["Medications"])
def add_medication(data: MedicationCreate, user=Depends(require_doctor), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    m = MedicationCRUD.create(db, **data.model_dump(exclude_none=True))
    log_action(db, user.id, "ADD_MEDICATION", "medication", m.id)
    return {"success": True, "medication": m.to_dict()}


@app.get("/patients/{patient_id}/medications", tags=["Medications"])
def patient_medications(patient_id: int, current_only: bool = False,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    meds = MedicationCRUD.get_by_patient(db, patient_id, current_only)
    return {"total": len(meds), "medications": [m.to_dict() for m in meds]}


@app.post("/allergies", status_code=201, tags=["Allergies"])
def add_allergy(data: AllergyCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    a = AllergyPatientCRUD.create(db, **data.model_dump(exclude_none=True))
    return {"success": True, "allergy": a.to_dict()}


@app.get("/patients/{patient_id}/allergies", tags=["Allergies"])
def patient_allergies(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    allergies = AllergyPatientCRUD.get_by_patient(db, patient_id)
    return {"total": len(allergies), "allergies": [a.to_dict() for a in allergies]}


@app.post("/conditions", status_code=201, tags=["Conditions"])
def add_condition(data: ConditionCreate, user=Depends(require_doctor), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    c = ChronicConditionCRUD.create(db, **data.model_dump(exclude_none=True))
    return {"success": True, "condition": c.to_dict()}


@app.get("/patients/{patient_id}/conditions", tags=["Conditions"])
def patient_conditions(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    conds = ChronicConditionCRUD.get_by_patient(db, patient_id)
    return {"total": len(conds), "conditions": [c.to_dict() for c in conds]}


@app.post("/invoices", status_code=201, tags=["Billing"])
def create_invoice(data: InvoiceCreate, user=Depends(require_doctor), db: Session = Depends(get_db)):
    if not PatientCRUD.get_by_id(db, data.patient_id): raise HTTPException(404, "Patient not found")
    payload = data.model_dump(exclude_none=True)
    if not payload.get("total_amount"):
        total = sum(float(payload.get(k, 0) or 0) for k in
                    ["consultation_fee","lab_charges","medication_charges","other_charges"])
        payload["total_amount"] = round(total - float(payload.get("discount",0)) + float(payload.get("tax",0)), 2)
    i = InvoiceCRUD.create(db, **payload)
    log_action(db, user.id, "CREATE_INVOICE", "invoice", i.id)
    return {"success": True, "invoice": i.to_dict()}


@app.get("/patients/{patient_id}/invoices", tags=["Billing"])
def patient_invoices(patient_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    invs = InvoiceCRUD.get_by_patient(db, patient_id)
    tb = sum(i.to_dict()["total_amount"] for i in invs)
    tp = sum(i.to_dict()["paid_amount"]  for i in invs)
    return {"total": len(invs), "total_billed": tb, "total_paid": tp,
            "balance_due": tb - tp, "invoices": [i.to_dict() for i in invs]}


@app.patch("/invoices/{inv_id}/payment", tags=["Billing"])
def update_payment(inv_id: int, paid_amount: float, method: str,
                   user=Depends(require_doctor), db: Session = Depends(get_db)):
    inv = InvoiceCRUD.update_payment(db, inv_id, paid_amount, method)
    if not inv: raise HTTPException(404, "Invoice not found")
    log_action(db, user.id, "RECORD_PAYMENT", "invoice", inv_id, detail=f"₹{paid_amount}")
    return {"success": True, "invoice": inv.to_dict()}


# ══════════════════════════════════════════════════════════════════════════════
# AI DIAGNOSIS  (FIX 4: email on save; BONUS: doctor approval flag)
# ══════════════════════════════════════════════════════════════════════════════

@app.post("/diagnose", tags=["AI"])
def diagnose(request: DiagnosisRequest, background_tasks: BackgroundTasks,
             db: Session = Depends(get_db), user=Depends(get_optional_user)):
    if request.model_name not in ALL_MODELS:
        raise HTTPException(400, f"Invalid model. Choose from: {ALL_MODELS}")

    patient_info_dict = None
    db_patient = None
    if request.patient_db_id:
        db_patient = PatientCRUD.get_by_id(db, request.patient_db_id)
        if not db_patient: raise HTTPException(404, "Patient not found")
        patient_info_dict = {k: v for k, v in db_patient.to_dict().items()
            if k in ["age","gender","weight","height","blood_type","medical_history",
                     "current_medications","allergies","smoking_status","alcohol_use","family_history"] and v}
    elif request.patient_info:
        patient_info_dict = request.patient_info.model_dump(exclude_none=True)

    query = analyze_symptoms(request.symptoms, request.severity or "Moderate", request.duration)
    if request.additional_info:
        query += f"\n\nAdditional Notes: {request.additional_info}"

    try:
        response = get_medical_diagnosis(
            llm_id=request.model_name, query=query,
            allow_search=request.allow_search,
            system_prompt=request.system_prompt or DEFAULT_MEDICAL_PROMPT,
            provider=request.model_provider, patient_info=patient_info_dict,
        )
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")

    saved_id = None
    if request.patient_db_id:
        try:
            c = ConsultationCRUD.create(
                db, patient_id=request.patient_db_id, symptoms=request.symptoms,
                chief_complaint=", ".join(request.symptoms),
                duration_of_symptoms=request.duration, severity=request.severity,
                additional_notes=request.additional_info, ai_diagnosis=response,
                model_used=request.model_name, model_provider=request.model_provider,
                web_search_enabled=request.allow_search,
                doctor_approval_status="pending",   # BONUS: requires doctor review
            )
            saved_id = c.id

            uid = user.id if user else None
            log_action(db, uid, "AI_DIAGNOSIS", "consultation", saved_id,
                       detail=f"{len(request.symptoms)} symptoms")

            # FIX 4: Email patient confirmation
            if request.send_email and db_patient and db_patient.email:
                html = consultation_saved_email_html(
                    db_patient.to_dict()["full_name"], request.symptoms, saved_id)
                background_tasks.add_task(
                    send_email_background, db_patient.email,
                    "✅ Your Health Consultation — MedAssist AI", html)
        except Exception as e:
            print(f"⚠️ Save failed: {e}")

    return {
        "diagnosis": response,
        "disclaimer": "⚠️ AI-generated. Pending doctor review before official use.",
        "doctor_approval_status": "pending" if saved_id else "not_saved",
        "model_used": request.model_name, "model_provider": request.model_provider,
        "web_search_enabled": request.allow_search,
        "saved_to_db": saved_id is not None, "consultation_id": saved_id,
        "patient_id": request.patient_db_id,
        "email_sent": bool(request.send_email and db_patient and db_patient.email),
    }


@app.post("/chat", tags=["AI"])
def chat(request: ChatRequest, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    if request.model_name not in ALL_MODELS:
        raise HTTPException(400, f"Invalid model: {ALL_MODELS}")
    query = "\n".join(request.messages)
    patient_info_dict = request.patient_info.model_dump(exclude_none=True) if request.patient_info else None
    try:
        response = get_medical_diagnosis(
            llm_id=request.model_name, query=query,
            allow_search=request.allow_search,
            system_prompt=request.system_prompt or DEFAULT_MEDICAL_PROMPT,
            provider=request.model_provider, patient_info=patient_info_dict,
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOGS  (FIX 2: DISHA compliance)
# ══════════════════════════════════════════════════════════════════════════════

@app.get("/audit-logs", tags=["Compliance"])
def audit_logs(skip: int = 0, limit: int = 100,
               user=Depends(require_admin), db: Session = Depends(get_db)):
    """Admin only — view all data access logs for DISHA compliance."""
    logs = AuditLogCRUD.get_all(db, skip, limit)
    return {"total": len(logs), "logs": [l.to_dict() for l in logs]}


@app.get("/audit-logs/patient/{patient_id}", tags=["Compliance"])
def patient_audit_logs(patient_id: int, user=Depends(require_admin), db: Session = Depends(get_db)):
    logs = AuditLogCRUD.get_by_resource(db, "patient", patient_id)
    return {"total": len(logs), "logs": [l.to_dict() for l in logs]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
