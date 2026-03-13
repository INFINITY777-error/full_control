# frontend.py — MedAssist AI v6.0 (Real-World Hospital Management System)
# ═══════════════════════════════════════════════════════════════════════════════
# TABS:
#   🏠 Dashboard          — Live stats, upcoming appointments, recent activity
#   🔬 AI Diagnosis       — Symptom analysis with full AI assessment
#   💬 Follow-up Chat     — Medical Q&A with AI
#   👤 Patients           — Register, view full profile, search
#   👨‍⚕️ Doctors           — Physician registry management
#   📅 Appointments       — Book, manage, view calendar
#   💊 Medications        — Add & track patient medications
#   🧪 Lab Results        — Record lab test results with reference ranges
#   ❤️ Vital Signs        — Record BP, pulse, temperature, SpO2, glucose
#   🏥 Medical Records    — Document registry (lab reports, scans, discharge)
#   ⚠️ Allergies          — Structured allergy management
#   🩺 Conditions         — Chronic condition tracker with ICD-10
#   🧾 Billing            — Invoice creation and payment tracking
# ═══════════════════════════════════════════════════════════════════════════════

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import requests
from datetime import date, datetime

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="MedAssist — Doctor Dashboard",
    page_icon="👨‍⚕️", layout="wide",
    initial_sidebar_state="expanded"
)

