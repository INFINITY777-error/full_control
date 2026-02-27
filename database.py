# database.py — MedAssist AI v5.0 (Real-World Hospital Management System)
# ═══════════════════════════════════════════════════════════════════════════════
# 14 SCHEMAS / TABLES:
#   1.  doctors           — Physician registry
#   2.  patients          — Master patient record (enhanced with address, insurance)
#   3.  appointments      — Scheduling & calendar management
#   4.  consultations     — AI + manual clinical visit records
#   5.  vital_signs       — BP, pulse, temperature, SpO2, glucose per visit
#   6.  symptoms          — Per-symptom rows linked to consultations
#   7.  prescriptions     — Medication orders from consultations
#   8.  diagnostic_tests  — Recommended lab/imaging from consultations
#   9.  medical_records   — Documents/uploads (lab reports, scans)
#  10.  lab_results       — Individual lab values with reference ranges
#  11.  patient_allergies — Structured allergy entries with reaction type
#  12.  chronic_conditions— ICD-10 coded conditions per patient
#  13.  medications       — Full medication tracker (current + history)
#  14.  invoices          — Billing and payment tracking
# ═══════════════════════════════════════════════════════════════════════════════

from dotenv import load_dotenv
load_dotenv()

import os, enum, uuid
from datetime import datetime, date, timezone
from typing import List, Optional
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Float, ForeignKey, Boolean, Date, Numeric, text
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ─── Engine ───────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/medassist"
)

# SQLite uses NullPool which does not support pool_size/max_overflow
_is_sqlite = DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if _is_sqlite else {}

if _is_sqlite:
    engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