# ─── JWT LOGIN PROTECTION ─────────────────────────────────────────────────────
for _k, _v in [("token", None), ("user", None), ("auth_role", None), ("authenticated", False)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if not st.session_state.authenticated:
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');
    .stApp{background:linear-gradient(135deg,#060b14,#080d1a) !important;font-family:'DM Sans',sans-serif}
    #MainMenu,footer,header{visibility:hidden}
    .stTextInput>div>div>input{background:rgba(255,255,255,.06) !important;border:1px solid rgba(255,255,255,.14) !important;border-radius:10px !important;color:#fff !important;font-size:.95rem !important}
    .stButton>button{background:linear-gradient(135deg,#005bcc,#0080ff) !important;border:none !important;color:#fff !important;border-radius:10px !important;font-weight:500 !important;width:100% !important}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:2rem">
          <div style="font-size:3.5rem">🏥</div>
          <div style="font-family:'DM Serif Display',serif;font-size:2rem;color:#fff;margin:.5rem 0">MedAssist AI</div>
          <div style="font-size:.8rem;color:#4a6480;text-transform:uppercase;letter-spacing:.12em">Doctor / Admin Dashboard</div>
        </div>
        <div style="background:rgba(244,67,54,.08);border:1px solid rgba(244,67,54,.2);border-radius:12px;padding:.8rem 1rem;font-size:.82rem;color:#ff8a80;text-align:center;margin-bottom:1.5rem">
          🔐 Authorised Medical Staff Only
        </div>
        """, unsafe_allow_html=True)

        auth_tab_login, auth_tab_register = st.tabs(["🔓 Login", "📝 Register"])

        with auth_tab_login:
            email_input = st.text_input("Email:", placeholder="doctor@hospital.com", key="login_email", label_visibility="collapsed")
            pwd_input   = st.text_input("Password:", type="password", placeholder="••••••••", key="login_pwd", label_visibility="collapsed")
            login_btn   = st.button("🔓 Login to Dashboard", type="primary", use_container_width=True)

            if login_btn:
                if not email_input or not pwd_input:
                    st.error("Please enter your email and password.")
                else:
                    try:
                        resp = requests.post(f"{API_URL}/auth/login-json",
                                             json={"email": email_input, "password": pwd_input}, timeout=8)
                        if resp.status_code == 200:
                            data = resp.json()
                            role = data["user"].get("role", "patient")
                            if role not in ("doctor", "admin"):
                                st.error("❌ Access denied. Doctor or Admin account required.")
                            else:
                                st.session_state.token         = data["access_token"]
                                st.session_state.user          = data["user"]
                                st.session_state.auth_role     = role
                                st.session_state.authenticated = True
                                st.rerun()
                        else:
                            err = resp.json().get("detail", "Incorrect email or password")
                            st.error(f"❌ {err}")
                    except Exception as e:
                        st.error(f"❌ Cannot connect to backend: {e}")

        with auth_tab_register:
            st.markdown('<div style="font-size:.82rem;color:#5a7a9a;margin-bottom:.5rem">Register a new Doctor account</div>', unsafe_allow_html=True)
            reg_name  = st.text_input("Full Name *", placeholder="Dr. Jane Smith", key="reg_name")
            reg_email = st.text_input("Email *", placeholder="doctor@hospital.com", key="reg_email")
            reg_pwd   = st.text_input("Password *", type="password", placeholder="Min 8 characters", key="reg_pwd")
            reg_pwd2  = st.text_input("Confirm Password *", type="password", placeholder="Repeat password", key="reg_pwd2")
            reg_phone = st.text_input("Phone (optional)", key="reg_phone")
            st.markdown('<div style="background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.2);border-radius:8px;padding:.6rem .9rem;font-size:.8rem;color:#fbbf24;margin-bottom:.5rem">🔒 New accounts registered as <strong>Doctor</strong> only.</div>', unsafe_allow_html=True)
            reg_btn = st.button("📝 Create Doctor Account", type="primary", use_container_width=True)

            if reg_btn:
                if not reg_name.strip() or not reg_email.strip() or not reg_pwd:
                    st.error("Name, email, and password are required.")
                elif len(reg_pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                elif reg_pwd != reg_pwd2:
                    st.error("Passwords do not match.")
                else:
                    try:
                        payload = {
                            "full_name": reg_name.strip(), "email": reg_email.strip(),
                            "password": reg_pwd, "role": "doctor",
                            "consent_given": True,
                        }
                        if reg_phone.strip(): payload["phone"] = reg_phone.strip()
                        resp = requests.post(f"{API_URL}/auth/register", json=payload, timeout=8)
                        if resp.status_code == 201:
                            data = resp.json()
                            role = data["user"].get("role", "doctor")
                            st.session_state.token         = data["access_token"]
                            st.session_state.user          = data["user"]
                            st.session_state.auth_role     = role
                            st.session_state.authenticated = True
                            st.success(f"✅ Doctor account created! Welcome, Dr. {reg_name.split()[0]}!")
                            st.rerun()
                        else:
                            err = resp.json().get("detail", "Registration failed")
                            st.error(f"❌ {err}")
                    except Exception as e:
                        st.error(f"❌ Cannot connect to backend: {e}")

        st.markdown("""
        <div style="text-align:center;margin-top:1.5rem;color:#2a4060;font-size:.78rem">
          Are you a patient? Use the<br>
          <strong style="color:#3a5a7a">Patient Portal on port 8501</strong> instead
        </div>""", unsafe_allow_html=True)

    st.stop()

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');
*,*::before,*::after{box-sizing:border-box}
.stApp{background:#080d1a;font-family:'DM Sans',sans-serif;color:#dde6f0}
#MainMenu,footer,header{visibility:hidden}.stDeployButton{display:none}
.stApp::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:radial-gradient(ellipse at 15% 10%,rgba(0,102,204,.1) 0%,transparent 50%),
  radial-gradient(ellipse at 85% 90%,rgba(0,180,160,.07) 0%,transparent 50%)}

/* Header */
.hero{background:linear-gradient(135deg,#0c1526 0%,#091220 50%,#0c1d38 100%);
  border:1px solid rgba(0,140,255,.12);border-radius:18px;padding:2rem 2.5rem;
  margin-bottom:1.5rem;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,#0080ff,#00c4b4,transparent)}
.hero-title{font-family:'DM Serif Display',serif;font-size:2.4rem;color:#fff;
  letter-spacing:-.02em;margin:0 0 .2rem}
.hero-title span{background:linear-gradient(135deg,#0096ff,#00c4b4);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:.85rem;color:#5a7a9a;text-transform:uppercase;letter-spacing:.08em}
.hero-badge{display:inline-flex;align-items:center;gap:.4rem;margin-top:.6rem;
  background:rgba(0,150,255,.08);border:1px solid rgba(0,150,255,.2);
  border-radius:20px;padding:.2rem .7rem;font-size:.72rem;color:#4db8ff;letter-spacing:.1em}

/* Stats grid */
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;margin:.5rem 0 1.5rem}
.stat-card{background:linear-gradient(135deg,rgba(255,255,255,.03),rgba(255,255,255,.01));
  border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:1rem 1.25rem;
  position:relative;overflow:hidden;transition:border-color .2s}
.stat-card:hover{border-color:rgba(0,150,255,.2)}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px}
.stat-card.blue::before{background:linear-gradient(90deg,#0066cc,#0096ff)}
.stat-card.teal::before{background:linear-gradient(90deg,#00a896,#00c4b4)}
.stat-card.purple::before{background:linear-gradient(90deg,#7c3aed,#a855f7)}
.stat-card.orange::before{background:linear-gradient(90deg,#d97706,#f59e0b)}
.stat-card.red::before{background:linear-gradient(90deg,#dc2626,#ef4444)}
.stat-card.green::before{background:linear-gradient(90deg,#059669,#10b981)}
.stat-value{font-family:'DM Serif Display',serif;font-size:2rem;color:#e8edf5;line-height:1;margin-bottom:.2rem}
.stat-label{font-size:.72rem;color:#5a7a9a;text-transform:uppercase;letter-spacing:.1em}
.stat-icon{position:absolute;right:1rem;top:50%;transform:translateY(-50%);font-size:2rem;opacity:.12}

/* Cards */
.data-card{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);
  border-radius:14px;padding:1.25rem;margin:.5rem 0;transition:border-color .2s}
.data-card:hover{border-color:rgba(0,150,255,.2)}
.card-header{font-size:.72rem;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
  color:#4db8ff;margin-bottom:.75rem;display:flex;align-items:center;gap:.5rem}

/* Alerts */
.alert-warn{background:rgba(255,152,0,.07);border:1px solid rgba(255,152,0,.2);
  border-left:3px solid #ff9800;border-radius:10px;padding:.9rem 1.1rem;
  margin-bottom:1.25rem;font-size:.87rem;color:#f0b96b;line-height:1.6}
.alert-danger{background:rgba(244,67,54,.08);border:1px solid rgba(244,67,54,.25);
  border-left:3px solid #f44336;border-radius:10px;padding:1rem 1.25rem;color:#ff8a80;margin:1rem 0}
.alert-success{background:rgba(16,185,129,.07);border:1px solid rgba(16,185,129,.2);
  border-left:3px solid #10b981;border-radius:10px;padding:.9rem 1.1rem;color:#6ee7b7;margin:.5rem 0}

/* Diagnosis panel */
.dx-panel{background:linear-gradient(145deg,#0a172b,#07111f);
  border:1px solid rgba(0,150,255,.18);border-radius:16px;padding:2rem;margin-top:1rem;position:relative}
.dx-panel::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,#0096ff,#00c4b4)}
.dx-panel h2{font-family:'DM Serif Display',serif;font-size:1.3rem;color:#e8edf5;
  border-bottom:1px solid rgba(0,150,255,.12);padding-bottom:.5rem;margin-top:1.5rem}
.dx-panel h3{font-size:.95rem;color:#4db8ff;font-weight:500;margin-top:1rem}
.dx-panel table{width:100%;border-collapse:collapse;margin:.75rem 0;font-size:.85rem}
.dx-panel th{background:rgba(0,150,255,.08);color:#4db8ff;padding:.55rem .9rem;
  text-align:left;font-size:.75rem;text-transform:uppercase;letter-spacing:.07em;
  border:1px solid rgba(0,150,255,.12)}
.dx-panel td{padding:.55rem .9rem;border:1px solid rgba(255,255,255,.04);color:#aabdd0;line-height:1.5}
.dx-panel blockquote{border-left:3px solid rgba(255,152,0,.4);background:rgba(255,152,0,.05);
  padding:.65rem .9rem;margin:.6rem 0;border-radius:0 8px 8px 0;color:#f0b96b;font-size:.85rem}
.dx-panel strong{color:#e8edf5}
.dx-panel hr{border:none;border-top:1px solid rgba(255,255,255,.05);margin:1.25rem 0}
.dx-panel p,.dx-panel li{color:#aabdd0;line-height:1.7;font-size:.9rem}
.dx-panel ul,.dx-panel ol{padding-left:1.4rem;line-height:1.9}
.dx-panel code{background:rgba(0,150,255,.1);color:#4db8ff;padding:.1rem .35rem;border-radius:4px;font-size:.83em}

/* Pill/tag */
.tag{display:inline-flex;align-items:center;gap:.3rem;background:rgba(0,150,255,.1);
  border:1px solid rgba(0,150,255,.2);border-radius:20px;padding:.2rem .65rem;
  font-size:.78rem;color:#4db8ff;margin:.15rem}
.tag.green{background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.25);color:#6ee7b7}
.tag.orange{background:rgba(245,158,11,.1);border-color:rgba(245,158,11,.25);color:#fbbf24}
.tag.red{background:rgba(244,67,54,.1);border-color:rgba(244,67,54,.25);color:#ff8a80}
.tag.purple{background:rgba(168,85,247,.1);border-color:rgba(168,85,247,.25);color:#c084fc}

/* Vitals */
.vital-card{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.06);
  border-radius:10px;padding:.9rem;text-align:center}
.vital-val{font-family:'DM Serif Display',serif;font-size:1.6rem;color:#4db8ff;line-height:1}
.vital-unit{font-size:.7rem;color:#4a6480;text-transform:uppercase;margin-top:.1rem}
.vital-label{font-size:.72rem;color:#5a7a9a;margin-top:.3rem}

/* Sidebar */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#070c18,#050a13) !important;
  border-right:1px solid rgba(255,255,255,.04) !important}

/* Inputs */
.stTextInput>div>div>input,.stTextArea>div>div>textarea,.stNumberInput>div>div>input{
  background:rgba(255,255,255,.04) !important;border:1px solid rgba(255,255,255,.09) !important;
  border-radius:9px !important;color:#dde6f0 !important;font-size:.89rem !important}
.stSelectbox>div>div{background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.09) !important;border-radius:9px !important}
.stDateInput>div>div>input{background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.09) !important;border-radius:9px !important;color:#dde6f0 !important}

/* Buttons */
.stButton>button{font-family:'DM Sans',sans-serif !important;font-weight:500 !important;
  border-radius:9px !important;transition:all .2s !important}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,#005bcc,#0080ff) !important;
  border:none !important;color:#fff !important;
  box-shadow:0 4px 14px rgba(0,90,200,.3) !important}
.stButton>button[kind="primary"]:hover{transform:translateY(-1px) !important;
  box-shadow:0 6px 18px rgba(0,90,200,.4) !important}
.stButton>button[kind="secondary"]{background:rgba(255,255,255,.04) !important;
  border:1px solid rgba(255,255,255,.1) !important;color:#8ba4bc !important}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{gap:.2rem;background:rgba(255,255,255,.025);
  border-radius:12px;padding:.25rem}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;
  color:#5a7a9a;font-size:.82rem;font-weight:500;padding:.45rem .9rem;transition:all .2s}
.stTabs [aria-selected="true"]{background:rgba(0,150,255,.12) !important;color:#4db8ff !important}

/* Loading */
@keyframes shimmer{0%{background-position:-1000px 0}100%{background-position:1000px 0}}
.loading-bar{height:2px;background:linear-gradient(90deg,transparent,#0080ff,#00c4b4,transparent);
  background-size:1000px;animation:shimmer 1.8s linear infinite;border-radius:1px;margin-bottom:1rem}
.pulse{width:9px;height:9px;background:#00c4b4;border-radius:50%;
  animation:pulse-anim 2s infinite;flex-shrink:0}
@keyframes pulse-anim{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.75)}}

/* Section divider */
.section-title{font-family:'DM Serif Display',serif;font-size:1.15rem;color:#c8d8e8;
  margin:1rem 0 .6rem;display:flex;align-items:center;gap:.5rem}

/* Tables */
.info-table{width:100%;border-collapse:collapse;font-size:.87rem}
.info-table td{padding:.5rem .75rem;border-bottom:1px solid rgba(255,255,255,.04);color:#9ab0c8}
.info-table td:first-child{color:#5a7a9a;width:40%;font-weight:500}
.info-table tr:last-child td{border-bottom:none}

/* Status badges */
.badge{display:inline-block;padding:.15rem .55rem;border-radius:12px;font-size:.72rem;font-weight:600}
.badge.scheduled{background:rgba(0,150,255,.12);color:#4db8ff}
.badge.completed{background:rgba(16,185,129,.12);color:#6ee7b7}
.badge.cancelled{background:rgba(244,67,54,.12);color:#ff8a80}
.badge.pending{background:rgba(245,158,11,.12);color:#fbbf24}
.badge.paid{background:rgba(16,185,129,.12);color:#6ee7b7}
.badge.active{background:rgba(239,68,68,.12);color:#ff8a80}
.badge.controlled{background:rgba(245,158,11,.12);color:#fbbf24}
.badge.resolved{background:rgba(16,185,129,.12);color:#6ee7b7}

::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:rgba(255,255,255,.02)}
::-webkit-scrollbar-thumb{background:rgba(0,150,255,.2);border-radius:3px}
</style>
""", unsafe_allow_html=True)


# ─── HELPERS ──────────────────────────────────────────────────────────────────
def _headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}

def api_get(path, params=None):
    try:
        r = requests.get(f"{API_URL}{path}", params=params, headers=_headers(), timeout=8)
        return r.json() if r.status_code == 200 else None
    except: return None

def api_post(path, payload):
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, headers=_headers(), timeout=30)
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500

def api_patch(path, payload=None, params=None):
    try:
        r = requests.patch(f"{API_URL}{path}", json=payload, params=params,
                           headers=_headers(), timeout=8)
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500

def badge(text, cls="scheduled"):
    return f'<span class="badge {cls.lower()}">{text}</span>'

def tag(text, cls=""):
    return f'<span class="tag {cls}">{text}</span>'

def get_patients():
    data = api_get("/patients", {"limit": 500})
    return data.get("patients", []) if data else []

def get_doctors():
    data = api_get("/doctors", {"limit": 200})
    return data.get("doctors", []) if data else []

def patient_options(pts):
    opts = {"— Select Patient —": None}
    for p in pts: opts[f"#{p['id']} — {p['full_name']} ({p.get('age','?')}y)"] = p["id"]
    return opts

def doctor_options(docs):
    opts = {"— No specific doctor —": None}
    for d in docs: opts[f"Dr. {d['first_name']} {d['last_name']} ({d.get('specialization','General')})"] = d["id"]
    return opts


# ─── HEADER ───────────────────────────────────────────────────────────────────
_curr_role = st.session_state.get("auth_role", "doctor")
_curr_user = st.session_state.get("user", {}) or {}
_hero_icon = "🔧" if _curr_role == "admin" else "👨‍⚕️"
_hero_label = "Admin" if _curr_role == "admin" else "Doctor"
_hero_name = _curr_user.get("full_name", "")
_hero_subtitle = "System Administration · Full Access · Doctor Management" if _curr_role == "admin" else "Clinical Management · Patient Records · AI Diagnosis"
_hero_badge_txt = f"🔧 Admin Access · v6.0" if _curr_role == "admin" else "🔐 Doctor Access · v6.0 · Clinical Edition"
st.markdown(f"""
<div class="hero">
  <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem">
    <div>
      <div class="hero-title">{_hero_icon} {_hero_label} <span>Dashboard</span></div>
      <div class="hero-sub">{_hero_subtitle}</div>
      <div class="hero-badge">{_hero_badge_txt}</div>
      {('<div style="font-size:.85rem;color:#7a9ab8;margin-top:.4rem">Welcome back, <strong style="color:#dde6f0">' + str(_hero_name) + '</strong></div>') if _hero_name else ''}
    </div>
    <div style="text-align:right;color:#3a5a7a;font-size:.82rem;line-height:1.9">
      📋 Patient-Submitted Symptoms<br>
      📅 Appointment Calendar<br>
      🧪 Lab Results & Vitals<br>
      🧾 Billing & Records
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="alert-warn">
  <strong>⚠️ Medical Disclaimer:</strong> MedAssist AI provides <strong>educational health information only</strong>.
  It does NOT replace licensed medical advice. All AI assessments require physician confirmation.
  <strong>Emergency? Call 112 (India) · 911 (US) · 999 (UK) immediately.</strong>
</div>
""", unsafe_allow_html=True)


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Show logged-in role + logout button
    _user_data = st.session_state.get("user", {}) or {}
    role = st.session_state.get("auth_role", "doctor")
    _display_name = _user_data.get("full_name", "Staff")
    _role_icon = "🔧" if role == "admin" else "👨‍⚕️"
    _role_label = "Admin" if role == "admin" else "Doctor"
    _role_color = "#f59e0b" if role == "admin" else "#4db8ff"
    st.markdown(f"""
    <div style="background:rgba(0,150,255,.08);border:1px solid rgba(0,150,255,.18);
      border-radius:10px;padding:.7rem 1rem;margin-bottom:.75rem;font-size:.82rem">
      <div style="color:{_role_color};font-weight:600">{_role_icon} {_role_label} Dashboard</div>
      <div style="color:#dde6f0;font-size:.88rem;margin-top:.2rem;font-weight:500">{_display_name}</div>
      <div style="color:#3a5a7a;font-size:.72rem;margin-top:.1rem">{_user_data.get("email","")}</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔓 Logout", type="secondary", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.auth_role = None
        st.session_state.token = None
        st.session_state.user  = None
        st.rerun()
    st.divider()
    st.markdown("### ⚙️ AI Configuration")
    st.divider()

    MODEL_GROQ   = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"]
    MODEL_OPENAI = ["gpt-4o-mini", "gpt-4o"]
    provider = st.radio("Provider:", ("Groq", "OpenAI"), horizontal=True)
    selected_model = st.selectbox("Model:", MODEL_GROQ if provider == "Groq" else MODEL_OPENAI)
    allow_web_search = st.checkbox("🌐 Enable Web Search", value=False)

    st.divider()
    st.markdown("### 🗄️ Active Patient")
    pts = get_patients()
    pt_opts = patient_options(pts)
    sel_label = st.selectbox("Select for Diagnosis:", list(pt_opts.keys()))
    active_patient_id = pt_opts[sel_label]

    st.divider()
    st.markdown("### 📊 Live Stats")
    stats = api_get("/stats")
    if stats:
        items = [
            ("👥 Patients",      stats.get("total_patients", 0)),
            ("👨‍⚕️ Doctors",     stats.get("total_doctors", 0)),
            ("📋 Consultations", stats.get("total_consultations", 0)),
            ("📅 Appointments",  stats.get("total_appointments", 0)),
            ("💊 Active Meds",   stats.get("total_medications", 0)),
            ("🧪 Lab Results",   stats.get("total_lab_results", 0)),
            ("🧾 Pending Bills", stats.get("pending_invoices", 0)),
        ]
        for label, val in items:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;
              padding:.4rem .6rem;margin:.2rem 0;background:rgba(255,255,255,.02);
              border-radius:8px;border:1px solid rgba(255,255,255,.05);font-size:.82rem">
              <span style="color:#5a7a9a">{label}</span>
              <strong style="color:#4db8ff">{val}</strong>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("⚠️ Backend not connected. Start with:\n```\npython backend.py\n```")

    st.divider()
    with st.expander("🤖 Custom AI Prompt"):
        custom_prompt = st.text_area("Override system prompt:", height=100)

    with st.expander("👤 Manual Patient Info"):
        sb_age    = st.number_input("Age", 0, 120, value=None, step=1, key="ni_age_1")
        sb_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], key="sel_gender_1")
        sb_weight = st.number_input("Weight (kg)", value=None, step=0.5, key="ni_weight_1")
        sb_height = st.number_input("Height (cm)", value=None, step=0.5, key="ni_height_1")
        sb_allergy= st.text_input("Allergies", placeholder="e.g., Penicillin")
        sb_history= st.text_input("Medical History")
        sb_meds   = st.text_input("Current Medications")


# ─── TABS ─────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "🏠 Dashboard",
    "🔬 AI Diagnosis",
    "💬 Chat",
    "👤 Patients",
    "👨‍⚕️ Doctors",
    "📅 Appointments",
    "💊 Medications",
    "🧪 Lab Results",
    "❤️ Vital Signs",
    "🏥 Medical Records",
    "⚠️ Allergies & Conditions",
    "🧾 Billing",
    "🔒 Audit Log",
])
(tab_dash, tab_dx, tab_chat, tab_pts, tab_docs, tab_appts,
 tab_meds, tab_labs, tab_vitals, tab_records, tab_ac, tab_billing, tab_audit) = tabs


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown('<div class="section-title">📊 System Overview</div>', unsafe_allow_html=True)
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        metrics = [
            (col1, "👥", stats.get("total_patients", 0), "Total Patients", "blue"),
            (col2, "👨‍⚕️", stats.get("total_doctors", 0), "Doctors", "teal"),
            (col3, "📋", stats.get("total_consultations", 0), "Consultations", "purple"),
            (col4, "📅", stats.get("upcoming_appointments", 0), "Upcoming Appts", "orange"),
        ]
        for col, icon, val, label, cls in metrics:
            with col:
                st.markdown(f"""
                <div class="stat-card {cls}">
                  <div class="stat-value">{val}</div>
                  <div class="stat-label">{label}</div>
                  <div class="stat-icon">{icon}</div>
                </div>""", unsafe_allow_html=True)

        col5, col6, col7, col8 = st.columns(4)
        metrics2 = [
            (col5, "💊", stats.get("total_medications", 0), "Active Meds", "green"),
            (col6, "🧪", stats.get("total_lab_results", 0), "Lab Results", "teal"),
            (col7, "🩺", stats.get("total_conditions", 0), "Conditions Tracked", "purple"),
            (col8, "🧾", stats.get("pending_invoices", 0), "Pending Invoices", "red"),
        ]
        for col, icon, val, label, cls in metrics2:
            with col:
                st.markdown(f"""
                <div class="stat-card {cls}">
                  <div class="stat-value">{val}</div>
                  <div class="stat-label">{label}</div>
                  <div class="stat-icon">{icon}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.error("❌ Cannot connect to backend. Start the server with `python backend.py`")

    st.divider()
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-title">📅 Upcoming Appointments</div>', unsafe_allow_html=True)
        upcoming = api_get("/appointments/upcoming", {"limit": 10})
        if upcoming and upcoming.get("appointments"):
            for a in upcoming["appointments"]:
                st.markdown(f"""
                <div class="data-card">
                  <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:.5rem">
                    <div>
                      <strong style="color:#dde6f0">{a.get('patient_name','—')}</strong>
                      <div style="font-size:.82rem;color:#5a7a9a;margin-top:.2rem">
                        📅 {a.get('appointment_date','—')} at {a.get('appointment_time','—')} &nbsp;·&nbsp;
                        👨‍⚕️ {a.get('doctor_name') or 'No doctor assigned'} &nbsp;·&nbsp;
                        🕐 {a.get('duration_mins',30)} min
                      </div>
                      <div style="font-size:.82rem;color:#4a6480;margin-top:.15rem">📝 {a.get('reason') or 'No reason specified'}</div>
                    </div>
                    <span class="badge scheduled">{a.get('status','Scheduled')}</span>
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-card" style="color:#4a6480;text-align:center;padding:1.5rem">No upcoming appointments</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="section-title">📋 Recent Consultations</div>', unsafe_allow_html=True)
        recent = api_get("/consultations/recent", {"limit": 8})
        if recent and recent.get("consultations"):
            for c in recent["consultations"]:
                urgency = c.get("urgency_level", "")
                urg_color = "#ff8a80" if "Emergency" in (urgency or "") else "#fbbf24" if "Seek" in (urgency or "") else "#6ee7b7"
                st.markdown(f"""
                <div class="data-card">
                  <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                    <div>
                      <strong style="color:#dde6f0;font-size:.9rem">Patient #{c.get('patient_id','?')}</strong>
                      <div style="font-size:.8rem;color:#5a7a9a;margin-top:.15rem">
                        🗓 {(c.get('consultation_date') or '')[:10]} &nbsp;·&nbsp;
                        🤖 {c.get('model_used','AI')} &nbsp;·&nbsp;
                        ⚡ {c.get('severity','—')}
                      </div>
                      <div style="font-size:.8rem;color:#4a6480;margin-top:.1rem">
                        💬 {(c.get('chief_complaint') or 'No complaint recorded')[:60]}...
                      </div>
                    </div>
                    {f'<span style="color:{urg_color};font-size:.75rem">{urgency}</span>' if urgency else ''}
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="data-card" style="color:#4a6480;text-align:center;padding:1.5rem">No consultations yet</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: AI DIAGNOSIS
# ══════════════════════════════════════════════════════════════════════════════
with tab_dx:
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown('<div class="section-title">📋 Clinical Intake Form</div>', unsafe_allow_html=True)
        input_method = st.radio("Entry:", ["✍️ Free-form", "☑️ Checklist"], horizontal=True)

        if "✍️" in input_method:
            symptoms_text = st.text_area("Describe symptoms in detail:", height=150,
                placeholder="e.g., Severe throbbing headache for 3 days with fever 38.5°C, neck stiffness, photophobia...")
            symptoms_list = [symptoms_text.strip()] if symptoms_text.strip() else []
        else:
            categories = {
                "🌡️ General":         ["Fever","Chills","Fatigue","Weakness","Weight Loss","Night Sweats","Malaise","Loss of Appetite"],
                "🧠 Neurological":    ["Headache","Migraine","Dizziness","Confusion","Seizure","Memory Issues","Numbness","Tingling","Fainting"],
                "👁️ Head & ENT":     ["Vision Changes","Eye Pain","Ear Pain","Hearing Loss","Nasal Congestion","Sore Throat","Neck Stiffness","Jaw Pain"],
                "🫁 Respiratory":     ["Cough","Dry Cough","Productive Cough","Shortness of Breath","Wheezing","Chest Tightness","Hemoptysis"],
                "❤️ Cardiovascular":  ["Chest Pain","Palpitations","Irregular Heartbeat","Leg Swelling","Fainting","Leg Pain Walking"],
                "🫃 Digestive":       ["Nausea","Vomiting","Diarrhea","Constipation","Abdominal Pain","Bloating","Heartburn","Blood in Stool","Jaundice"],
                "🦴 Musculoskeletal": ["Joint Pain","Muscle Aches","Back Pain","Neck Pain","Stiffness","Swelling","Limited Mobility","Muscle Weakness"],
                "🩹 Skin":            ["Rash","Itching","Hives","Discoloration","Bruising","Lesions","Jaundice","Hair Loss","Nail Changes"],
                "🚽 Urinary":         ["Frequent Urination","Painful Urination","Blood in Urine","Urinary Incontinence","Reduced Urine Output"],
                "🧠 Mental Health":   ["Anxiety","Depression","Insomnia","Mood Changes","Panic Attacks","Hallucinations","Suicidal Thoughts"],
                "🤰 Reproductive":    ["Irregular Periods","Pelvic Pain","Discharge","Erectile Dysfunction","Testicular Pain","Breast Changes"],
            }
            selected = []
            for cat_idx, (cat, syms) in enumerate(categories.items()):
                with st.expander(cat):
                    cols = st.columns(2)
                    for sym_idx, s in enumerate(syms):
                        with cols[sym_idx % 2]:
                            if st.checkbox(s, key=f"sx_{cat_idx}_{sym_idx}"): selected.append(s)
            symptoms_list = selected
            if symptoms_list:
                tags_html = "".join([f'<span class="tag">✓ {s}</span>' for s in symptoms_list])
                st.markdown(f'<div style="margin:.5rem 0;line-height:2.2">{tags_html}</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            duration = st.text_input("⏱️ Duration", placeholder="e.g., 3 days")
        with col2:
            severity = st.select_slider("📊 Severity", ["Mild","Moderate","Severe","Critical"], value="Moderate")

        additional_info = st.text_area("📝 Additional Notes", height=80,
            placeholder="Travel history, exposures, aggravating/relieving factors...")
        analyze_btn = st.button("🔬 Run Clinical Analysis", type="primary", use_container_width=True)

    with right:
        st.markdown('<div class="section-title">📊 Clinical Assessment</div>', unsafe_allow_html=True)

        if analyze_btn:
            if not symptoms_list or not any(s.strip() for s in symptoms_list):
                st.warning("Please enter at least one symptom.")
            else:
                with st.spinner("⚕️ Analysing symptoms..."):
                    prog = st.empty()
                    prog.markdown('<div class="loading-bar"></div>', unsafe_allow_html=True)

                    patient_info = {}
                    if sb_age:    patient_info["age"]                 = sb_age
                    if sb_gender: patient_info["gender"]              = sb_gender
                    if sb_weight: patient_info["weight"]              = sb_weight
                    if sb_height: patient_info["height"]              = sb_height
                    if sb_allergy:patient_info["allergies"]           = sb_allergy
                    if sb_history:patient_info["medical_history"]     = sb_history
                    if sb_meds:   patient_info["current_medications"] = sb_meds

                    payload = {
                        "model_name": selected_model, "model_provider": provider,
                        "system_prompt": custom_prompt or None,
                        "symptoms": symptoms_list,
                        "additional_info": f"Severity: {severity}. {additional_info}" if additional_info else f"Severity: {severity}",
                        "duration": duration or None,
                        "allow_search": allow_web_search,
                        "patient_info": patient_info if patient_info and not active_patient_id else None,
                        "patient_db_id": active_patient_id,
                    }

                    try:
                        resp = requests.post(f"{API_URL}/diagnose", json=payload, headers=_headers(), timeout=180)
                        prog.empty()
                        if resp.status_code == 200:
                            result = resp.json()
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.markdown(f'<div class="stat-card blue"><div class="stat-value" style="font-size:1.3rem">{"🌐" if result.get("web_search_enabled") else "🧠"}</div><div class="stat-label">{"Web Search" if result.get("web_search_enabled") else "Knowledge"}</div></div>', unsafe_allow_html=True)
                            with col_b:
                                st.markdown(f'<div class="stat-card teal"><div class="stat-value" style="font-size:1rem">⚕️</div><div class="stat-label">{result.get("model_used","AI")}</div></div>', unsafe_allow_html=True)
                            with col_c:
                                st.markdown(f'<div class="stat-card purple"><div class="stat-value">{len(symptoms_list)}</div><div class="stat-label">Symptoms</div></div>', unsafe_allow_html=True)

                            st.markdown('<div class="dx-panel">', unsafe_allow_html=True)
                            st.markdown(result["diagnosis"])
                            st.markdown('</div>', unsafe_allow_html=True)
                            st.warning(result.get("disclaimer","Consult a licensed physician."))

                            if result.get("saved_to_db"):
                                st.success(f"✅ Saved to database — Consultation **#{result.get('consultation_id')}**")
                            elif active_patient_id:
                                st.warning("⚠️ Could not save to database. Check backend logs.")
                            else:
                                st.info("💡 Select a patient in the sidebar to save this diagnosis.")
                        else:
                            prog.empty()
                            st.error(f"❌ {resp.status_code}: {resp.json().get('detail','Error')}")
                    except requests.exceptions.ConnectionError:
                        prog.empty()
                        st.error("🔌 Backend not running. Start with `python backend.py`")
                    except Exception as e:
                        prog.empty()
                        st.error(f"❌ {e}")
        else:
            st.markdown("""
            <div style="text-align:center;padding:3rem 1rem;color:#2a3f5a">
              <div style="font-size:3.5rem;opacity:.3;margin-bottom:.75rem">🩺</div>
              <div style="font-size:1.1rem;color:#1e3a5f;font-family:'DM Serif Display',serif">Awaiting Clinical Input</div>
              <div style="font-size:.82rem;color:#1e3a5f;opacity:.6;margin-top:.4rem">
                Enter symptoms and click<br><strong>Run Clinical Analysis</strong>
              </div>
            </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: CHAT
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    st.markdown('<div class="section-title">💬 Medical Follow-up Chat</div>', unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    chat_input = st.text_area("Your Question:", height=90,
        placeholder="e.g., What are the side effects of Metformin? Is it safe to take with my blood pressure medication?")
    c1, c2 = st.columns([4, 1])
    with c1: send = st.button("📤 Send", type="primary", use_container_width=True)
    with c2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.chat_history = []; st.rerun()

    if send and chat_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": chat_input.strip()})
        with st.spinner("Consulting..."):
            payload = {"model_name": selected_model, "model_provider": provider,
                       "messages": [m["content"] for m in st.session_state.chat_history if m["role"] == "user"],
                       "allow_search": allow_web_search, "patient_info": None}
            data, code = api_post("/chat", payload)
            if code == 200:
                st.session_state.chat_history.append({"role": "assistant", "content": data.get("response","")})
            else:
                st.error(f"Error: {data.get('detail','Unknown error')}")

    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "user":
            st.markdown(f"""<div class="data-card" style="border-color:rgba(0,150,255,.15)">
              <div style="font-size:.7rem;color:#4db8ff;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.4rem">You</div>
              <div style="font-size:.9rem;color:#b0c4d8">{msg['content']}</div>
            </div>""", unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown("**🩺 Dr. MedAssist AI**")
                st.markdown(msg["content"])
                st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: PATIENTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_pts:
    pt_action = st.radio("Action", ["➕ Register", "📋 All Patients", "🔍 Search", "📂 Full Profile"], horizontal=True, key="radio_action")

    # ── Register ──
    if "➕" in pt_action:
        st.markdown('<div class="section-title">➕ Register New Patient</div>', unsafe_allow_html=True)
        with st.form("reg_pt", clear_on_submit=True):
            st.markdown("**Identity**")
            c1, c2, c3 = st.columns(3)
            with c1:
                fn = st.text_input("First Name *", key="ti_firstname_1")
                email = st.text_input("Email", key="ti_email_1")
                dob   = st.text_input("Date of Birth (YYYY-MM-DD)", placeholder="1990-01-15")
                gender= st.selectbox("Gender", ["","Male","Female","Other"], key="sel_gender_2")
            with c2:
                ln  = st.text_input("Last Name *", key="ti_lastname_1")
                phone= st.text_input("Phone", key="ti_phone_1")
                age  = st.number_input("Age", 0, 120, value=None, step=1, key="ni_age_2")
                occ  = st.text_input("Occupation")
            with c3:
                wt = st.number_input("Weight (kg)", value=None, step=0.5, key="ni_weight_2")
                ht = st.number_input("Height (cm)", value=None, step=0.5, key="ni_height_2")
                bt = st.selectbox("Blood Type", ["","A+","A-","B+","B-","AB+","AB-","O+","O-","Unknown"])
                act= st.selectbox("Activity Level", ["","Sedentary","Light","Moderate","Active","Very Active"])

            st.markdown("**Address**")
            c4, c5, c6 = st.columns(3)
            with c4: addr = st.text_input("Street Address")
            with c5: city = st.text_input("City")
            with c6:
                state= st.text_input("State")
                pin  = st.text_input("Pincode")

            st.markdown("**Emergency Contact**")
            c7, c8, c9 = st.columns(3)
            with c7: ec_name = st.text_input("Contact Name")
            with c8: ec_phone= st.text_input("Contact Phone")
            with c9: ec_rel  = st.text_input("Relation", placeholder="Spouse, Parent...")

            st.markdown("**Insurance**")
            c10, c11, c12 = st.columns(3)
            with c10: ins_prov = st.text_input("Insurance Provider")
            with c11: ins_id   = st.text_input("Policy / Insurance ID")
            with c12: ins_val  = st.text_input("Validity (YYYY-MM-DD)")

            st.markdown("**Medical Background**")
            c13, c14 = st.columns(2)
            with c13:
                med_hist = st.text_area("Medical History / Chronic Conditions", height=70)
                curr_meds= st.text_area("Current Medications", height=70)
                diet     = st.selectbox("Diet Type", ["","Vegetarian","Non-Vegetarian","Vegan","Jain","Diabetic"])
            with c14:
                allergy  = st.text_area("Known Allergies", height=70)
                fam_hist = st.text_area("Family History", height=70)
                smoking  = st.selectbox("Smoking", ["","Non-smoker","Ex-smoker","Light","Heavy"])
                alcohol  = st.selectbox("Alcohol Use", ["","None","Occasional","Moderate","Heavy"])

            submitted = st.form_submit_button("✅ Register Patient", type="primary", use_container_width=True)
            if submitted:
                if not fn.strip() or not ln.strip():
                    st.error("First Name and Last Name are required.")
                else:
                    payload = {"first_name": fn.strip(), "last_name": ln.strip()}
                    for k, v in [("email",email),("phone",phone),("date_of_birth",dob),("age",age),
                                  ("gender",gender),("weight",wt),("height",ht),("blood_type",bt),
                                  ("address",addr),("city",city),("state",state),("pincode",pin),
                                  ("emergency_contact_name",ec_name),("emergency_contact_phone",ec_phone),
                                  ("emergency_contact_relation",ec_rel),("occupation",occ),
                                  ("insurance_provider",ins_prov),("insurance_id",ins_id),
                                  ("insurance_validity",ins_val),("medical_history",med_hist),
                                  ("current_medications",curr_meds),("allergies",allergy),
                                  ("family_history",fam_hist),("smoking_status",smoking),
                                  ("alcohol_use",alcohol),("activity_level",act),("diet_type",diet)]:
                        if v: payload[k] = v
                    data, code = api_post("/patients", payload)
                    if code == 201:
                        p = data["patient"]
                        st.success(f"✅ Patient registered! **#{p['id']} — {p['full_name']}**. Select them in the sidebar to save diagnoses.")
                    else:
                        st.error(f"❌ {data.get('detail','Error')}")

    # ── All Patients ──
    elif "📋" in pt_action:
        st.markdown('<div class="section-title">📋 All Registered Patients</div>', unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="btn_refresh"): st.rerun()
        all_pts = api_get("/patients", {"limit": 500})
        if all_pts:
            st.caption(f"Total: **{all_pts.get('total',0)}** patients")
            for p in all_pts.get("patients", []):
                bmi = f" · BMI {p['bmi']} ({p['bmi_category']})" if p.get("bmi") else ""
                with st.expander(f"#{p['id']} — {p['full_name']} | {p.get('age','?')}y {p.get('gender','') or ''} | {p.get('blood_type','—')}{bmi} | Consultations: {p.get('total_consultations',0)}"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown(f"**Email:** {p.get('email') or '—'}")
                        st.markdown(f"**Phone:** {p.get('phone') or '—'}")
                        st.markdown(f"**DOB:** {p.get('date_of_birth') or '—'}")
                        st.markdown(f"**Address:** {p.get('city','')}, {p.get('state','')}")
                        st.markdown(f"**Occupation:** {p.get('occupation') or '—'}")
                    with c2:
                        st.markdown(f"**Medical History:** {p.get('medical_history') or '—'}")
                        st.markdown(f"**Medications:** {p.get('current_medications') or '—'}")
                        st.markdown(f"**Allergies:** {p.get('allergies') or '—'}")
                        st.markdown(f"**Family History:** {p.get('family_history') or '—'}")
                    with c3:
                        st.markdown(f"**Insurance:** {p.get('insurance_provider') or '—'} / {p.get('insurance_id') or '—'}")
                        st.markdown(f"**Emergency:** {p.get('emergency_contact_name') or '—'} ({p.get('emergency_contact_phone') or '—'})")
                        st.markdown(f"**Smoking:** {p.get('smoking_status') or '—'} · **Alcohol:** {p.get('alcohol_use') or '—'}")
                        st.markdown(f"**Activity:** {p.get('activity_level') or '—'} · **Diet:** {p.get('diet_type') or '—'}")

                    b1, b2 = st.columns([3, 1])
                    with b1:
                        if st.button(f"📋 Load Consultations", key=f"lc_{p['id']}"):
                            cdata = api_get(f"/patients/{p['id']}/consultations")
                            if cdata:
                                st.markdown(f"**{cdata.get('total_consultations',0)} consultation(s):**")
                                for c in cdata.get("consultations", []):
                                    syms = [s.get("symptom_name","") for s in c.get("symptoms", [])]
                                    approval = c.get("doctor_approval_status", "pending")
                                    badge_html = '<span style="background:#22c55e22;border:1px solid #22c55e;border-radius:6px;padding:2px 8px;font-size:.75rem;color:#22c55e">✅ Reviewed</span>' \
                                        if approval == "approved" else \
                                        '<span style="background:#f59e0b22;border:1px solid #f59e0b;border-radius:6px;padding:2px 8px;font-size:.75rem;color:#f59e0b">⏳ Pending</span>'
                                    st.markdown(f"**#{c['id']}** — {(c.get('consultation_date') or '')[:10]} | Severity: {c.get('severity','—')} | {c.get('model_used','—')} {badge_html}", unsafe_allow_html=True)
                                    if syms: st.markdown(f"Symptoms: {', '.join(syms)}")
                                    st.markdown(f"<div style='background:#0d1f2d;border:1px solid #1e3a5f;border-radius:8px;padding:8px 14px;margin-top:6px'><strong style='color:#7ab3d4'>🤖 Full AI Diagnosis #{c['id']}</strong></div>", unsafe_allow_html=True)
                                    if True:
                                        st.markdown(c.get("ai_diagnosis") or "No diagnosis recorded.")
                                        if c.get("doctor_notes"):
                                            st.markdown(f"**🩺 Doctor's Note:** {c['doctor_notes']}")
                                        # Review form — only show if pending
                                        if approval != "approved":
                                            st.markdown("---")
                                            st.markdown("**✍️ Review & Approve this Diagnosis:**")
                                            review_notes = st.text_area(f"Doctor's Notes for #{c['id']}",
                                                placeholder="Add clinical notes, corrections, or follow-up instructions...",
                                                key=f"notes_{c['id']}", height=80)
                                            urgency = st.selectbox(f"Urgency Level #{c['id']}",
                                                ["", "Non-Urgent", "48-72 Hours", "Today", "Emergency"],
                                                key=f"urg_{c['id']}")
                                            col_approve, col_reject = st.columns(2)
                                            with col_approve:
                                                if st.button(f"✅ Approve #{c['id']}", key=f"appr_{c['id']}", type="primary"):
                                                    if not review_notes.strip():
                                                        st.error("Please add doctor's notes before approving.")
                                                    else:
                                                        rv, rc = api_patch(f"/consultations/{c['id']}/review", payload={
                                                            "doctor_notes": review_notes.strip(),
                                                            "approved": True,
                                                            "urgency_level": urgency or None
                                                        })
                                                        if rc == 200:
                                                            st.success(f"✅ Consultation #{c['id']} approved!")
                                                            st.rerun()
                                                        else:
                                                            st.error(f"Error: {rv.get('detail','')}")
                                            with col_reject:
                                                if st.button(f"❌ Flag for Revision #{c['id']}", key=f"flag_{c['id']}", type="secondary"):
                                                    if not review_notes.strip():
                                                        st.error("Please add notes explaining the revision needed.")
                                                    else:
                                                        rv, rc = api_patch(f"/consultations/{c['id']}/review", payload={
                                                            "doctor_notes": review_notes.strip(),
                                                            "approved": False,
                                                            "urgency_level": urgency or None
                                                        })
                                                        if rc == 200:
                                                            st.warning(f"Consultation #{c['id']} flagged for revision.")
                                                            st.rerun()
                                                        else:
                                                            st.error(f"Error: {rv.get('detail','')}")
                    with b2:
                        if st.button(f"🗑️ Deactivate", key=f"dp_{p['id']}", type="secondary"):
                            try:
                                r = requests.delete(f"{API_URL}/patients/{p['id']}", headers=_headers(), timeout=8)
                                if r.status_code == 200: st.warning(f"Patient #{p['id']} deactivated."); st.rerun()
                                else: st.error(f"Failed: {r.json().get('detail','')}")
                            except Exception as e:
                                st.error(f"Connection error: {e}")

    # ── Search ──
    elif "🔍" in pt_action:
        st.markdown('<div class="section-title">🔍 Search Patients</div>', unsafe_allow_html=True)
        q = st.text_input("Search by name, email, or phone:")
        if q.strip():
            data = api_get("/patients/search", {"q": q})
            if data:
                results = data.get("results", [])
                st.caption(f"Found {len(results)} result(s)")
                for p in results:
                    st.markdown(f"**#{p['id']} — {p['full_name']}** | Email: {p.get('email','—')} | Phone: {p.get('phone','—')} | Age: {p.get('age','—')} | Consultations: {p.get('total_consultations',0)}")

    # ── Full Profile ──
    elif "📂" in pt_action:
        st.markdown('<div class="section-title">📂 Complete Patient Profile</div>', unsafe_allow_html=True)
        fp_pts = get_patients()
        fp_opts = {f"#{p['id']} — {p['full_name']}": p["id"] for p in fp_pts}
        fp_sel = st.selectbox("Select Patient:", ["— Select —"] + list(fp_opts.keys()))
        if fp_sel != "— Select —":
            pid = fp_opts[fp_sel]
            profile = api_get(f"/patients/{pid}/full-profile")
            if profile:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Age", f"{profile.get('age','?')} yrs")
                    st.metric("Blood Type", profile.get('blood_type','—'))
                with c2:
                    st.metric("BMI", f"{profile.get('bmi','—')} ({profile.get('bmi_category','—')})")
                    st.metric("Gender", profile.get('gender','—'))
                with c3:
                    st.metric("Consultations", profile.get('total_consultations',0))
                    st.metric("Appointments", profile.get('total_appointments',0))

                with st.expander("💊 Current Medications"):
                    meds = profile.get("medications", [])
                    if meds:
                        for m in meds:
                            st.markdown(f"**{m['drug_name']}** {m.get('dosage','')}/{m.get('frequency','')} — {m.get('indication','')}")
                    else: st.caption("No medications recorded")

                with st.expander("⚠️ Allergies"):
                    allergies = profile.get("allergies", [])
                    if allergies:
                        for a in allergies:
                            st.markdown(f"**{a['allergen']}** ({a.get('allergy_type','')}) — Reaction: {a.get('reaction','—')} | Severity: {a.get('severity','—')}")
                    else: st.caption("No allergies recorded")

                with st.expander("🩺 Chronic Conditions"):
                    conds = profile.get("conditions", [])
                    if conds:
                        for c in conds:
                            st.markdown(f"**{c['condition']}** [{c.get('icd10_code','—')}] — Status: {c.get('status','—')}")
                    else: st.caption("No conditions recorded")

                with st.expander("❤️ Latest Vitals"):
                    vitals = profile.get("vitals", [])
                    if vitals:
                        v = vitals[0]
                        cols = st.columns(4)
                        with cols[0]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("blood_pressure","—")}</div><div class="vital-unit">mmHg</div><div class="vital-label">Blood Pressure</div></div>', unsafe_allow_html=True)
                        with cols[1]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("pulse_rate","—")}</div><div class="vital-unit">bpm</div><div class="vital-label">Pulse</div></div>', unsafe_allow_html=True)
                        with cols[2]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("temperature","—")}</div><div class="vital-unit">°C</div><div class="vital-label">Temperature</div></div>', unsafe_allow_html=True)
                        with cols[3]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("spo2","—")}</div><div class="vital-unit">%</div><div class="vital-label">SpO₂</div></div>', unsafe_allow_html=True)
                    else: st.caption("No vitals recorded")

                with st.expander("🧪 Recent Lab Results"):
                    labs = profile.get("lab_results", [])
                    if labs:
                        for l in labs[:10]:
                            status_color = {"High":"🔴","Low":"🟡","Critical":"🚨"}.get(l.get("status",""), "🟢")
                            st.markdown(f"{status_color} **{l['test_name']}**: {l.get('result_value','—')} {l.get('result_unit','')}"
                                        f" (Ref: {l.get('reference_range','—')}) — {l.get('lab_name','—')} · {(l.get('tested_at') or '')[:10]}")
                    else: st.caption("No lab results recorded")

                with st.expander("🧾 Billing Summary"):
                    invs = profile.get("invoices", [])
                    if invs:
                        total = sum(i.get("total_amount",0) for i in invs)
                        paid  = sum(i.get("paid_amount",0)  for i in invs)
                        st.markdown(f"**Total Billed:** ₹{total:.2f} | **Paid:** ₹{paid:.2f} | **Balance:** ₹{total-paid:.2f}")
                        for i in invs[:5]:
                            st.markdown(f"#{i['id']} · ₹{i.get('total_amount',0):.2f} · {i.get('payment_status','—')} · {i.get('invoice_date','—')}")
                    else: st.caption("No invoices")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: DOCTORS
# ══════════════════════════════════════════════════════════════════════════════
with tab_docs:
    _is_admin = st.session_state.get("auth_role", "doctor") == "admin"

    # Admins can add/delete doctors; doctors can only view
    _doc_actions = ["➕ Add Doctor", "📋 All Doctors"] if _is_admin else ["📋 All Doctors"]
    doc_action = st.radio("Action", _doc_actions, horizontal=True, key="radio_action_2")

    if not _is_admin and "➕" in doc_action:
        st.warning("⚠️ Only Admins can add doctors.")

    if "➕" in doc_action and _is_admin:
        st.markdown('<div class="section-title">➕ Register Doctor</div>', unsafe_allow_html=True)
        with st.form("reg_doc", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                d_fn  = st.text_input("First Name *", key="ti_firstname_2")
                d_email= st.text_input("Email", key="ti_email_2")
                d_spec = st.text_input("Specialization", placeholder="Cardiology")
                d_qual = st.text_input("Qualification", placeholder="MBBS, MD, DM")
                d_hosp = st.text_input("Hospital / Clinic")
                d_fee  = st.number_input("Consultation Fee (₹)", value=None, step=50.0, key="ni_confee_1")
            with c2:
                d_ln   = st.text_input("Last Name *", key="ti_lastname_2")
                d_phone= st.text_input("Phone", key="ti_phone_2")
                d_sub  = st.text_input("Sub-specialization", placeholder="Interventional Cardiology")
                d_lic  = st.text_input("License Number")
                d_dept = st.text_input("Department")
                d_exp  = st.number_input("Experience (years)", 0, 60, value=None, step=1)
            with c3:
                d_days = st.text_input("Available Days", placeholder="Mon,Tue,Wed,Thu,Fri")
                d_from = st.text_input("Available From", placeholder="09:00")
                d_to   = st.text_input("Available To", placeholder="17:00")
                d_lang = st.text_input("Languages", placeholder="English, Hindi, Tamil")
            d_bio = st.text_area("Bio / About", height=80)
            if st.form_submit_button("✅ Register Doctor", type="primary", use_container_width=True):
                if not d_fn.strip() or not d_ln.strip():
                    st.error("First and Last Name required")
                else:
                    payload = {"first_name": d_fn.strip(), "last_name": d_ln.strip()}
                    for k, v in [("email",d_email),("phone",d_phone),("specialization",d_spec),
                                  ("sub_specialization",d_sub),("qualification",d_qual),
                                  ("license_number",d_lic),("hospital",d_hosp),("department",d_dept),
                                  ("experience_years",d_exp),("consultation_fee",d_fee),
                                  ("available_days",d_days),("available_from",d_from),
                                  ("available_to",d_to),("languages",d_lang),("bio",d_bio)]:
                        if v: payload[k] = v
                    data, code = api_post("/doctors", payload)
                    if code == 201:
                        st.success(f"✅ Dr. {d_fn} {d_ln} registered! ID: #{data['doctor']['id']}")
                    else:
                        st.error(f"❌ {data.get('detail','Error')}")

    else:
        st.markdown('<div class="section-title">📋 All Doctors</div>', unsafe_allow_html=True)
        if st.button("🔄 Refresh", key="btn_refresh_2"): st.rerun()
        docs_data = api_get("/doctors")
        if docs_data:
            for d in docs_data.get("doctors", []):
                with st.expander(f"👨‍⚕️ Dr. {d['first_name']} {d['last_name']} — {d.get('specialization','—')} | {d.get('hospital','—')}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Email:** {d.get('email','—')}")
                        st.markdown(f"**Phone:** {d.get('phone','—')}")
                        st.markdown(f"**Qualification:** {d.get('qualification','—')}")
                        st.markdown(f"**Sub-spec:** {d.get('sub_specialization','—')}")
                        st.markdown(f"**License:** {d.get('license_number','—')}")
                    with c2:
                        st.markdown(f"**Hospital:** {d.get('hospital','—')}")
                        st.markdown(f"**Department:** {d.get('department','—')}")
                        st.markdown(f"**Experience:** {d.get('experience_years','—')} years")
                        st.markdown(f"**Fee:** ₹{d.get('consultation_fee','—')}")
                        st.markdown(f"**Available:** {d.get('available_days','—')} · {d.get('available_from','')}-{d.get('available_to','')}")
                    if d.get("bio"): st.markdown(f"**Bio:** {d['bio']}")
                    if _is_admin:
                        if st.button(f"🗑️ Deactivate Dr. {d['first_name']}", key=f"dd_{d['id']}", type="secondary"):
                            try:
                                r = requests.delete(f"{API_URL}/doctors/{d['id']}", headers=_headers(), timeout=8)
                                if r.status_code == 200: st.warning("Doctor deactivated."); st.rerun()
                                else: st.error(f"Failed: {r.json().get('detail','')}")
                            except Exception as e:
                                st.error(f"Connection error: {e}")
                    else:
                        st.caption("🔒 Admin access required to deactivate doctors")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: APPOINTMENTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_appts:
    appt_action = st.radio("Action", ["📅 Book Appointment", "📋 View Appointments", "✅ Update Status"], horizontal=True, key="radio_action_3")

    if "📅" in appt_action:
        st.markdown('<div class="section-title">📅 Book New Appointment</div>', unsafe_allow_html=True)
        with st.form("book_appt", clear_on_submit=True):
            all_pts2 = get_patients(); all_docs2 = get_doctors()
            pt_opts2 = patient_options(all_pts2); doc_opts2 = doctor_options(all_docs2)
            c1, c2 = st.columns(2)
            with c1:
                a_pt  = st.selectbox("Patient *", list(pt_opts2.keys()), key="sel_patient")
                a_date= st.text_input("Date (YYYY-MM-DD) *", value=str(date.today()))
                a_type= st.selectbox("Type", ["In-person","Telemedicine","Follow-up","Emergency"], key="sel_type")
                a_room= st.text_input("Room / Location", placeholder="Room 204 / Online")
            with c2:
                a_doc = st.selectbox("Doctor", list(doc_opts2.keys()))
                a_time= st.text_input("Time (HH:MM)", placeholder="10:30")
                a_dur = st.number_input("Duration (mins)", 15, 120, 30, step=15)
                a_fup = st.checkbox("Follow-up Required?")
            a_reason = st.text_area("Reason for Visit", height=70)
            a_notes  = st.text_area("Additional Notes", height=100)
            if st.form_submit_button("📅 Book Appointment", type="primary", use_container_width=True):
                pid2 = pt_opts2.get(a_pt)
                did2 = doc_opts2.get(a_doc)
                if not pid2: st.error("Select a valid patient")
                elif not a_date: st.error("Date is required")
                else:
                    payload = {"patient_id": pid2, "appointment_date": a_date,
                               "appointment_type": a_type, "duration_mins": int(a_dur),
                               "follow_up_required": a_fup}
                    if did2: payload["doctor_id"] = did2
                    if a_time:   payload["appointment_time"] = a_time
                    if a_room:   payload["room_number"] = a_room
                    if a_reason: payload["reason"] = a_reason
                    if a_notes:  payload["notes"]  = a_notes
                    data, code = api_post("/appointments", payload)
                    if code == 201:
                        st.success(f"✅ Appointment booked! ID: #{data['appointment']['id']}")
                    else:
                        st.error(f"❌ {data.get('detail','Error')}")

    elif "📋" in appt_action:
        st.markdown('<div class="section-title">📋 Patient Appointments</div>', unsafe_allow_html=True)
        va_pts = get_patients()
        va_opts = patient_options(va_pts)
        va_sel = st.selectbox("Select Patient:", list(va_opts.keys()), key="sel_selpatient")
        va_pid = va_opts.get(va_sel)
        if va_pid:
            adata = api_get(f"/patients/{va_pid}/appointments")
            if adata:
                for a in adata.get("appointments", []):
                    status_cls = {"Completed":"completed","Cancelled":"cancelled","No-show":"cancelled"}.get(a.get("status",""),"scheduled")
                    st.markdown(f"""<div class="data-card">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                        <div>
                          <strong style="color:#dde6f0">#{a['id']} · {a.get('appointment_date','—')} at {a.get('appointment_time','—')}</strong>
                          <div style="font-size:.82rem;color:#5a7a9a;margin-top:.2rem">
                            👨‍⚕️ {a.get('doctor_name') or 'No doctor'} · {a.get('appointment_type','—')} · {a.get('duration_mins',30)} min
                          </div>
                          <div style="font-size:.82rem;color:#4a6480">📝 {a.get('reason') or '—'}</div>
                        </div>
                        <span class="badge {status_cls}">{a.get('status','—')}</span>
                      </div></div>""", unsafe_allow_html=True)

    else:
        st.markdown('<div class="section-title">✅ Update Appointment Status</div>', unsafe_allow_html=True)
        appt_id_inp = st.number_input("Appointment ID", min_value=1, step=1)
        new_status  = st.selectbox("New Status", ["Scheduled","Completed","Cancelled","No-show"])
        if st.button("✅ Update Status", type="primary"):
            r, code = api_patch(f"/appointments/{appt_id_inp}/status", params={"status": new_status})
            if code == 200: st.success(f"Appointment #{appt_id_inp} → {new_status}")
            else: st.error(f"Error: {r.get('detail','')}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: MEDICATIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_meds:
    med_action = st.radio("Action", ["➕ Add Medication", "💊 View Medications"], horizontal=True, key="radio_action_4")

    if "➕" in med_action:
        st.markdown('<div class="section-title">➕ Add Patient Medication</div>', unsafe_allow_html=True)
        with st.form("add_med", clear_on_submit=True):
            m_pts = get_patients(); m_opts = patient_options(m_pts)
            m_pt_sel = st.selectbox("Patient *", list(m_opts.keys()), key="sel_patient_2")
            c1, c2, c3 = st.columns(3)
            with c1:
                m_drug= st.text_input("Drug Name *", placeholder="Metformin")
                m_dose= st.text_input("Dosage", placeholder="500mg")
                m_start= st.text_input("Start Date (YYYY-MM-DD)", value=str(date.today()))
                m_indication= st.text_area("Indication (why prescribed)", height=70)
            with c2:
                m_generic= st.text_input("Generic Name", placeholder="Metformin HCl")
                m_freq   = st.text_input("Frequency", placeholder="Twice daily")
                m_end    = st.text_input("End Date (YYYY-MM-DD)", placeholder="Optional")
                m_side   = st.text_area("Known Side Effects", height=70)
            with c3:
                m_route  = st.selectbox("Route", ["Oral","IV","Topical","Inhaled","Sublingual","Injection","Transdermal"])
                m_pby    = st.text_input("Prescribed By", placeholder="Dr. Name")
                m_refill = st.text_input("Refill Date (YYYY-MM-DD)", placeholder="Optional")
                m_current= st.checkbox("Currently Active", value=True)
            m_notes = st.text_area("Notes", height=100, key="ta_notes")
            if st.form_submit_button("💊 Save Medication", type="primary", use_container_width=True):
                pid3 = m_opts.get(m_pt_sel)
                if not pid3: st.error("Select a valid patient")
                elif not m_drug.strip(): st.error("Drug name required")
                else:
                    payload = {"patient_id": pid3, "drug_name": m_drug.strip(),
                               "route": m_route, "is_current": m_current}
                    for k, v in [("generic_name",m_generic),("dosage",m_dose),("frequency",m_freq),
                                  ("prescribed_by",m_pby),("start_date",m_start),("end_date",m_end),
                                  ("refill_date",m_refill),("indication",m_indication),
                                  ("side_effects",m_side),("notes",m_notes)]:
                        if v: payload[k] = v
                    data, code = api_post("/medications", payload)
                    if code == 201: st.success(f"✅ Medication '{m_drug}' saved!")
                    else: st.error(f"❌ {data.get('detail','Error')}")

    else:
        st.markdown('<div class="section-title">💊 Patient Medication History</div>', unsafe_allow_html=True)
        vm_pts = get_patients(); vm_opts = patient_options(vm_pts)
        vm_sel = st.selectbox("Patient:", list(vm_opts.keys()))
        vm_pid = vm_opts.get(vm_sel)
        show_all = st.checkbox("Show All (including past)", value=False)
        if vm_pid:
            mdata = api_get(f"/patients/{vm_pid}/medications", {"current_only": str(not show_all).lower()})
            if mdata:
                for m in mdata.get("medications", []):
                    status_cls = "green" if m.get("is_current") else ""
                    st.markdown(f"""<div class="data-card">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                        <div>
                          <strong style="color:#dde6f0">{m['drug_name']}</strong>
                          {f'<span class="tag green">Active</span>' if m.get("is_current") else '<span class="tag">Discontinued</span>'}
                          <div style="font-size:.82rem;color:#5a7a9a;margin-top:.2rem">
                            💊 {m.get('dosage','—')} · {m.get('frequency','—')} · {m.get('route','Oral')}
                          </div>
                          <div style="font-size:.82rem;color:#4a6480">
                            📋 {m.get('indication') or '—'} · 👨‍⚕️ {m.get('prescribed_by') or '—'}
                          </div>
                          <div style="font-size:.8rem;color:#3a5a7a">
                            📅 {m.get('start_date','—')} → {m.get('end_date','Ongoing')}
                            {f" · Refill: {m.get('refill_date','—')}" if m.get('refill_date') else ''}
                          </div>
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8: LAB RESULTS
# ══════════════════════════════════════════════════════════════════════════════
with tab_labs:
    lab_action = st.radio("Action", ["➕ Add Lab Result", "🧪 View Results"], horizontal=True, key="radio_action_5")

    if "➕" in lab_action:
        st.markdown('<div class="section-title">➕ Add Lab Result</div>', unsafe_allow_html=True)
        with st.form("add_lab", clear_on_submit=True):
            l_pts = get_patients(); l_opts = patient_options(l_pts)
            l_pt_sel = st.selectbox("Patient *", list(l_opts.keys()), key="sel_patient_3")
            c1, c2, c3 = st.columns(3)
            with c1:
                l_test = st.text_input("Test Name *", placeholder="Hemoglobin")
                l_val  = st.text_input("Result Value", placeholder="12.5")
                l_ref  = st.text_input("Reference Range", placeholder="12.0-16.0")
            with c2:
                l_cat  = st.selectbox("Category", ["","Hematology","Biochemistry","Lipid Profile","Thyroid","Diabetes","Liver Function","Kidney Function","Cardiac","Urine","Microbiology","Hormones","Vitamins","Imaging","Other"])
                l_unit = st.text_input("Unit", placeholder="g/dL")
                l_stat = st.selectbox("Status", ["","Normal","High","Low","Critical"], key="sel_status")
            with c3:
                l_lab  = st.text_input("Lab Name", placeholder="Apollo Diagnostics")
                l_date = st.text_input("Test Date (YYYY-MM-DD)", value=str(date.today()))
            l_notes = st.text_area("Notes", height=100, key="ta_notes_2")
            if st.form_submit_button("🧪 Save Lab Result", type="primary", use_container_width=True):
                pid4 = l_opts.get(l_pt_sel)
                if not pid4: st.error("Select a patient")
                elif not l_test.strip(): st.error("Test name required")
                else:
                    payload = {"patient_id": pid4, "test_name": l_test.strip()}
                    for k, v in [("test_category",l_cat),("result_value",l_val),("result_unit",l_unit),
                                  ("reference_range",l_ref),("status",l_stat),("lab_name",l_lab),
                                  ("tested_at",l_date),("notes",l_notes)]:
                        if v: payload[k] = v
                    data, code = api_post("/lab-results", payload)
                    if code == 201: st.success(f"✅ Lab result for '{l_test}' saved!")
                    else: st.error(f"❌ {data.get('detail','')}")

    else:
        st.markdown('<div class="section-title">🧪 Patient Lab Results</div>', unsafe_allow_html=True)
        vl_pts = get_patients(); vl_opts = patient_options(vl_pts)
        vl_sel = st.selectbox("Patient:", list(vl_opts.keys()), key="vlab_sel")
        vl_pid = vl_opts.get(vl_sel)
        if vl_pid:
            ldata = api_get(f"/patients/{vl_pid}/lab-results")
            if ldata:
                for l in ldata.get("lab_results", []):
                    status_icon = {"High":"🔴","Low":"🟡","Critical":"🚨","Normal":"🟢"}.get(l.get("status",""),"⚪")
                    st.markdown(f"""<div class="data-card">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                        <div>
                          <strong style="color:#dde6f0">{status_icon} {l['test_name']}</strong>
                          <span class="tag" style="margin-left:.5rem">{l.get('test_category','—')}</span>
                          <div style="font-size:.85rem;color:#4db8ff;margin-top:.2rem;font-weight:600">
                            {l.get('result_value','—')} {l.get('result_unit','')}
                          </div>
                          <div style="font-size:.8rem;color:#5a7a9a">
                            Ref: {l.get('reference_range','—')} · Lab: {l.get('lab_name','—')} · {(l.get('tested_at') or '')[:10]}
                          </div>
                          {f'<div style="font-size:.8rem;color:#4a6480">📝 {l["notes"]}</div>' if l.get("notes") else ''}
                        </div>
                      </div></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9: VITAL SIGNS
# ══════════════════════════════════════════════════════════════════════════════
with tab_vitals:
    v_action = st.radio("Action", ["➕ Record Vitals", "❤️ View Vitals"], horizontal=True, key="radio_action_6")

    if "➕" in v_action:
        st.markdown('<div class="section-title">➕ Record Vital Signs</div>', unsafe_allow_html=True)
        with st.form("add_vitals", clear_on_submit=True):
            v_pts = get_patients(); v_opts = patient_options(v_pts)
            v_pt_sel = st.selectbox("Patient *", list(v_opts.keys()), key="sel_patient_4")
            c1, c2, c3 = st.columns(3)
            with c1:
                v_sys   = st.number_input("BP Systolic (mmHg)", 0, 300, value=None, step=1)
                v_dia   = st.number_input("BP Diastolic (mmHg)", 0, 200, value=None, step=1)
                v_pulse = st.number_input("Pulse Rate (bpm)", 0, 300, value=None, step=1)
            with c2:
                v_rr    = st.number_input("Respiratory Rate (breaths/min)", 0, 60, value=None, step=1)
                v_temp  = st.number_input("Temperature (°C)", 30.0, 45.0, value=None, step=0.1)
                v_spo2  = st.number_input("SpO₂ (%)", 0.0, 100.0, value=None, step=0.5)
            with c3:
                v_glucose= st.number_input("Blood Glucose (mg/dL)", 0.0, 600.0, value=None, step=0.5)
                v_wt    = st.number_input("Weight (kg)", value=None, step=0.5, key="ni_weight_3")
                v_pain  = st.number_input("Pain Scale (0–10)", 0, 10, value=None, step=1)
            v_notes = st.text_area("Notes", height=100, key="ta_notes_3")
            if st.form_submit_button("❤️ Save Vitals", type="primary", use_container_width=True):
                pid5 = v_opts.get(v_pt_sel)
                if not pid5: st.error("Select a patient")
                else:
                    payload = {"patient_id": pid5}
                    for k, v2 in [("bp_systolic",v_sys),("bp_diastolic",v_dia),("pulse_rate",v_pulse),
                                   ("respiratory_rate",v_rr),("temperature",v_temp),("spo2",v_spo2),
                                   ("blood_glucose",v_glucose),("weight",v_wt),("pain_scale",v_pain),("notes",v_notes)]:
                        if v2 is not None: payload[k] = v2
                    data, code = api_post("/vitals", payload)
                    if code == 201: st.success("✅ Vitals recorded successfully!")
                    else: st.error(f"❌ {data.get('detail','')}")

    else:
        st.markdown('<div class="section-title">❤️ Vital Signs History</div>', unsafe_allow_html=True)
        vv_pts = get_patients(); vv_opts = patient_options(vv_pts)
        vv_sel = st.selectbox("Patient:", list(vv_opts.keys()), key="vv_sel")
        vv_pid = vv_opts.get(vv_sel)
        if vv_pid:
            vdata = api_get(f"/patients/{vv_pid}/vitals")
            if vdata and vdata.get("vitals"):
                for v in vdata["vitals"]:
                    st.markdown(f"**📅 {(v.get('recorded_at') or '')[:16]}** — {v.get('bp_status','')}")
                    cols = st.columns(5)
                    with cols[0]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("blood_pressure","—")}</div><div class="vital-unit">mmHg</div><div class="vital-label">Blood Pressure</div></div>', unsafe_allow_html=True)
                    with cols[1]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("pulse_rate","—")}</div><div class="vital-unit">bpm</div><div class="vital-label">Pulse</div></div>', unsafe_allow_html=True)
                    with cols[2]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("temperature","—")}</div><div class="vital-unit">°C</div><div class="vital-label">Temp</div></div>', unsafe_allow_html=True)
                    with cols[3]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("spo2","—")}</div><div class="vital-unit">%</div><div class="vital-label">SpO₂</div></div>', unsafe_allow_html=True)
                    with cols[4]: st.markdown(f'<div class="vital-card"><div class="vital-val">{v.get("blood_glucose","—")}</div><div class="vital-unit">mg/dL</div><div class="vital-label">Glucose</div></div>', unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("No vitals recorded for this patient.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 10: MEDICAL RECORDS
# ══════════════════════════════════════════════════════════════════════════════
with tab_records:
    mr_action = st.radio("Action", ["➕ Add Record", "📁 View Records"], horizontal=True, key="radio_action_7")

    if "➕" in mr_action:
        st.markdown('<div class="section-title">➕ Add Medical Record</div>', unsafe_allow_html=True)
        with st.form("add_record", clear_on_submit=True):
            r_pts = get_patients(); r_opts = patient_options(r_pts)
            r_pt_sel = st.selectbox("Patient *", list(r_opts.keys()), key="sel_patient_5")
            c1, c2 = st.columns(2)
            with c1:
                r_type  = st.selectbox("Record Type *", ["Lab Report","X-Ray","MRI","CT Scan","Ultrasound","ECG","Prescription","Discharge Summary","Vaccination Record","Medical Certificate","Other"])
                r_title = st.text_input("Title *", placeholder="CBC Blood Test Report")
                r_by    = st.text_input("Issued By", placeholder="Apollo Hospital / Dr. Name")
                r_date  = st.text_input("Issue Date (YYYY-MM-DD)", value=str(date.today()))
            with c2:
                r_file  = st.text_input("File Name (if digital)", placeholder="cbc_report_jan2025.pdf")
                r_ftype = st.selectbox("File Type", ["","PDF","JPG","PNG","DICOM","DOCX","Other"])
                r_tags  = st.text_input("Tags (comma-separated)", placeholder="blood,cbc,hematology")
            r_desc = st.text_area("Description / Summary", height=80)
            if st.form_submit_button("📁 Save Record", type="primary", use_container_width=True):
                pid6 = r_opts.get(r_pt_sel)
                if not pid6: st.error("Select a patient")
                elif not r_title.strip(): st.error("Title required")
                else:
                    payload = {"patient_id": pid6, "record_type": r_type, "title": r_title.strip()}
                    for k, v in [("description",r_desc),("file_name",r_file),("file_type",r_ftype),
                                  ("issued_by",r_by),("issued_date",r_date),("tags",r_tags)]:
                        if v: payload[k] = v
                    data, code = api_post("/medical-records", payload)
                    if code == 201: st.success(f"✅ Record '{r_title}' saved!")
                    else: st.error(f"❌ {data.get('detail','')}")

    else:
        st.markdown('<div class="section-title">📁 Patient Medical Records</div>', unsafe_allow_html=True)
        vr_pts = get_patients(); vr_opts = patient_options(vr_pts)
        vr_sel = st.selectbox("Patient:", list(vr_opts.keys()), key="vr_sel")
        vr_pid = vr_opts.get(vr_sel)
        if vr_pid:
            rdata = api_get(f"/patients/{vr_pid}/medical-records")
            if rdata:
                for r in rdata.get("records", []):
                    type_icons = {"Lab Report":"🧪","X-Ray":"🦴","MRI":"🧠","CT Scan":"💻","ECG":"❤️","Prescription":"💊","Discharge Summary":"🏥"}
                    icon = type_icons.get(r.get("record_type",""),"📄")
                    tags_html = "".join([f'<span class="tag">{t.strip()}</span>' for t in (r.get("tags") or [])])
                    st.markdown(f"""<div class="data-card">
                      <strong>{icon} {r.get('title','—')}</strong>
                      <span class="tag purple" style="margin-left:.5rem">{r.get('record_type','—')}</span>
                      <div style="font-size:.82rem;color:#5a7a9a;margin-top:.3rem">
                        📅 {r.get('issued_date','—')} · 🏥 {r.get('issued_by','—')} · 📄 {r.get('file_name','No file') or 'No file'}
                      </div>
                      {f'<div style="font-size:.82rem;color:#4a6480;margin-top:.2rem">{r["description"]}</div>' if r.get("description") else ''}
                      <div style="margin-top:.4rem">{tags_html}</div>
                    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 11: ALLERGIES & CONDITIONS
# ══════════════════════════════════════════════════════════════════════════════
with tab_ac:
    ac_sub = st.radio("Action", ["⚠️ Add Allergy", "🩺 Add Condition", "📋 View Both"], horizontal=True, key="radio_action_8")

    if "⚠️ Add" in ac_sub:
        st.markdown('<div class="section-title">⚠️ Add Allergy</div>', unsafe_allow_html=True)
        with st.form("add_allergy", clear_on_submit=True):
            al_pts = get_patients(); al_opts = patient_options(al_pts)
            al_pt_sel = st.selectbox("Patient *", list(al_opts.keys()), key="sel_patient_6")
            c1, c2 = st.columns(2)
            with c1:
                al_name = st.text_input("Allergen *", placeholder="Penicillin")
                al_type = st.selectbox("Type", ["Drug","Food","Environmental","Latex","Insect","Other"], key="sel_type_2")
                al_sev  = st.selectbox("Severity", ["Mild","Moderate","Severe","Life-threatening"])
            with c2:
                al_rxn  = st.text_input("Reaction", placeholder="Anaphylaxis, Rash, Hives...")
                al_date = st.text_input("Date Noted (YYYY-MM-DD)", placeholder="Optional")
            al_notes = st.text_area("Notes", height=100, key="ta_notes_4")
            if st.form_submit_button("⚠️ Save Allergy", type="primary", use_container_width=True):
                pid7 = al_opts.get(al_pt_sel)
                if not pid7: st.error("Select a patient")
                elif not al_name.strip(): st.error("Allergen required")
                else:
                    payload = {"patient_id": pid7, "allergen": al_name.strip(),
                               "allergy_type": al_type, "severity": al_sev}
                    if al_rxn:  payload["reaction"] = al_rxn
                    if al_date: payload["noted_date"] = al_date
                    if al_notes:payload["notes"] = al_notes
                    data, code = api_post("/allergies", payload)
                    if code == 201: st.success(f"✅ Allergy '{al_name}' saved!")
                    else: st.error(f"❌ {data.get('detail','')}")

    elif "🩺 Add" in ac_sub:
        st.markdown('<div class="section-title">🩺 Add Chronic Condition</div>', unsafe_allow_html=True)
        with st.form("add_cond", clear_on_submit=True):
            co_pts = get_patients(); co_opts = patient_options(co_pts)
            co_pt_sel = st.selectbox("Patient *", list(co_opts.keys()), key="sel_patient_7")
            c1, c2 = st.columns(2)
            with c1:
                co_cond = st.text_input("Condition *", placeholder="Type 2 Diabetes Mellitus")
                co_icd  = st.text_input("ICD-10 Code", placeholder="E11")
                co_date = st.text_input("Diagnosed Date (YYYY-MM-DD)", placeholder="Optional")
            with c2:
                co_by   = st.text_input("Diagnosed By", placeholder="Dr. Name / Hospital")
                co_stat = st.selectbox("Status", ["Active","Controlled","Resolved","In Remission"], key="sel_status_2")
            co_treat = st.text_area("Treatment / Management", height=70)
            co_notes = st.text_area("Notes", height=100, key="ta_notes_5")
            if st.form_submit_button("🩺 Save Condition", type="primary", use_container_width=True):
                pid8 = co_opts.get(co_pt_sel)
                if not pid8: st.error("Select a patient")
                elif not co_cond.strip(): st.error("Condition required")
                else:
                    payload = {"patient_id": pid8, "condition": co_cond.strip(), "status": co_stat}
                    for k, v in [("icd10_code",co_icd),("diagnosed_date",co_date),("diagnosed_by",co_by),
                                  ("treatment",co_treat),("notes",co_notes)]:
                        if v: payload[k] = v
                    data, code = api_post("/conditions", payload)
                    if code == 201: st.success(f"✅ Condition '{co_cond}' saved!")
                    else: st.error(f"❌ {data.get('detail','')}")

    else:
        st.markdown('<div class="section-title">📋 Patient Allergies & Conditions</div>', unsafe_allow_html=True)
        vc_pts = get_patients(); vc_opts = patient_options(vc_pts)
        vc_sel = st.selectbox("Patient:", list(vc_opts.keys()), key="vc_sel")
        vc_pid = vc_opts.get(vc_sel)
        if vc_pid:
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**⚠️ Allergies**")
                adata2 = api_get(f"/patients/{vc_pid}/allergies")
                if adata2:
                    for a in adata2.get("allergies", []):
                        sev_color = {"Mild":"green","Moderate":"orange","Severe":"red","Life-threatening":"red"}.get(a.get("severity",""), "")
                        st.markdown(f"""<div class="data-card">
                          <strong style="color:#ff8a80">⚠️ {a['allergen']}</strong>
                          <span class="tag {sev_color}" style="margin-left:.5rem">{a.get('severity','—')}</span>
                          <span class="tag" style="margin-left:.25rem">{a.get('allergy_type','—')}</span>
                          <div style="font-size:.82rem;color:#5a7a9a;margin-top:.25rem">Reaction: {a.get('reaction','—')}</div>
                        </div>""", unsafe_allow_html=True)
                else: st.caption("No allergies")
            with col_b:
                st.markdown("**🩺 Chronic Conditions**")
                cdata2 = api_get(f"/patients/{vc_pid}/conditions")
                if cdata2:
                    for c in cdata2.get("conditions", []):
                        stat_cls = {"Active":"red","Controlled":"orange","Resolved":"green","In Remission":"green"}.get(c.get("status",""),"")
                        st.markdown(f"""<div class="data-card">
                          <strong style="color:#dde6f0">{c['condition']}</strong>
                          {f'<span class="tag purple" style="margin-left:.5rem">{c["icd10_code"]}</span>' if c.get("icd10_code") else ''}
                          <span class="badge {stat_cls}" style="margin-left:.5rem">{c.get('status','—')}</span>
                          <div style="font-size:.82rem;color:#5a7a9a;margin-top:.25rem">Dx: {c.get('diagnosed_date','—')} by {c.get('diagnosed_by','—')}</div>
                        </div>""", unsafe_allow_html=True)
                else: st.caption("No conditions")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 12: BILLING
# ══════════════════════════════════════════════════════════════════════════════
with tab_billing:
    bill_action = st.radio("Action", ["🧾 Create Invoice", "💰 View Invoices", "✅ Record Payment"], horizontal=True, key="radio_action_9")

    if "🧾" in bill_action:
        st.markdown('<div class="section-title">🧾 Create Invoice</div>', unsafe_allow_html=True)
        with st.form("create_invoice", clear_on_submit=True):
            b_pts = get_patients(); b_opts = patient_options(b_pts)
            b_pt_sel = st.selectbox("Patient *", list(b_opts.keys()), key="sel_patient_8")
            c1, c2, c3 = st.columns(3)
            with c1:
                b_con_fee = st.number_input("Consultation Fee (₹)", 0.0, 100000.0, value=0.0, step=50.0, key="ni_confee_2")
                b_lab_fee = st.number_input("Lab Charges (₹)", 0.0, 100000.0, value=0.0, step=50.0)
            with c2:
                b_med_fee = st.number_input("Medication Charges (₹)", 0.0, 100000.0, value=0.0, step=10.0)
                b_other   = st.number_input("Other Charges (₹)", 0.0, 100000.0, value=0.0, step=10.0)
            with c3:
                b_disc    = st.number_input("Discount (₹)", 0.0, 50000.0, value=0.0, step=10.0)
                b_tax     = st.number_input("Tax (₹)", 0.0, 20000.0, value=0.0, step=10.0)

            subtotal = b_con_fee + b_lab_fee + b_med_fee + b_other
            total    = subtotal - b_disc + b_tax
            st.markdown(f"""<div class="data-card">
              <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:1rem;text-align:center">
                <div><div style="font-size:.72rem;color:#5a7a9a">Subtotal</div><div style="font-size:1.2rem;color:#dde6f0">₹{subtotal:.2f}</div></div>
                <div><div style="font-size:.72rem;color:#5a7a9a">Discount</div><div style="font-size:1.2rem;color:#6ee7b7">-₹{b_disc:.2f}</div></div>
                <div><div style="font-size:.72rem;color:#5a7a9a">Tax</div><div style="font-size:1.2rem;color:#fbbf24">+₹{b_tax:.2f}</div></div>
                <div><div style="font-size:.72rem;color:#5a7a9a">Total Due</div><div style="font-size:1.4rem;color:#4db8ff;font-weight:700">₹{total:.2f}</div></div>
              </div></div>""", unsafe_allow_html=True)

            b_method = st.selectbox("Payment Method", ["","Cash","Card","UPI","Insurance","Net Banking","Cheque"], key="sel_paymethod")
            b_ins    = st.checkbox("Insurance Claim?")
            b_due    = st.text_input("Due Date (YYYY-MM-DD)", placeholder="Optional")
            b_notes  = st.text_area("Notes", height=100, key="ta_notes_6")
            if st.form_submit_button("🧾 Create Invoice", type="primary", use_container_width=True):
                pid9 = b_opts.get(b_pt_sel)
                if not pid9: st.error("Select a patient")
                else:
                    payload = {"patient_id": pid9, "consultation_fee": b_con_fee,
                               "lab_charges": b_lab_fee, "medication_charges": b_med_fee,
                               "other_charges": b_other, "discount": b_disc, "tax": b_tax,
                               "total_amount": total, "insurance_claim": b_ins}
                    if b_method: payload["payment_method"] = b_method
                    if b_due:    payload["due_date"] = b_due
                    if b_notes:  payload["notes"] = b_notes
                    data, code = api_post("/invoices", payload)
                    if code == 201:
                        inv = data["invoice"]
                        st.success(f"✅ Invoice **{inv.get('invoice_number')}** created! Total: ₹{inv.get('total_amount',0):.2f}")
                    else:
                        st.error(f"❌ {data.get('detail','')}")

    elif "💰" in bill_action:
        st.markdown('<div class="section-title">💰 Patient Invoices</div>', unsafe_allow_html=True)
        vi_pts = get_patients(); vi_opts = patient_options(vi_pts)
        vi_sel = st.selectbox("Patient:", list(vi_opts.keys()), key="vi_sel")
        vi_pid = vi_opts.get(vi_sel)
        if vi_pid:
            idata = api_get(f"/patients/{vi_pid}/invoices")
            if idata:
                tb  = idata.get("total_billed", 0)
                tp  = idata.get("total_paid", 0)
                tbd = idata.get("balance_due", 0)
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(f'<div class="stat-card blue"><div class="stat-value" style="font-size:1.5rem">₹{tb:.0f}</div><div class="stat-label">Total Billed</div></div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="stat-card green"><div class="stat-value" style="font-size:1.5rem">₹{tp:.0f}</div><div class="stat-label">Total Paid</div></div>', unsafe_allow_html=True)
                with c3: st.markdown(f'<div class="stat-card red"><div class="stat-value" style="font-size:1.5rem">₹{tbd:.0f}</div><div class="stat-label">Balance Due</div></div>', unsafe_allow_html=True)
                st.markdown("")
                for inv in idata.get("invoices", []):
                    status_cls = {"Paid":"paid","Cancelled":"cancelled","Pending":"pending","Partial":"orange"}.get(inv.get("payment_status",""),"pending")
                    st.markdown(f"""<div class="data-card">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                        <div>
                          <strong style="color:#dde6f0">{inv.get('invoice_number','—')}</strong>
                          <div style="font-size:.82rem;color:#5a7a9a;margin-top:.2rem">
                            📅 {inv.get('invoice_date','—')} · Due: {inv.get('due_date','—')}
                          </div>
                          <div style="font-size:.82rem;color:#4db8ff;margin-top:.1rem">
                            Total: ₹{inv.get('total_amount',0):.2f} · Paid: ₹{inv.get('paid_amount',0):.2f} · Balance: ₹{inv.get('balance_due',0):.2f}
                          </div>
                          <div style="font-size:.8rem;color:#4a6480">
                            💳 {inv.get('payment_method') or 'Not specified'} · Insurance: {'Yes' if inv.get('insurance_claim') else 'No'}
                          </div>
                        </div>
                        <span class="badge {status_cls}">{inv.get('payment_status','—')}</span>
                      </div></div>""", unsafe_allow_html=True)

    else:
        st.markdown('<div class="section-title">✅ Record Payment</div>', unsafe_allow_html=True)
        inv_id_inp  = st.number_input("Invoice ID", min_value=1, step=1)
        pay_amount  = st.number_input("Amount Paid (₹)", min_value=0.0, step=10.0)
        pay_method  = st.selectbox("Payment Method", ["Cash","Card","UPI","Insurance","Net Banking","Cheque"], key="sel_paymethod_2")
        if st.button("✅ Record Payment", type="primary"):
            r, code = api_patch(f"/invoices/{inv_id_inp}/payment",
                                params={"paid_amount": pay_amount, "method": pay_method})
            if code == 200:
                st.success(f"✅ Payment recorded! Invoice #{inv_id_inp} — Status: **{r.get('invoice',{}).get('payment_status')}**")
            else:
                st.error(f"Error: {r.get('detail','')}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 13: AUDIT LOG (admin only)
# ══════════════════════════════════════════════════════════════════════════════
with tab_audit:
    _audit_role = st.session_state.get("auth_role", "doctor")
    if _audit_role != "admin":
        st.markdown("""
        <div class="alert-danger">
          <strong>🔒 Admin Access Required</strong><br>
          The audit log is restricted to administrators only for DISHA compliance.
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-title">🔒 Audit Log — DISHA Compliance</div>', unsafe_allow_html=True)

        with st.expander("⚙️ User Management — Promote / Demote Roles"):
            st.markdown('<div style="font-size:.82rem;color:#fbbf24;margin-bottom:.5rem">⚠️ Use with caution.</div>', unsafe_allow_html=True)
            pm_email = st.text_input("User Email to Promote", placeholder="doctor@hospital.com", key="pm_email")
            pm_role  = st.selectbox("New Role", ["doctor", "patient", "admin"], key="pm_role")
            if st.button("🔧 Update Role", type="primary", key="pm_btn"):
                if not pm_email.strip():
                    st.error("Enter a user email.")
                else:
                    try:
                        r = requests.post(f"{API_URL}/admin/promote",
                                          params={"email": pm_email.strip(), "new_role": pm_role},
                                          headers=_headers(), timeout=8)
                        if r.status_code == 200:
                            st.success(f"✅ {pm_email} is now {pm_role}")
                        else:
                            st.error(f"❌ {r.json().get('detail', 'Failed')}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")
        st.divider()
        audit_limit = st.slider("Records to load", 20, 200, 50, step=10)
        if st.button("🔄 Load Audit Log", type="primary"):
            adata = api_get("/audit-logs", {"limit": audit_limit})
            if adata:
                logs = adata.get("logs", [])
                st.caption(f"Showing {len(logs)} most recent audit entries")
                for log in logs:
                    action_color = {"CREATE": "#6ee7b7", "DELETE": "#ff8a80", "VIEW": "#4db8ff",
                                    "UPDATE": "#fbbf24", "AI_DIAGNOSIS": "#c084fc"}.get(
                        log.get("action","").split("_")[0], "#8ba4bc")
                    st.markdown(f"""<div class="data-card">
                      <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem">
                        <div>
                          <strong style="color:{action_color}">{log.get("action","—")}</strong>
                          <span style="color:#5a7a9a;font-size:.8rem;margin-left:.5rem">
                            · {log.get("resource","—")} #{log.get("resource_id","—")}
                          </span>
                          <div style="font-size:.8rem;color:#5a7a9a;margin-top:.2rem">
                            👤 User #{log.get("user_id","—")} &nbsp;·&nbsp;
                            🕐 {(log.get("created_at") or "")[:19]}
                          </div>
                          {f'<div style="font-size:.8rem;color:#4a6480">{log["detail"]}</div>' if log.get("detail") else ""}
                        </div>
                      </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.error("Could not load audit logs.")


# ─── Emergency Banner ─────────────────────────────────────────────────────────
st.markdown("""
<div class="alert-danger">
  <strong>🚨 Emergency Signs — Seek Immediate Care:</strong>
  Chest pain · Sudden shortness of breath · Stroke signs (FAST) · Severe allergic reaction ·
  Uncontrolled bleeding · Loss of consciousness · Suspected poisoning<br>
  <strong>📞 112 (India) · 911 (US) · 999 (UK)</strong>
</div>""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:1rem 0 .3rem;color:#1e3a5f;font-size:.78rem;letter-spacing:.03em">
  MedAssist AI v6.0 · Doctor Dashboard · Built with LangGraph &amp; Streamlit ·
  14 Database Schemas · <em>Educational purposes only</em>
</div>""", unsafe_allow_html=True)