else:
    engine = create_engine(
        DATABASE_URL, echo=False,
        pool_pre_ping=True, pool_recycle=3600,
        pool_size=10, max_overflow=20,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _bmi_category(bmi):
    if not bmi: return None
    if bmi < 18.5: return "Underweight"
    if bmi < 25.0: return "Normal"
    if bmi < 30.0: return "Overweight"
    return "Obese"


# ══════════════════════════════════════════════════════════════════════════════
# 1. DOCTOR
# ══════════════════════════════════════════════════════════════════════════════
class Doctor(Base):
    __tablename__ = "doctors"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    first_name       = Column(String(100), nullable=False)
    last_name        = Column(String(100), nullable=False)
    email            = Column(String(255), unique=True, nullable=True)
    phone            = Column(String(20),  nullable=True)
    specialization   = Column(String(150), nullable=True)
    sub_specialization = Column(String(150), nullable=True)
    qualification    = Column(String(300), nullable=True)
    license_number   = Column(String(100), nullable=True)
    hospital         = Column(String(200), nullable=True)
    department       = Column(String(150), nullable=True)
    experience_years = Column(Integer,     nullable=True)
    consultation_fee = Column(Numeric(10,2), nullable=True)
    available_days   = Column(String(200), nullable=True)
    available_from   = Column(String(10),  nullable=True)
    available_to     = Column(String(10),  nullable=True)
    bio              = Column(Text,        nullable=True)
    languages        = Column(String(300), nullable=True)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    appointments  = relationship("Appointment",  back_populates="doctor")
    consultations = relationship("Consultation", back_populates="doctor")

    def to_dict(self):
        return {
            "id": self.id, "first_name": self.first_name, "last_name": self.last_name,
            "full_name": f"Dr. {self.first_name} {self.last_name}",
            "email": self.email, "phone": self.phone,
            "specialization": self.specialization, "sub_specialization": self.sub_specialization,
            "qualification": self.qualification, "license_number": self.license_number,
            "hospital": self.hospital, "department": self.department,
            "experience_years": self.experience_years,
            "consultation_fee": float(self.consultation_fee) if self.consultation_fee else None,
            "available_days": self.available_days, "available_from": self.available_from,
            "available_to": self.available_to, "bio": self.bio, "languages": self.languages,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 2. PATIENT
# ══════════════════════════════════════════════════════════════════════════════
class Patient(Base):
    __tablename__ = "patients"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    # Identity
    first_name    = Column(String(100), nullable=False)
    last_name     = Column(String(100), nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=True)
    phone         = Column(String(20),  nullable=True)
    date_of_birth = Column(DateTime,    nullable=True)
    age           = Column(Integer,     nullable=True)
    gender        = Column(String(20),  nullable=True)
    # Address
    address       = Column(Text,        nullable=True)
    city          = Column(String(100), nullable=True)
    state         = Column(String(100), nullable=True)
    pincode       = Column(String(20),  nullable=True)
    country       = Column(String(100), default="India")
    # Emergency Contact
    emergency_contact_name     = Column(String(200), nullable=True)
    emergency_contact_phone    = Column(String(20),  nullable=True)
    emergency_contact_relation = Column(String(100), nullable=True)
    # Physical
    weight     = Column(Float,      nullable=True)
    height     = Column(Float,      nullable=True)
    blood_type = Column(String(10), nullable=True)
    # Medical background (free text — kept for backward compat)
    medical_history     = Column(Text, nullable=True)
    current_medications = Column(Text, nullable=True)
    allergies           = Column(Text, nullable=True)
    family_history      = Column(Text, nullable=True)
    # Lifestyle
    smoking_status = Column(String(50),  nullable=True)
    alcohol_use    = Column(String(50),  nullable=True)
    activity_level = Column(String(100), nullable=True)
    diet_type      = Column(String(100), nullable=True)
    # Professional
    occupation         = Column(String(150), nullable=True)
    # Insurance
    insurance_provider = Column(String(200), nullable=True)
    insurance_id       = Column(String(100), nullable=True)
    insurance_validity = Column(Date,        nullable=True)
    # Meta
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active  = Column(Boolean,  default=True)

    consultations    = relationship("Consultation",     back_populates="patient", cascade="all, delete-orphan")
    appointments     = relationship("Appointment",      back_populates="patient", cascade="all, delete-orphan")
    vital_signs      = relationship("VitalSigns",       back_populates="patient", cascade="all, delete-orphan")
    medical_records  = relationship("MedicalRecord",    back_populates="patient", cascade="all, delete-orphan")
    lab_results      = relationship("LabResult",        back_populates="patient", cascade="all, delete-orphan")
    allergies_list   = relationship("PatientAllergy",   back_populates="patient", cascade="all, delete-orphan")
    conditions       = relationship("ChronicCondition", back_populates="patient", cascade="all, delete-orphan")
    medications      = relationship("Medication",       back_populates="patient", cascade="all, delete-orphan")
    invoices         = relationship("Invoice",          back_populates="patient", cascade="all, delete-orphan")

    def _bmi(self):
        if self.weight and self.height and self.height > 0:
            return round(self.weight / ((self.height / 100) ** 2), 1)
        return None

    def _age(self):
        if self.date_of_birth:
            today = date.today()
            dob = self.date_of_birth.date() if isinstance(self.date_of_birth, datetime) else self.date_of_birth
            return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return self.age

    def to_dict(self):
        bmi = self._bmi()
        return {
            "id": self.id, "first_name": self.first_name, "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "email": self.email, "phone": self.phone,
            "date_of_birth": self.date_of_birth.strftime("%Y-%m-%d") if self.date_of_birth else None,
            "age": self._age(), "gender": self.gender,
            "address": self.address, "city": self.city, "state": self.state,
            "pincode": self.pincode, "country": self.country,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relation": self.emergency_contact_relation,
            "weight": self.weight, "height": self.height,
            "bmi": bmi, "bmi_category": _bmi_category(bmi),
            "blood_type": self.blood_type,
            "medical_history": self.medical_history,
            "current_medications": self.current_medications,
            "allergies": self.allergies, "family_history": self.family_history,
            "smoking_status": self.smoking_status, "alcohol_use": self.alcohol_use,
            "activity_level": self.activity_level, "diet_type": self.diet_type,
            "occupation": self.occupation,
            "insurance_provider": self.insurance_provider,
            "insurance_id": self.insurance_id,
            "insurance_validity": str(self.insurance_validity) if self.insurance_validity else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "total_consultations": len(self.consultations) if self.consultations is not None else 0,
            "total_appointments":  len(self.appointments)  if self.appointments  is not None else 0,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 3. APPOINTMENT
# ══════════════════════════════════════════════════════════════════════════════
class Appointment(Base):
    __tablename__ = "appointments"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    patient_id       = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id        = Column(Integer, ForeignKey("doctors.id",  ondelete="SET NULL"), nullable=True)
    appointment_date = Column(Date,       nullable=False)
    appointment_time = Column(String(10), nullable=True)
    duration_mins    = Column(Integer, default=30)
    appointment_type = Column(String(100), nullable=True)   # In-person / Telemedicine / Follow-up
    reason           = Column(Text,        nullable=True)
    status           = Column(String(50),  default="Scheduled")  # Scheduled/Completed/Cancelled/No-show
    room_number      = Column(String(50),  nullable=True)
    notes            = Column(Text,        nullable=True)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date   = Column(Date,        nullable=True)
    reminder_sent    = Column(Boolean, default=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="appointments")
    doctor  = relationship("Doctor",  back_populates="appointments")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id, "doctor_id": self.doctor_id,
            "appointment_date": str(self.appointment_date) if self.appointment_date else None,
            "appointment_time": self.appointment_time, "duration_mins": self.duration_mins,
            "appointment_type": self.appointment_type, "reason": self.reason,
            "status": self.status, "room_number": self.room_number, "notes": self.notes,
            "follow_up_required": self.follow_up_required,
            "follow_up_date": str(self.follow_up_date) if self.follow_up_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "doctor_name": f"Dr. {self.doctor.first_name} {self.doctor.last_name}" if self.doctor else None,
            "patient_name": f"{self.patient.first_name} {self.patient.last_name}" if self.patient else None,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 4. CONSULTATION
# ══════════════════════════════════════════════════════════════════════════════
class Consultation(Base):
    __tablename__ = "consultations"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id       = Column(Integer, ForeignKey("doctors.id",  ondelete="SET NULL"), nullable=True)
    consultation_date    = Column(DateTime,    default=datetime.utcnow)
    chief_complaint      = Column(Text,        nullable=True)
    duration_of_symptoms = Column(String(100), nullable=True)
    severity             = Column(String(20),  nullable=True)
    additional_notes     = Column(Text,        nullable=True)
    # AI Output
    ai_diagnosis           = Column(Text,       nullable=True)
    differential_diagnoses = Column(Text,       nullable=True)
    urgency_level          = Column(String(50), nullable=True)
    # Model info
    model_used         = Column(String(100), nullable=True)
    model_provider     = Column(String(50),  nullable=True)
    web_search_enabled = Column(Boolean, default=False)
    # Follow-up
    follow_up_required = Column(Boolean, default=False)
    follow_up_date     = Column(Date,    nullable=True)
    # v6.0: doctor approval flow
    doctor_approval_status = Column(String(20), default='pending')  # pending/approved/rejected
    doctor_notes   = Column(Text, nullable=True)
    reviewed_by    = Column(Integer, nullable=True)  # doctor user_id
    reviewed_at    = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient       = relationship("Patient",       back_populates="consultations")
    doctor        = relationship("Doctor",        back_populates="consultations")
    symptoms      = relationship("Symptom",       back_populates="consultation", cascade="all, delete-orphan")
    prescriptions = relationship("Prescription",  back_populates="consultation", cascade="all, delete-orphan")
    tests         = relationship("DiagnosticTest",back_populates="consultation", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id, "patient_id": self.patient_id, "doctor_id": self.doctor_id,
            "consultation_date": self.consultation_date.isoformat() if self.consultation_date else None,
            "chief_complaint": self.chief_complaint,
            "duration_of_symptoms": self.duration_of_symptoms,
            "severity": self.severity, "additional_notes": self.additional_notes,
            "ai_diagnosis": self.ai_diagnosis,
            "urgency_level": self.urgency_level,
            "model_used": self.model_used, "model_provider": self.model_provider,
            "web_search_enabled": self.web_search_enabled,
            "follow_up_required": self.follow_up_required,
            "follow_up_date": str(self.follow_up_date) if self.follow_up_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "doctor_name": f"Dr. {self.doctor.first_name} {self.doctor.last_name}" if self.doctor else None,
            "symptoms":      [s.to_dict() for s in self.symptoms]      if self.symptoms      else [],
            "prescriptions": [p.to_dict() for p in self.prescriptions] if self.prescriptions else [],
            "tests":         [t.to_dict() for t in self.tests]         if self.tests         else [],
        }


# ══════════════════════════════════════════════════════════════════════════════
# 5. VITAL SIGNS
# ══════════════════════════════════════════════════════════════════════════════
class VitalSigns(Base):
    __tablename__ = "vital_signs"
    id               = Column(Integer, primary_key=True, autoincrement=True)
    patient_id       = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consultation_id  = Column(Integer, ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    recorded_at      = Column(DateTime, default=datetime.utcnow)
    bp_systolic      = Column(Integer, nullable=True)
    bp_diastolic     = Column(Integer, nullable=True)
    pulse_rate       = Column(Integer, nullable=True)
    respiratory_rate = Column(Integer, nullable=True)
    temperature      = Column(Float,   nullable=True)
    spo2             = Column(Float,   nullable=True)
    blood_glucose    = Column(Float,   nullable=True)
    weight           = Column(Float,   nullable=True)
    height           = Column(Float,   nullable=True)
    pain_scale       = Column(Integer, nullable=True)   # 0–10
    notes            = Column(Text,    nullable=True)

    patient = relationship("Patient", back_populates="vital_signs")

    def _bp_status(self):
        if not self.bp_systolic: return None
        s, d = self.bp_systolic, self.bp_diastolic or 0
        if s < 120 and d < 80:  return "✅ Normal"
        if s < 130:              return "🟡 Elevated"
        if s < 140 or d < 90:   return "🟠 High Stage 1"
        return "🔴 High Stage 2"

    def to_dict(self):
        bmi = round(self.weight / ((self.height/100)**2), 1) if self.weight and self.height else None
        return {
            "id": self.id, "patient_id": self.patient_id, "consultation_id": self.consultation_id,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "bp_systolic": self.bp_systolic, "bp_diastolic": self.bp_diastolic,
            "blood_pressure": f"{self.bp_systolic}/{self.bp_diastolic}" if self.bp_systolic else None,
            "bp_status": self._bp_status(),
            "pulse_rate": self.pulse_rate, "respiratory_rate": self.respiratory_rate,
            "temperature": self.temperature, "spo2": self.spo2,
            "blood_glucose": self.blood_glucose, "weight": self.weight, "height": self.height,
            "bmi": bmi, "pain_scale": self.pain_scale, "notes": self.notes,
        }


# ══════════════════════════════════════════════════════════════════════════════
# 6. SYMPTOM
# ══════════════════════════════════════════════════════════════════════════════
class Symptom(Base):
    __tablename__ = "symptoms"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id", ondelete="CASCADE"), nullable=False)
    symptom_name    = Column(String(200), nullable=False)
    category        = Column(String(100), nullable=True)
    severity        = Column(String(20),  nullable=True)
    description     = Column(Text,        nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    consultation    = relationship("Consultation", back_populates="symptoms")
    def to_dict(self):
        return {"id": self.id, "symptom_name": self.symptom_name,
                "category": self.category, "severity": self.severity,
                "description": self.description,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 7. PRESCRIPTION
# ══════════════════════════════════════════════════════════════════════════════
class Prescription(Base):
    __tablename__ = "prescriptions"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id", ondelete="CASCADE"), nullable=False)
    medication_name = Column(String(200), nullable=False)
    medication_type = Column(String(50),  nullable=True)
    dosage          = Column(String(100), nullable=True)
    frequency       = Column(String(100), nullable=True)
    duration        = Column(String(100), nullable=True)
    purpose         = Column(Text,        nullable=True)
    instructions    = Column(Text,        nullable=True)
    warnings        = Column(Text,        nullable=True)
    is_otc          = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    consultation    = relationship("Consultation", back_populates="prescriptions")
    def to_dict(self):
        return {"id": self.id, "medication_name": self.medication_name,
                "medication_type": self.medication_type, "dosage": self.dosage,
                "frequency": self.frequency, "duration": self.duration,
                "purpose": self.purpose, "is_otc": self.is_otc,
                "instructions": self.instructions, "warnings": self.warnings,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 8. DIAGNOSTIC TEST
# ══════════════════════════════════════════════════════════════════════════════
class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id", ondelete="CASCADE"), nullable=False)
    test_name  = Column(String(200), nullable=False)
    test_type  = Column(String(100), nullable=True)
    priority   = Column(String(50),  nullable=True)
    reason     = Column(Text,        nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    consultation = relationship("Consultation", back_populates="tests")
    def to_dict(self):
        return {"id": self.id, "test_name": self.test_name, "test_type": self.test_type,
                "priority": self.priority, "reason": self.reason,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 9. MEDICAL RECORD (document/upload)
# ══════════════════════════════════════════════════════════════════════════════
class MedicalRecord(Base):
    __tablename__ = "medical_records"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    record_type     = Column(String(100), nullable=False)  # Lab Report / X-Ray / MRI / Discharge / Prescription
    title           = Column(String(300), nullable=False)
    description     = Column(Text,        nullable=True)
    file_name       = Column(String(300), nullable=True)
    file_type       = Column(String(50),  nullable=True)
    issued_by       = Column(String(200), nullable=True)
    issued_date     = Column(Date,        nullable=True)
    tags            = Column(String(500), nullable=True)
    file_path       = Column(String(500), nullable=True)  # v6.0: actual file path on disk
    created_at      = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="medical_records")
    def to_dict(self):
        return {"id": self.id, "patient_id": self.patient_id,
                "record_type": self.record_type, "title": self.title,
                "description": self.description, "file_name": self.file_name,
                "file_type": self.file_type, "issued_by": self.issued_by,
                "issued_date": str(self.issued_date) if self.issued_date else None,
                "tags": self.tags.split(",") if self.tags else [],
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 10. LAB RESULT
# ══════════════════════════════════════════════════════════════════════════════
class LabResult(Base):
    __tablename__ = "lab_results"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    patient_id      = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consultation_id = Column(Integer, ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    test_name       = Column(String(200), nullable=False)
    test_category   = Column(String(100), nullable=True)
    result_value    = Column(String(100), nullable=True)
    result_unit     = Column(String(50),  nullable=True)
    reference_range = Column(String(100), nullable=True)
    status          = Column(String(50),  nullable=True)  # Normal / High / Low / Critical
    lab_name        = Column(String(200), nullable=True)
    tested_at       = Column(DateTime,    nullable=True)
    notes           = Column(Text,        nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="lab_results")
    def to_dict(self):
        return {"id": self.id, "patient_id": self.patient_id,
                "test_name": self.test_name, "test_category": self.test_category,
                "result_value": self.result_value, "result_unit": self.result_unit,
                "reference_range": self.reference_range, "status": self.status,
                "lab_name": self.lab_name,
                "tested_at": self.tested_at.isoformat() if self.tested_at else None,
                "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 11. PATIENT ALLERGY (structured)
# ══════════════════════════════════════════════════════════════════════════════
class PatientAllergy(Base):
    __tablename__ = "patient_allergies"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    patient_id   = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    allergen     = Column(String(200), nullable=False)
    allergy_type = Column(String(100), nullable=True)   # Drug / Food / Environmental / Latex
    reaction     = Column(String(300), nullable=True)
    severity     = Column(String(50),  nullable=True)   # Mild / Moderate / Severe / Life-threatening
    noted_date   = Column(Date,        nullable=True)
    notes        = Column(Text,        nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="allergies_list")
    def to_dict(self):
        return {"id": self.id, "patient_id": self.patient_id,
                "allergen": self.allergen, "allergy_type": self.allergy_type,
                "reaction": self.reaction, "severity": self.severity,
                "noted_date": str(self.noted_date) if self.noted_date else None,
                "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 12. CHRONIC CONDITION
# ══════════════════════════════════════════════════════════════════════════════
class ChronicCondition(Base):
    __tablename__ = "chronic_conditions"
    id             = Column(Integer, primary_key=True, autoincrement=True)
    patient_id     = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    condition      = Column(String(200), nullable=False)
    icd10_code     = Column(String(20),  nullable=True)
    diagnosed_date = Column(Date,        nullable=True)
    diagnosed_by   = Column(String(200), nullable=True)
    status         = Column(String(50),  nullable=True)  # Active / Controlled / Resolved
    treatment      = Column(Text,        nullable=True)
    notes          = Column(Text,        nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="conditions")
    def to_dict(self):
        return {"id": self.id, "patient_id": self.patient_id,
                "condition": self.condition, "icd10_code": self.icd10_code,
                "diagnosed_date": str(self.diagnosed_date) if self.diagnosed_date else None,
                "diagnosed_by": self.diagnosed_by, "status": self.status,
                "treatment": self.treatment, "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 13. MEDICATION TRACKER
# ══════════════════════════════════════════════════════════════════════════════
class Medication(Base):
    __tablename__ = "medications"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    patient_id    = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    drug_name     = Column(String(200), nullable=False)
    generic_name  = Column(String(200), nullable=True)
    dosage        = Column(String(100), nullable=True)
    frequency     = Column(String(100), nullable=True)
    route         = Column(String(50),  nullable=True)   # Oral / IV / Topical / Inhaled
    prescribed_by = Column(String(200), nullable=True)
    start_date    = Column(Date,        nullable=True)
    end_date      = Column(Date,        nullable=True)
    is_current    = Column(Boolean, default=True)
    indication    = Column(Text,        nullable=True)
    side_effects  = Column(Text,        nullable=True)
    refill_date   = Column(Date,        nullable=True)
    notes         = Column(Text,        nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="medications")
    def to_dict(self):
        return {"id": self.id, "patient_id": self.patient_id,
                "drug_name": self.drug_name, "generic_name": self.generic_name,
                "dosage": self.dosage, "frequency": self.frequency, "route": self.route,
                "prescribed_by": self.prescribed_by,
                "start_date": str(self.start_date) if self.start_date else None,
                "end_date": str(self.end_date) if self.end_date else None,
                "is_current": self.is_current, "indication": self.indication,
                "side_effects": self.side_effects,
                "refill_date": str(self.refill_date) if self.refill_date else None,
                "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ══════════════════════════════════════════════════════════════════════════════
# 14. INVOICE / BILLING
# ══════════════════════════════════════════════════════════════════════════════
class Invoice(Base):
    __tablename__ = "invoices"
    id                 = Column(Integer, primary_key=True, autoincrement=True)
    patient_id         = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consultation_id    = Column(Integer, ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True)
    invoice_number     = Column(String(50), unique=True, nullable=True)
    invoice_date       = Column(Date,   default=date.today)
    due_date           = Column(Date,   nullable=True)
    consultation_fee   = Column(Numeric(10,2), nullable=True)
    lab_charges        = Column(Numeric(10,2), nullable=True)
    medication_charges = Column(Numeric(10,2), nullable=True)
    other_charges      = Column(Numeric(10,2), nullable=True)
    discount           = Column(Numeric(10,2), default=0)
    tax                = Column(Numeric(10,2), default=0)
    total_amount       = Column(Numeric(10,2), nullable=True)
    paid_amount        = Column(Numeric(10,2), default=0)
    payment_status     = Column(String(50), default="Pending")  # Pending/Paid/Partial/Cancelled
    payment_method     = Column(String(100), nullable=True)
    insurance_claim    = Column(Boolean, default=False)
    notes              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)
    patient = relationship("Patient", back_populates="invoices")
    def to_dict(self):
        def f(v): return float(v) if v is not None else 0.0
        return {"id": self.id, "patient_id": self.patient_id,
                "consultation_id": self.consultation_id,
                "invoice_number": self.invoice_number,
                "invoice_date": str(self.invoice_date) if self.invoice_date else None,
                "due_date": str(self.due_date) if self.due_date else None,
                "consultation_fee": f(self.consultation_fee),
                "lab_charges": f(self.lab_charges),
                "medication_charges": f(self.medication_charges),
                "other_charges": f(self.other_charges),
                "discount": f(self.discount), "tax": f(self.tax),
                "total_amount": f(self.total_amount),
                "paid_amount": f(self.paid_amount),
                "balance_due": max(0, f(self.total_amount) - f(self.paid_amount)),
                "payment_status": self.payment_status,
                "payment_method": self.payment_method,
                "insurance_claim": self.insurance_claim, "notes": self.notes,
                "created_at": self.created_at.isoformat() if self.created_at else None}


# ─── DB Lifecycle ─────────────────────────────────────────────────────────────



# ══════════════════════════════════════════════════════════════════════════════
# v6.0 ADDITIONS (MOVED HERE — must be before init_db so create_all sees them)
# User (JWT Auth) + AuditLog (DISHA Compliance)
# ══════════════════════════════════════════════════════════════════════════════

class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(200), nullable=False)
    role          = Column(String(20), default="patient")  # patient/doctor/admin
    phone         = Column(String(20), nullable=True)
    consent_given = Column(Boolean, default=False)
    is_active     = Column(Boolean, default=True)
    last_login    = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "email": self.email, "full_name": self.full_name,
            "role": self.role, "phone": self.phone,
            "consent_given": self.consent_given, "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    user_id     = Column(Integer, nullable=True)
    action      = Column(String(100), nullable=False)
    resource    = Column(String(100), nullable=True)
    resource_id = Column(Integer,     nullable=True)
    detail      = Column(Text,        nullable=True)
    ip_address  = Column(String(50),  nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "user_id": self.user_id, "action": self.action,
            "resource": self.resource, "resource_id": self.resource_id,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

def init_db():
    Base.metadata.create_all(bind=engine)
    safe = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    print(f"✅ 14 tables ready — {safe}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"❌ DB connection failed: {e}")
        return False


def get_db_stats(db):
    return {
        "total_patients":      db.query(Patient).filter(Patient.is_active == True).count(),
        "total_doctors":       db.query(Doctor).filter(Doctor.is_active == True).count(),
        "total_consultations": db.query(Consultation).count(),
        "total_appointments":  db.query(Appointment).count(),
        "upcoming_appointments": db.query(Appointment).filter(
            Appointment.appointment_date >= date.today(),
            Appointment.status == "Scheduled"
        ).count(),
        "total_symptoms":      db.query(Symptom).count(),
        "total_prescriptions": db.query(Prescription).count(),
        "total_lab_results":   db.query(LabResult).count(),
        "total_invoices":      db.query(Invoice).count(),
        "pending_invoices":    db.query(Invoice).filter(Invoice.payment_status == "Pending").count(),
        "total_medications":   db.query(Medication).filter(Medication.is_current == True).count(),
        "total_conditions":    db.query(ChronicCondition).count(),
    }


# ─── CRUD ─────────────────────────────────────────────────────────────────────

class PatientCRUD:
    @staticmethod
    def create(db, **kw):
        # Strip fields that belong to other models / request schemas, not the Patient table
        for _extra in ("consent_given",):
            kw.pop(_extra, None)
        if "date_of_birth" in kw and isinstance(kw["date_of_birth"], str):
            try: kw["date_of_birth"] = datetime.strptime(kw["date_of_birth"], "%Y-%m-%d")
            except: kw.pop("date_of_birth")
        if "insurance_validity" in kw and isinstance(kw["insurance_validity"], str):
            try: kw["insurance_validity"] = datetime.strptime(kw["insurance_validity"], "%Y-%m-%d").date()
            except: kw.pop("insurance_validity")
        p = Patient(**kw); db.add(p); db.commit(); db.refresh(p); return p

    @staticmethod
    def get_by_id(db, pid):
        return db.query(Patient).filter(Patient.id == pid, Patient.is_active == True).first()

    @staticmethod
    def get_by_email(db, email):
        return db.query(Patient).filter(Patient.email == email).first()

    @staticmethod
    def search_by_email_exact(db, email):
        """Return list with the single patient matching this email exactly (for patient self-lookup)."""
        p = db.query(Patient).filter(Patient.email == email, Patient.is_active == True).first()
        return [p] if p else []

    @staticmethod
    def get_all(db, skip=0, limit=200):
        return db.query(Patient).filter(Patient.is_active == True).order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def search(db, q):
        like = f"%{q}%"
        return db.query(Patient).filter(Patient.is_active == True).filter(
            Patient.first_name.ilike(like) | Patient.last_name.ilike(like) |
            Patient.email.ilike(like) | Patient.phone.ilike(like)
        ).all()

    @staticmethod
    def update(db, pid, **kw):
        if "date_of_birth" in kw and isinstance(kw["date_of_birth"], str):
            try: kw["date_of_birth"] = datetime.strptime(kw["date_of_birth"], "%Y-%m-%d")
            except: kw.pop("date_of_birth")
        p = db.query(Patient).filter(Patient.id == pid).first()
        if p:
            for k, v in kw.items():
                if hasattr(p, k) and v is not None: setattr(p, k, v)
            p.updated_at = datetime.utcnow(); db.commit(); db.refresh(p)
        return p

    @staticmethod
    def delete(db, pid):
        p = db.query(Patient).filter(Patient.id == pid).first()
        if p: p.is_active = False; p.updated_at = datetime.utcnow(); db.commit(); return True
        return False

    @staticmethod
    def count(db): return db.query(Patient).filter(Patient.is_active == True).count()


class ConsultationCRUD:
    @staticmethod
    def create(db, patient_id, symptoms, **kw):
        c = Consultation(patient_id=patient_id, **kw); db.add(c); db.flush()
        for s in symptoms:
            db.add(Symptom(consultation_id=c.id, symptom_name=s, severity=kw.get("severity")))
        db.commit(); db.refresh(c); return c

    @staticmethod
    def get_by_id(db, cid): return db.query(Consultation).filter(Consultation.id == cid).first()

    @staticmethod
    def get_by_patient(db, pid, skip=0, limit=50):
        return db.query(Consultation).filter(Consultation.patient_id == pid).order_by(Consultation.consultation_date.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_recent(db, limit=20):
        return db.query(Consultation).order_by(Consultation.consultation_date.desc()).limit(limit).all()

    @staticmethod
    def count(db): return db.query(Consultation).count()

    @staticmethod
    def count_by_patient(db, pid): return db.query(Consultation).filter(Consultation.patient_id == pid).count()

    @staticmethod
    def add_doctor_review(db, cid, doctor_notes, approved, urgency_level=None, reviewed_by=None):
        c = db.query(Consultation).filter(Consultation.id == cid).first()
        if c:
            c.doctor_notes = doctor_notes
            c.doctor_approval_status = "approved" if approved else "rejected"
            c.urgency_level = urgency_level
            c.reviewed_by = reviewed_by
            c.reviewed_at = datetime.utcnow()
            db.commit(); db.refresh(c)
        return c


class DoctorCRUD:
    @staticmethod
    def create(db, **kw):
        d = Doctor(**kw); db.add(d); db.commit(); db.refresh(d); return d

    @staticmethod
    def get_all(db, skip=0, limit=100):
        return db.query(Doctor).filter(Doctor.is_active == True).order_by(Doctor.first_name).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_id(db, did): return db.query(Doctor).filter(Doctor.id == did).first()

    @staticmethod
    def update(db, did, **kw):
        d = db.query(Doctor).filter(Doctor.id == did).first()
        if d:
            for k, v in kw.items():
                if hasattr(d, k) and v is not None: setattr(d, k, v)
            db.commit(); db.refresh(d)
        return d

    @staticmethod
    def delete(db, did):
        d = db.query(Doctor).filter(Doctor.id == did).first()
        if d: d.is_active = False; db.commit(); return True
        return False

    @staticmethod
    def count(db): return db.query(Doctor).filter(Doctor.is_active == True).count()


class AppointmentCRUD:
    @staticmethod
    def create(db, **kw):
        for f in ["appointment_date", "follow_up_date"]:
            if f in kw and isinstance(kw[f], str):
                try: kw[f] = datetime.strptime(kw[f], "%Y-%m-%d").date()
                except: kw.pop(f)
        a = Appointment(**kw); db.add(a); db.commit(); db.refresh(a); return a

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(Appointment).filter(Appointment.patient_id == pid).order_by(Appointment.appointment_date.desc()).all()

    @staticmethod
    def get_upcoming(db, limit=30):
        return db.query(Appointment).filter(
            Appointment.appointment_date >= date.today(),
            Appointment.status == "Scheduled"
        ).order_by(Appointment.appointment_date, Appointment.appointment_time).limit(limit).all()

    @staticmethod
    def update_status(db, aid, status):
        a = db.query(Appointment).filter(Appointment.id == aid).first()
        if a: a.status = status; db.commit(); db.refresh(a)
        return a

    @staticmethod
    def count(db): return db.query(Appointment).count()


class VitalSignsCRUD:
    @staticmethod
    def create(db, **kw):
        v = VitalSigns(**kw); db.add(v); db.commit(); db.refresh(v); return v

    @staticmethod
    def get_by_patient(db, pid, limit=20):
        return db.query(VitalSigns).filter(VitalSigns.patient_id == pid).order_by(VitalSigns.recorded_at.desc()).limit(limit).all()


class LabResultCRUD:
    @staticmethod
    def create(db, **kw):
        if "tested_at" in kw and isinstance(kw["tested_at"], str):
            try: kw["tested_at"] = datetime.strptime(kw["tested_at"], "%Y-%m-%d")
            except: pass
        l = LabResult(**kw); db.add(l); db.commit(); db.refresh(l); return l

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(LabResult).filter(LabResult.patient_id == pid).order_by(LabResult.tested_at.desc()).all()


class MedicalRecordCRUD:
    @staticmethod
    def create(db, **kw):
        if "issued_date" in kw and isinstance(kw["issued_date"], str):
            try: kw["issued_date"] = datetime.strptime(kw["issued_date"], "%Y-%m-%d").date()
            except: pass
        r = MedicalRecord(**kw); db.add(r); db.commit(); db.refresh(r); return r

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(MedicalRecord).filter(MedicalRecord.patient_id == pid).order_by(MedicalRecord.created_at.desc()).all()


class MedicationCRUD:
    @staticmethod
    def create(db, **kw):
        for f in ["start_date", "end_date", "refill_date"]:
            if f in kw and isinstance(kw[f], str):
                try: kw[f] = datetime.strptime(kw[f], "%Y-%m-%d").date()
                except: kw.pop(f)
        m = Medication(**kw); db.add(m); db.commit(); db.refresh(m); return m

    @staticmethod
    def get_by_patient(db, pid, current_only=False):
        q = db.query(Medication).filter(Medication.patient_id == pid)
        if current_only: q = q.filter(Medication.is_current == True)
        return q.order_by(Medication.created_at.desc()).all()


class AllergyPatientCRUD:
    @staticmethod
    def create(db, **kw):
        if "noted_date" in kw and isinstance(kw["noted_date"], str):
            try: kw["noted_date"] = datetime.strptime(kw["noted_date"], "%Y-%m-%d").date()
            except: kw.pop("noted_date")
        a = PatientAllergy(**kw); db.add(a); db.commit(); db.refresh(a); return a

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(PatientAllergy).filter(PatientAllergy.patient_id == pid).all()


class ChronicConditionCRUD:
    @staticmethod
    def create(db, **kw):
        if "diagnosed_date" in kw and isinstance(kw["diagnosed_date"], str):
            try: kw["diagnosed_date"] = datetime.strptime(kw["diagnosed_date"], "%Y-%m-%d").date()
            except: kw.pop("diagnosed_date")
        c = ChronicCondition(**kw); db.add(c); db.commit(); db.refresh(c); return c

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(ChronicCondition).filter(ChronicCondition.patient_id == pid).all()


class InvoiceCRUD:
    @staticmethod
    def create(db, **kw):
        kw["invoice_number"] = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        i = Invoice(**kw); db.add(i); db.commit(); db.refresh(i); return i

    @staticmethod
    def get_by_patient(db, pid):
        return db.query(Invoice).filter(Invoice.patient_id == pid).order_by(Invoice.invoice_date.desc()).all()

    @staticmethod
    def update_payment(db, iid, paid_amount, method):
        inv = db.query(Invoice).filter(Invoice.id == iid).first()
        if inv:
            inv.paid_amount = paid_amount; inv.payment_method = method
            inv.payment_status = "Paid" if paid_amount >= float(inv.total_amount or 0) else "Partial"
            db.commit(); db.refresh(inv)
        return inv


class PrescriptionCRUD:
    @staticmethod
    def get_by_patient(db, pid):
        return db.query(Prescription).join(Consultation).filter(Consultation.patient_id == pid).order_by(Prescription.created_at.desc()).all()


if __name__ == "__main__":
    print("🏥 MedAssist AI — Database v5.0")
    if test_connection():
        init_db()
        print("✅ All 14 tables created successfully!")


# ══════════════════════════════════════════════════════════════════════════════


class UserCRUD:
    @staticmethod
    def create(db, **kw):
        u = User(**kw); db.add(u); db.commit(); db.refresh(u); return u

    @staticmethod
    def get_by_email(db, email):
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_id(db, uid):
        return db.query(User).filter(User.id == uid).first()

    @staticmethod
    def update_last_login(db, uid):
        u = db.query(User).filter(User.id == uid).first()
        if u: u.last_login = datetime.utcnow(); db.commit()

    @staticmethod
    def update_password(db, uid, new_hash):
        u = db.query(User).filter(User.id == uid).first()
        if u: u.password_hash = new_hash; db.commit()

    @staticmethod
    def get_all(db, skip=0, limit=100):
        return db.query(User).offset(skip).limit(limit).all()


class AuditLogCRUD:
    @staticmethod
    def create(db, **kw):
        log = AuditLog(**kw); db.add(log); db.commit(); return log

    @staticmethod
    def get_all(db, skip=0, limit=100):
        return db.query(AuditLog).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_by_resource(db, resource, resource_id):
        return db.query(AuditLog).filter(
            AuditLog.resource == resource, AuditLog.resource_id == resource_id
        ).order_by(AuditLog.created_at.desc()).all()
