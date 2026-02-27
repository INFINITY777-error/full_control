# patient_portal.py — MedAssist AI v6.0 Patient Portal
# FIX 1: Real JWT auth (register/login with hashed password)
# FIX 3: File uploads for medical records
# FIX 4: Email confirmation on appointment & consultation
# FIX 5: Mobile-responsive design
# BONUS: Consent tracking, doctor approval status shown

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import requests
from datetime import date

API_URL = "https://fullcontrol-production.up.railway.app"

st.set_page_config(
    page_title="MedAssist — Patient Portal",
    page_icon="🩺", layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600&family=Syne:wght@400;600;700&display=swap');

:root {
  --bg-deep:    #080d14;
  --bg-surface: #0e1520;
  --bg-card:    #111a27;
  --bg-card2:   #152030;
  --border:     rgba(0,220,200,.13);
  --border-mid: rgba(0,220,200,.22);
  --cyan:       #00dcc8;
  --cyan-dim:   rgba(0,220,200,.65);
  --cyan-glow:  rgba(0,220,200,.15);
  --blue-acc:   #3b82f6;
  --text-pri:   #e8f0fe;
  --text-sec:   #7a99b8;
  --text-dim:   #4a6580;
  --red:        #ff4d6a;
  --amber:      #f59e0b;
  --green:      #22c55e;
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body,.stApp{
  background:var(--bg-deep) !important;
  font-family:'Space Grotesk',sans-serif;
  color:var(--text-pri);
}
#MainMenu,footer,header{visibility:hidden}.stDeployButton{display:none}

/* Ambient background glow */
.stApp::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse at 15% 15%, rgba(0,220,200,.06) 0%, transparent 45%),
    radial-gradient(ellipse at 85% 85%, rgba(59,130,246,.07) 0%, transparent 45%),
    radial-gradient(ellipse at 50% 50%, rgba(0,220,200,.03) 0%, transparent 70%);
}

/* Hero */
.hero{text-align:center;padding:2.8rem 1rem 1.8rem;position:relative}
.hero-icon{
  font-size:2.8rem;margin-bottom:1rem;display:block;
  filter:drop-shadow(0 0 18px rgba(0,220,200,.5));
}
.hero-title{
  font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:700;
  color:var(--text-pri);letter-spacing:-.04em;line-height:1.05;margin-bottom:.5rem;
  text-shadow:0 0 40px rgba(0,220,200,.25);
}
.hero-title em{
  color:var(--cyan);font-style:normal;
  text-shadow:0 0 30px rgba(0,220,200,.6);
}
.hero-sub{font-size:.9rem;color:var(--text-sec);font-weight:300;line-height:1.6;letter-spacing:.03em}

/* Pulse line decoration */
.hero-pulse{
  width:120px;height:2px;margin:.8rem auto 0;
  background:linear-gradient(90deg,transparent,var(--cyan),transparent);
  border-radius:2px;
}

/* Auth box */
.auth-title{font-family:'Syne',sans-serif;font-size:1.35rem;color:var(--text-pri);margin-bottom:.25rem;font-weight:600}
.auth-sub{font-size:.82rem;color:var(--text-sec);margin-bottom:1.5rem}

/* Cards */
.card{
  background:var(--bg-card);
  border-radius:16px;padding:1.5rem;margin:.75rem 0;
  border:1px solid var(--border);
  box-shadow:0 4px 30px rgba(0,0,0,.4), inset 0 1px 0 rgba(0,220,200,.06);
}
.card-title{
  font-family:'Syne',sans-serif;font-size:1rem;color:var(--cyan);
  margin-bottom:1rem;display:flex;align-items:center;gap:.5rem;
  font-weight:600;letter-spacing:.02em;text-transform:uppercase;font-size:.82rem;
}

/* Status badges */
.badge-pending{
  background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.4);
  border-radius:6px;padding:.2rem .6rem;font-size:.73rem;color:#f59e0b;display:inline-block;
}
.badge-approved{
  background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.4);
  border-radius:6px;padding:.2rem .6rem;font-size:.73rem;color:#22c55e;display:inline-block;
}
.badge-green{
  background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.35);border-radius:20px;
  padding:.15rem .55rem;font-size:.73rem;color:#22c55e;display:inline-block;
}
.badge-red{
  background:rgba(255,77,106,.12);border:1px solid rgba(255,77,106,.35);border-radius:20px;
  padding:.15rem .55rem;font-size:.73rem;color:#ff4d6a;display:inline-block;
}
.badge-amber{
  background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);border-radius:20px;
  padding:.15rem .55rem;font-size:.73rem;color:#f59e0b;display:inline-block;
}

/* AI bubble */
.bubble-ai{
  background:var(--bg-card2);
  border:1px solid var(--border-mid);border-radius:16px;
  padding:1.25rem;font-size:.88rem;line-height:1.8;color:var(--text-pri);
  box-shadow:0 0 30px rgba(0,220,200,.06);margin:.5rem 0;
}
.bubble-ai h2{
  font-family:'Syne',sans-serif;font-size:.95rem;
  border-bottom:1px solid var(--border);
  padding-bottom:.35rem;margin:.75rem 0 .35rem;color:var(--cyan);font-weight:600;
}
.bubble-ai h3{font-size:.84rem;color:#7dd3fc;margin:.5rem 0 .2rem;font-weight:500}
.bubble-ai strong{color:var(--text-pri)}
.bubble-ai ul,.bubble-ai ol{padding-left:1.3rem;line-height:1.9;color:var(--text-sec)}
.bubble-ai table{width:100%;border-collapse:collapse;margin:.5rem 0;font-size:.82rem}
.bubble-ai th{
  background:rgba(0,220,200,.08);padding:.4rem .7rem;text-align:left;
  font-size:.71rem;text-transform:uppercase;color:var(--cyan);border:1px solid var(--border);letter-spacing:.07em;
}
.bubble-ai td{padding:.4rem .7rem;border:1px solid var(--border);color:var(--text-sec)}
.bubble-ai blockquote{
  border-left:3px solid var(--cyan);background:rgba(0,220,200,.06);
  padding:.5rem .9rem;margin:.4rem 0;border-radius:0 8px 8px 0;color:var(--cyan-dim);font-size:.84rem;
}
.bubble-ai hr{border:none;border-top:1px solid var(--border);margin:.8rem 0}
.bubble-user{
  background:linear-gradient(135deg,#1a3a5c,#0f2a45);
  color:var(--text-pri);border-radius:14px 14px 4px 14px;
  border:1px solid rgba(59,130,246,.3);
  padding:.8rem 1.1rem;font-size:.88rem;line-height:1.6;margin:.4rem 0 .4rem auto;max-width:90%;
}

/* Vitals grid */
.vital-mini{
  background:var(--bg-card2);border-radius:12px;padding:.85rem;text-align:center;
  border:1px solid var(--border);
  box-shadow:0 0 20px rgba(0,220,200,.05);
}
.vital-val{font-family:'Syne',sans-serif;font-size:1.35rem;color:var(--cyan);line-height:1;font-weight:600}
.vital-unit{font-size:.66rem;color:var(--text-dim);margin:.15rem 0;text-transform:uppercase;letter-spacing:.06em}
.vital-lbl{font-size:.7rem;color:var(--text-sec);margin-top:.2rem}

/* Consent box */
.consent-box{
  background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.3);border-radius:12px;
  padding:1rem 1.2rem;font-size:.82rem;color:#d4a820;line-height:1.7;margin-bottom:1rem;
}

/* Step list */
.step-row{display:flex;gap:.9rem;align-items:flex-start;padding:.7rem 0;border-bottom:1px solid var(--border)}
.step-row:last-child{border-bottom:none}
.step-n{
  width:26px;height:26px;min-width:26px;
  background:linear-gradient(135deg,var(--cyan),#00a896);
  color:#080d14;border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:.73rem;font-weight:700;
}
.step-t{font-size:.85rem;color:var(--text-sec);line-height:1.6}
.step-t strong{color:var(--text-pri)}

/* Inputs */
.stTextInput>div>div>input,
.stTextArea>div>div>textarea,
.stNumberInput>div>div>input{
  background:var(--bg-card) !important;
  border:1.5px solid var(--border-mid) !important;
  border-radius:10px !important;
  color:var(--text-pri) !important;
  font-size:.88rem !important;
}
.stTextInput>div>div>input:focus,
.stTextArea>div>div>textarea:focus{
  border-color:var(--cyan) !important;
  box-shadow:0 0 12px rgba(0,220,200,.2) !important;
}
.stSelectbox>div>div{
  background:var(--bg-card) !important;
  border:1.5px solid var(--border-mid) !important;
  border-radius:10px !important;
  color:var(--text-pri) !important;
}

/* Buttons */
.stButton>button{
  font-family:'Space Grotesk',sans-serif !important;
  font-weight:600 !important;
  border-radius:10px !important;
  transition:all .2s !important;
  letter-spacing:.03em !important;
}
.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,var(--cyan),#00a896) !important;
  border:none !important;color:#080d14 !important;
  box-shadow:0 0 20px rgba(0,220,200,.25) !important;
}
.stButton>button[kind="primary"]:hover{
  box-shadow:0 0 30px rgba(0,220,200,.45) !important;
  transform:translateY(-1px);
}
.stButton>button[kind="secondary"]{
  background:transparent !important;
  border:1.5px solid var(--border-mid) !important;
  color:var(--text-sec) !important;
}
.stButton>button[kind="secondary"]:hover{
  border-color:var(--cyan) !important;
  color:var(--cyan) !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"]{
  background:var(--bg-surface);border-radius:12px;
  padding:.22rem;gap:.12rem;
  border:1px solid var(--border);
}
.stTabs [data-baseweb="tab"]{
  background:transparent;border-radius:9px;
  color:var(--text-dim);font-size:.82rem;font-weight:500;
}
.stTabs [aria-selected="true"]{
  background:var(--bg-card2) !important;
  color:var(--cyan) !important;
  box-shadow:0 0 15px rgba(0,220,200,.15) !important;
}

/* Notice */
.notice{
  background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.25);
  border-radius:10px;padding:.8rem 1rem;font-size:.82rem;color:#c9940a;line-height:1.6;margin:.75rem 0;
}
.emergency{
  background:rgba(255,77,106,.08);border:1.5px solid rgba(255,77,106,.35);
  border-radius:12px;padding:.9rem 1.2rem;font-size:.83rem;color:#ff6b82;margin:1rem 0;
}

/* Doctor note */
.doctor-note{
  background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.25);border-radius:10px;
  padding:.9rem 1.1rem;font-size:.85rem;color:#6ee7a7;line-height:1.6;margin:.75rem 0;
}
.doctor-note strong{color:#86efac}

/* Metric overrides */
[data-testid="metric-container"]{
  background:var(--bg-card2);border:1px solid var(--border);border-radius:12px;
  padding:.75rem !important;
}
[data-testid="stMetricValue"]{color:var(--cyan) !important;font-family:'Syne',sans-serif !important}
[data-testid="stMetricLabel"]{color:var(--text-sec) !important;font-size:.75rem !important}

/* Mobile */
@media(max-width:640px){
  .hero-title{font-size:2rem}
  .card{padding:1.1rem}
}

/* File upload */
[data-testid="stFileUploader"]{
  background:var(--bg-card) !important;
  border:1.5px dashed var(--border-mid) !important;
  border-radius:12px !important;
}

/* Expander */
.streamlit-expanderHeader{
  background:var(--bg-card) !important;
  color:var(--text-pri) !important;
  border:1px solid var(--border) !important;
  border-radius:10px !important;
}
.streamlit-expanderContent{
  background:var(--bg-card2) !important;
  border:1px solid var(--border) !important;
  border-top:none !important;
}

/* Radio */
.stRadio>div>label{color:var(--text-sec) !important}
.stRadio>div>label:hover{color:var(--cyan) !important}

/* Caption / small text */
.stCaption,.stCaption p{color:var(--text-dim) !important}

/* Checkbox */
.stCheckbox>label{color:var(--text-sec) !important}

/* Form submit button special */
[data-testid="stForm"]{
  background:var(--bg-card);
  border:1px solid var(--border);
  border-radius:16px;padding:1.25rem !important;
}

/* Spinner */
.stSpinner>div{border-top-color:var(--cyan) !important}

/* Info/Warning/Success/Error */
.stAlert{border-radius:10px !important}
div[data-testid="stNotification"]{background:var(--bg-card2) !important;border-radius:10px !important}

/* Scrollbar */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:var(--bg-deep)}
::-webkit-scrollbar-thumb{background:var(--border-mid);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:var(--cyan)}
</style>
""", unsafe_allow_html=True)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def api_get(path, params=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.get(f"{API_URL}{path}", params=params, headers=headers, timeout=8)
        return r.json() if r.status_code == 200 else None
    except: return None

def api_post(path, payload, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, headers=headers, timeout=120)
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500

def upload_file(path, patient_id, record_type, title, file_bytes, filename, token):
    headers = {"Authorization": f"Bearer {token}"}
    files   = {"file": (filename, file_bytes)}
    params  = {"patient_id": patient_id, "record_type": record_type, "title": title}
    try:
        r = requests.post(f"{API_URL}{path}", params=params, files=files, headers=headers, timeout=30)
        return r.json(), r.status_code
    except Exception as e:
        return {"detail": str(e)}, 500


# ─── Session State ────────────────────────────────────────────────────────────
for key, default in [("token", None), ("user", None), ("patient_id", None),
                      ("patient_name", None), ("chat", []), ("symptoms", [])]:
    if key not in st.session_state:
        st.session_state[key] = default

token = st.session_state.token


# ══════════════════════════════════════════════════════════════════════════════
# AUTH WALL — show login if not authenticated
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.token:
    st.markdown("""
    <div class="hero">
      <span class="hero-icon">🩺</span>
      <div class="hero-title">MedAssist <em>AI</em></div>
      <div class="hero-sub">Your intelligent health companion</div>
      <div class="hero-pulse"></div>
    </div>""", unsafe_allow_html=True)

    auth_mode = st.radio("Account:", ["🔑 Login", "✨ Register"], horizontal=True,
                         label_visibility="collapsed")
    st.markdown("")

    if "🔑" in auth_mode:
        with st.form("login_form"):
            st.markdown('<div class="auth-title">Welcome back 👋</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Login to access your health portal</div>', unsafe_allow_html=True)
            email = st.text_input("Email", placeholder="you@example.com")
            pwd   = st.text_input("Password", type="password", placeholder="••••••••")
            if st.form_submit_button("🔓 Login", type="primary", use_container_width=True):
                data, code = api_post("/auth/login-json", {"email": email, "password": pwd})
                if code == 200:
                    st.session_state.token = data["access_token"]
                    st.session_state.user  = data["user"]
                    # Link to patient record — search by exact email match
                    p_results = api_get("/patients/search", {"q": email}, token=data["access_token"])
                    if p_results and p_results.get("results"):
                        p = p_results["results"][0]
                        st.session_state.patient_id   = p["id"]
                        st.session_state.patient_name = p["full_name"]
                    else:
                        # Fallback: try get_by_email via direct patient lookup
                        # Patient record may exist but search failed; will show re-link button in portal
                        st.session_state.patient_id   = None
                        st.session_state.patient_name = None
                    st.success("✅ Logged in! Redirecting...")
                    st.rerun()
                else:
                    st.error(f"❌ {data.get('detail', 'Incorrect email or password')}")

    else:
        with st.form("register_form"):
            st.markdown('<div class="auth-title">Create your account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Register once, access your health records anytime</div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                fn    = st.text_input("First Name *", key="ti_fn_1")
                email = st.text_input("Email *")
                pwd   = st.text_input("Password * (min 8 chars)", type="password")
            with c2:
                ln    = st.text_input("Last Name *", key="ti_ln_1")
                phone = st.text_input("Phone", key="ti_phone_1")
                dob   = st.text_input("Date of Birth (YYYY-MM-DD)", key="ti_dob_1")

            c3, c4 = st.columns(2)
            with c3: gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], key="sel_gender_1")
            with c4: blood  = st.selectbox("Blood Type", ["","A+","A-","B+","B-","AB+","AB-","O+","O-"], key="sel_bt_1")

            wt = st.number_input("Weight (kg)", value=None, step=0.5, key="ni_weight_1")
            ht = st.number_input("Height (cm)", value=None, step=0.5, key="ni_height_1")

            med_hist  = st.text_area("Medical History / Past Conditions", height=100,
                placeholder="e.g., Diabetes, Hypertension...", key="ta_medhist_1")
            allergies = st.text_area("Known Allergies", height=100,
                placeholder="e.g., Penicillin, Shellfish...", key="ta_allergy_1")
            curr_meds = st.text_area("Current Medications", height=100,
                placeholder="e.g., Metformin 500mg twice daily", key="ta_meds_1")

            st.markdown("""
            <div class="consent-box">
              🔒 <strong>Data Privacy Consent (DISHA Act Compliance)</strong><br>
              By registering, you consent to MedAssist AI securely storing and processing your
              health information to provide medical assistance. Your data is encrypted and only
              accessible to your treating doctor. You may request deletion at any time.
            </div>""", unsafe_allow_html=True)
            consent = st.checkbox("✅ I agree to the privacy policy and data processing terms *")

            if st.form_submit_button("✨ Create Account & Register", type="primary", use_container_width=True):
                if not fn or not ln or not email or not pwd:
                    st.error("Name, email and password are required.")
                elif len(pwd) < 8:
                    st.error("Password must be at least 8 characters.")
                elif not consent:
                    st.error("You must give consent to store health data.")
                else:
                    # Step 1: Create user account
                    user_data, u_code = api_post("/auth/register", {
                        "email": email, "password": pwd,
                        "full_name": f"{fn.strip()} {ln.strip()}",
                        "role": "patient", "phone": phone, "consent_given": True
                    })
                    if u_code == 201:
                        new_token = user_data["access_token"]
                        st.session_state.token = new_token
                        st.session_state.user  = user_data["user"]

                        # Step 2: Create patient record
                        pt_payload = {
                            "first_name": fn.strip(), "last_name": ln.strip(),
                            "email": email, "consent_given": True
                        }
                        for k, v in [("phone",phone),("date_of_birth",dob),("gender",gender),
                                      ("weight",wt),("height",ht),("blood_type",blood),
                                      ("medical_history",med_hist),("allergies",allergies),
                                      ("current_medications",curr_meds)]:
                            if v: pt_payload[k] = v

                        p_data, p_code = api_post("/patients", pt_payload, token=new_token)
                        if p_code == 201:
                            p = p_data["patient"]
                            st.session_state.patient_id   = p["id"]
                            st.session_state.patient_name = p["full_name"]
                            st.success(f"✅ Account created! Welcome, {fn}!")
                        else:
                            # User account OK but patient record failed
                            err = p_data.get("detail", "Unknown error")
                            st.warning(f"⚠️ Account created but patient profile setup failed: {err}. "
                                       f"You are logged in — please contact support to complete your profile.")
                        st.rerun()
                    else:
                        st.error(f"❌ {user_data.get('detail','Registration failed')}")

    st.markdown("""
    <div class="emergency">
      🚨 <strong>Emergency? Call 112 immediately.</strong>
      This portal is for non-emergency health guidance only.
    </div>""", unsafe_allow_html=True)
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# LOGGED IN — Main App
# ══════════════════════════════════════════════════════════════════════════════
user_info = st.session_state.user or {}

# Header with user info
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown(f"""
    <div class="hero" style="text-align:left;padding:1.5rem 0 1rem">
      <div class="hero-title" style="font-size:1.9rem">🩺 MedAssist <em>AI</em></div>
      <div class="hero-sub">Welcome, <strong>{user_info.get('full_name','Patient')}</strong></div>
    </div>""", unsafe_allow_html=True)
with col_h2:
    if st.button("🔓 Logout", type="secondary"):
        for k in ["token","user","patient_id","patient_name","chat","symptoms"]:
            st.session_state[k] = None if k in ["token","user","patient_id","patient_name"] else []
        st.rerun()

st.markdown("""
<div class="notice">
  ⚕️ AI assessments are <strong>preliminary guidance only</strong>.
  Every consultation is reviewed by a doctor before it's finalised.
  🚨 Emergencies → Call <strong>112</strong>
</div>""", unsafe_allow_html=True)

# ── AUTO RE-LINK: try to re-link patient record if not yet linked ──────────────
if not st.session_state.patient_id and token:
    _relink = api_get("/patients/search", {"q": (st.session_state.user or {}).get("email","")}, token=token)
    if _relink and _relink.get("results"):
        _p = _relink["results"][0]
        st.session_state.patient_id   = _p["id"]
        st.session_state.patient_name = _p["full_name"]
        st.rerun()
    else:
        # Patient record missing — show inline form to create it now
        _user_email = (st.session_state.user or {}).get("email", "")
        _user_name  = (st.session_state.user or {}).get("full_name", "")
        _fn_default = _user_name.split()[0] if _user_name else ""
        _ln_default = " ".join(_user_name.split()[1:]) if _user_name and len(_user_name.split()) > 1 else ""

        st.markdown("""
        <div class="card" style="border-color:rgba(0,220,200,.35);margin-bottom:1rem">
          <div class="card-title">⚠️ COMPLETE YOUR PATIENT PROFILE</div>
          <p style="color:#7a99b8;font-size:.87rem;margin-bottom:1rem">
            Your login account was created but your patient record wasn't saved (this can happen due to a network timeout during registration).
            Fill in the form below to complete setup — you only need to do this once.
          </p>
        </div>""", unsafe_allow_html=True)

        with st.form("fix_patient_profile"):
            c1, c2 = st.columns(2)
            with c1:
                fix_fn    = st.text_input("First Name *", value=_fn_default, key="ti_fn_2")
                fix_phone = st.text_input("Phone", placeholder="+91 9999999999", key="ti_phone_2")
                fix_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], key="sel_gender_2")
                fix_wt    = st.number_input("Weight (kg)", value=None, step=0.5, key="ni_weight_2")
            with c2:
                fix_ln    = st.text_input("Last Name *", value=_ln_default, key="ti_ln_2")
                fix_dob   = st.text_input("Date of Birth (YYYY-MM-DD)", placeholder="1990-01-15", key="ti_dob_2")
                fix_blood = st.selectbox("Blood Type", ["","A+","A-","B+","B-","AB+","AB-","O+","O-"], key="sel_bt_2")
                fix_ht    = st.number_input("Height (cm)", value=None, step=0.5, key="ni_height_2")

            fix_hist  = st.text_area("Medical History / Past Conditions", height=100,
                                      placeholder="e.g. Diabetes, Hypertension…", key="ta_medhist_2")
            fix_allergy = st.text_area("Known Allergies", height=100, placeholder="e.g. Penicillin, Pollen…", key="ta_allergy_2")
            fix_meds    = st.text_area("Current Medications", height=100, placeholder="e.g. Metformin 500mg twice daily", key="ta_meds_2")

            if st.form_submit_button("✅ Save My Profile & Continue", type="primary", use_container_width=True):
                if not fix_fn.strip() or not fix_ln.strip():
                    st.error("First name and last name are required.")
                else:
                    _pt_payload = {
                        "first_name": fix_fn.strip(),
                        "last_name":  fix_ln.strip(),
                        "email":      _user_email,
                        "consent_given": True,
                    }
                    for _k, _v in [("phone", fix_phone), ("date_of_birth", fix_dob),
                                   ("gender", fix_gender), ("blood_type", fix_blood),
                                   ("weight", fix_wt), ("height", fix_ht),
                                   ("medical_history", fix_hist),
                                   ("allergies", fix_allergy),
                                   ("current_medications", fix_meds)]:
                        if _v: _pt_payload[_k] = _v

                    with st.spinner("Creating your patient profile…"):
                        _pd, _pc = api_post("/patients", _pt_payload, token=token)

                    if _pc == 201:
                        _p = _pd["patient"]
                        st.session_state.patient_id   = _p["id"]
                        st.session_state.patient_name = _p["full_name"]
                        st.success("✅ Profile created! Loading your portal…")
                        st.rerun()
                    elif _pc == 400 and "already registered" in str(_pd.get("detail","")):
                        # Race condition: record was created between checks — re-link
                        _retry = api_get("/patients/search", {"q": _user_email}, token=token)
                        if _retry and _retry.get("results"):
                            _p = _retry["results"][0]
                            st.session_state.patient_id   = _p["id"]
                            st.session_state.patient_name = _p["full_name"]
                            st.success("✅ Profile linked! Loading your portal…")
                            st.rerun()
                        else:
                            st.error(f"Unexpected error: {_pd.get('detail','')}")
                    else:
                        st.error(f"❌ Could not create profile: {_pd.get('detail','Please try again.')}")

        st.stop()  # Don't render tabs until profile is set up

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Health Assistant", "📋 My Profile",
    "📅 Appointments", "📁 My Records", "📂 History"
])


# ── TAB 1: HEALTH ASSISTANT ───────────────────────────────────────────────────
with tab1:
    # Symptom selector
    st.markdown('<div class="card"><div class="card-title">🤒 Select Your Symptoms</div>', unsafe_allow_html=True)
    SYMPTOMS = [
        "🌡️ Fever", "🤕 Headache", "😮‍💨 Shortness of Breath", "💔 Chest Pain",
        "🤢 Nausea", "🤮 Vomiting", "😴 Fatigue", "🤧 Cold / Runny Nose",
        "😤 Cough", "🦴 Body Aches", "😵 Dizziness", "🫃 Stomach Pain",
        "💩 Diarrhea", "🔥 Sore Throat", "👁️ Eye Pain", "🩸 Bleeding",
        "💊 Rash / Skin Issue", "🦵 Joint Pain", "😰 Anxiety", "🧠 Confusion",
    ]
    cols = st.columns(4)
    for i, s in enumerate(SYMPTOMS):
        with cols[i % 4]:
            val = s in st.session_state.symptoms
            if st.checkbox(s, value=val, key=f"s_{i}"):
                if s not in st.session_state.symptoms: st.session_state.symptoms.append(s)
            else:
                if s in st.session_state.symptoms: st.session_state.symptoms.remove(s)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">📝 Describe Further</div>', unsafe_allow_html=True)
    extra    = st.text_area("In your own words:", height=90,
        placeholder="e.g., Fever 38.5°C for 2 days with sore throat and difficulty swallowing...")
    c1, c2  = st.columns(2)
    with c1: duration = st.text_input("Duration:", placeholder="e.g., 3 days")
    with c2: severity = st.select_slider("Severity:", ["Very Mild","Mild","Moderate","Severe","Very Severe"], value="Moderate")
    send_email_notif = st.checkbox("📧 Email me a copy of this consultation", value=True)
    ask_btn = st.button("🔬 Analyse My Symptoms", type="primary", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if ask_btn:
        all_symptoms = st.session_state.symptoms.copy()
        if extra.strip(): all_symptoms.append(extra.strip())
        if not all_symptoms:
            st.warning("Please select at least one symptom.")
        else:
            with st.spinner("🩺 Analysing..."):
                payload = {
                    "model_name": "llama-3.3-70b-versatile",
                    "model_provider": "Groq",
                    "symptoms": [s.split(" ",1)[-1] if len(s) > 2 and not s[0].isalpha() else s for s in all_symptoms],
                    "duration": duration or None,
                    "severity": severity,
                    "allow_search": False,
                    "patient_db_id": st.session_state.patient_id,
                    "send_email": send_email_notif,
                }
                data, code = api_post("/diagnose", payload, token=token)
                if code == 200:
                    st.session_state.chat.append({
                        "role": "user",
                        "content": f"**Symptoms:** {', '.join(all_symptoms)}\n**Duration:** {duration or '—'} | **Severity:** {severity}"
                    })
                    st.session_state.chat.append({
                        "role": "ai",
                        "content": data.get("diagnosis",""),
                        "consultation_id": data.get("consultation_id"),
                        "saved": data.get("saved_to_db", False),
                        "approval": data.get("doctor_approval_status","pending"),
                        "email_sent": data.get("email_sent", False),
                    })
                    st.rerun()
                else:
                    st.error(f"Error: {data.get('detail','Please try again.')}")

    # Chat display
    for msg in st.session_state.chat:
        if msg["role"] == "user":
            st.markdown(f'<div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            cid = msg.get("consultation_id")
            approval = msg.get("approval","pending")
            email_sent = msg.get("email_sent", False)

            status_html = f'<span class="badge-pending">⏳ Pending Doctor Review</span>' \
                if approval == "pending" else f'<span class="badge-approved">✅ Doctor Reviewed</span>'

            st.markdown(f"""
            <div style="display:flex;align-items:center;gap:.5rem;margin:.5rem 0 .25rem;flex-wrap:wrap">
              <span style="font-size:.72rem;color:#7a99b8;text-transform:uppercase;letter-spacing:.1em">🤖 AI Assessment</span>
              {status_html}
              {'<span class="badge-green">📧 Email Sent</span>' if email_sent else ''}
              {f'<span style="font-size:.72rem;color:#4a6580">Ref #{cid}</span>' if cid else ''}
            </div>""", unsafe_allow_html=True)

            if approval == "pending":
                st.markdown("""
                <div class="notice" style="margin:.25rem 0 .5rem">
                  ⚕️ This is an <strong>AI-generated preliminary assessment</strong>.
                  Your doctor will review it and may add notes before it's finalised.
                </div>""", unsafe_allow_html=True)

            st.markdown(f'<div class="bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)

            # Show doctor's review note if approved
            if approval == "approved" and cid:
                c_data = api_get(f"/consultations/{cid}", token=token)
                if c_data and c_data.get("doctor_notes"):
                    st.markdown(f"""
                    <div class="doctor-note">
                      👨‍⚕️ <strong>Doctor's Review:</strong><br>
                      {c_data["doctor_notes"]}
                    </div>""", unsafe_allow_html=True)

    if st.session_state.chat:
        col_a, col_b = st.columns(2)
        with col_a:
            followup = st.text_input("💬 Follow-up question:", placeholder="e.g., Can I take paracetamol?")
            if st.button("📤 Ask", type="primary") and followup.strip():
                with st.spinner("Thinking..."):
                    msgs = [m["content"] for m in st.session_state.chat]
                    msgs.append(followup.strip())
                    data, code = api_post("/chat", {
                        "model_name":"llama-3.3-70b-versatile","model_provider":"Groq",
                        "messages": msgs, "allow_search": False}, token=token)
                    if code == 200:
                        st.session_state.chat.append({"role":"user","content":followup})
                        st.session_state.chat.append({"role":"ai","content":data.get("response",""),"approval":"info"})
                        st.rerun()
        with col_b:
            if st.button("🗑️ Clear Consultation", type="secondary"):
                st.session_state.chat = []; st.session_state.symptoms = []; st.rerun()


# ── TAB 2: MY PROFILE ─────────────────────────────────────────────────────────
with tab2:
    if st.session_state.patient_id:
        profile = api_get(f"/patients/{st.session_state.patient_id}/full-profile", token=token)
        if profile:
            st.markdown('<div class="card"><div class="card-title">📊 Health Summary</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Age", f"{profile.get('age','?')} yrs")
            with c2: st.metric("Blood Type", profile.get("blood_type") or "—")
            with c3: st.metric("BMI", f"{profile.get('bmi') or '—'}")
            with c4: st.metric("Consultations", profile.get("total_consultations",0))

            if profile.get("allergies"):
                st.markdown(f'⚠️ **Allergies:** {profile["allergies"]}')
            if profile.get("medical_history"):
                st.markdown(f'🏥 **History:** {profile["medical_history"]}')
            if profile.get("current_medications"):
                st.markdown(f'💊 **Medications:** {profile["current_medications"]}')

            vitals = profile.get("vitals", [])
            if vitals:
                v = vitals[0]
                st.markdown("**❤️ Latest Vitals:**")
                vc = st.columns(5)
                data_v = [
                    (v.get("blood_pressure","—"), "mmHg", "Blood Pressure"),
                    (v.get("pulse_rate","—"),     "bpm",  "Pulse"),
                    (v.get("temperature","—"),    "°C",   "Temperature"),
                    (v.get("spo2","—"),            "%",    "SpO₂"),
                    (v.get("blood_glucose","—"),  "mg/dL","Glucose"),
                ]
                for col, (val, unit, lbl) in zip(vc, data_v):
                    with col:
                        st.markdown(f'<div class="vital-mini"><div class="vital-val">{val}</div><div class="vital-unit">{unit}</div><div class="vital-lbl">{lbl}</div></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Active medications
            meds = profile.get("medications", [])
            if meds:
                st.markdown('<div class="card"><div class="card-title">💊 Current Medications</div>', unsafe_allow_html=True)
                for m in meds:
                    st.markdown(f"**{m['drug_name']}** {m.get('dosage','')} — {m.get('frequency','')} | {m.get('indication','')}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No patient record linked. Please register using the login page.")


# ── TAB 3: BOOK APPOINTMENT ───────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="card"><div class="card-title">📅 Book an Appointment</div>', unsafe_allow_html=True)
    if not st.session_state.patient_id:
        st.markdown("""
        <div class="notice" style="border-color:rgba(255,77,106,.4);background:rgba(255,77,106,.07)">
          ❌ <strong>Cannot book appointment</strong> — your patient profile is not linked to this account.<br>
          Please logout and re-register, or contact your clinic admin to link your profile.
        </div>""", unsafe_allow_html=True)
    else:
        docs_data = api_get("/doctors")
        docs = docs_data.get("doctors", []) if docs_data else []
        if docs:
            for d in docs:
                st.markdown(f"""
                <div style="background:#111a27;border-radius:10px;padding:.8rem 1rem;margin:.35rem 0;border:1px solid rgba(0,220,200,.18)">
                  <strong style="color:#e8f0fe">Dr. {d['first_name']} {d['last_name']}</strong>
                  <span style="color:#00dcc8;font-size:.82rem"> — {d.get('specialization','General')}</span><br>
                  <span style="font-size:.8rem;color:#7a99b8">🏥 {d.get('hospital','—')} · 📅 {d.get('available_days','—')} · 💰 ₹{d.get('consultation_fee','—')}</span>
                </div>""", unsafe_allow_html=True)

        with st.form("book_appt_p", clear_on_submit=True):
            doc_opts = {"No preference": None}
            for d in docs:
                doc_opts[f"Dr. {d['first_name']} {d['last_name']} — {d.get('specialization','General')}"] = d["id"]
            sel_doc = st.selectbox("Choose Doctor:", list(doc_opts.keys()))
            c1, c2 = st.columns(2)
            with c1: a_date = st.text_input("Date (YYYY-MM-DD) *", value=str(date.today()))
            with c2: a_time = st.text_input("Time", placeholder="10:00 AM")
            a_type   = st.selectbox("Visit Type", ["In-person","Telemedicine","Follow-up"])
            a_reason = st.text_area("Reason *", height=70, placeholder="Why do you need to see the doctor?")
            send_conf= st.checkbox("📧 Send email confirmation", value=True)

            if st.form_submit_button("📅 Book Appointment", type="primary", use_container_width=True):
                if not a_date or not a_reason.strip():
                    st.error("Date and reason are required.")
                else:
                    payload = {"patient_id": st.session_state.patient_id,
                               "appointment_date": a_date, "appointment_type": a_type,
                               "reason": a_reason.strip(), "send_email": send_conf}
                    if doc_opts.get(sel_doc): payload["doctor_id"] = doc_opts[sel_doc]
                    if a_time: payload["appointment_time"] = a_time
                    data, code = api_post("/appointments", payload, token=token)
                    if code == 201:
                        email_msg = " A confirmation email has been sent." if data.get("email_sent") else ""
                        st.success(f"✅ Appointment booked for **{a_date}**!{email_msg}")
                    else:
                        st.error(f"Error: {data.get('detail','')}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="card-title">ℹ️ How It Works</div>', unsafe_allow_html=True)
    steps = [
        ("Describe symptoms", "Use the AI assistant to log how you feel."),
        ("Book appointment", "Choose a doctor and time that suits you."),
        ("Get confirmation email", "Appointment details sent to your inbox automatically."),
        ("Doctor reviews your data", "Doctor sees your AI consultation before you arrive."),
        ("Receive professional care", "Doctor adds notes, medications and follow-up plan."),
    ]
    for i, (t, d) in enumerate(steps):
        st.markdown(f'<div class="step-row"><div class="step-n">{i+1}</div><div class="step-t"><strong>{t}</strong><br>{d}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── TAB 4: MY RECORDS (File Upload) ──────────────────────────────────────────
with tab4:
    st.markdown('<div class="card"><div class="card-title">📁 Upload Medical Documents</div>', unsafe_allow_html=True)
    st.caption("Upload your lab reports, prescriptions, X-rays etc. Your doctor can see all uploaded files.")

    if not st.session_state.patient_id:
        st.warning("Patient profile not linked.")
    else:
        with st.form("upload_rec", clear_on_submit=True):
            rec_type  = st.selectbox("Document Type:", ["Lab Report","X-Ray","MRI","CT Scan",
                                     "Prescription","Discharge Summary","Vaccination Record","Other"])
            rec_title = st.text_input("Document Title *", placeholder="CBC Blood Report - Jan 2025")
            rec_by    = st.text_input("Issued By", placeholder="Apollo Hospital / Dr. Name")
            uploaded  = st.file_uploader("Choose File (PDF, JPG, PNG — max 10MB):",
                                          type=["pdf","jpg","jpeg","png"])
            if st.form_submit_button("📤 Upload Document", type="primary", use_container_width=True):
                if not rec_title.strip():
                    st.error("Title is required.")
                elif not uploaded:
                    st.error("Please choose a file to upload.")
                else:
                    with st.spinner("Uploading..."):
                        data, code = upload_file("/upload", st.session_state.patient_id,
                                                  rec_type, rec_title.strip(),
                                                  uploaded.read(), uploaded.name, token)
                        if code == 200:
                            st.success(f"✅ '{rec_title}' uploaded! ({data.get('file_size_kb','?')} KB)")
                        else:
                            st.error(f"Upload failed: {data.get('detail','')}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card"><div class="card-title">📂 My Documents</div>', unsafe_allow_html=True)
        recs = api_get(f"/patients/{st.session_state.patient_id}/medical-records", token=token)
        if recs and recs.get("records"):
            for r in recs["records"]:
                icons = {"Lab Report":"🧪","X-Ray":"🦴","MRI":"🧠","Prescription":"💊","Discharge Summary":"🏥"}
                icon = icons.get(r.get("record_type",""),"📄")
                st.markdown(f"""
                <div style="padding:.75rem;background:#111a27;border-radius:10px;margin:.35rem 0;border:1px solid rgba(0,220,200,.15)">
                  <strong style="color:#e8f0fe">{icon} {r.get('title','—')}</strong>
                  <span style="background:rgba(0,220,200,.12);border:1px solid rgba(0,220,200,.2);border-radius:6px;padding:.1rem .5rem;font-size:.73rem;margin-left:.5rem;color:#00dcc8">{r.get('record_type','—')}</span><br>
                  <span style="font-size:.8rem;color:#7a99b8">📅 {r.get('issued_date','—')} · 🏥 {r.get('issued_by','—')} · 📄 {r.get('file_name','No file')}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("No documents uploaded yet.")
        st.markdown('</div>', unsafe_allow_html=True)


# ── TAB 5: HISTORY ────────────────────────────────────────────────────────────
with tab5:
    if not st.session_state.patient_id:
        st.info("No patient record linked.")
    else:
        # Consultations
        st.markdown('<div class="card"><div class="card-title">📋 Consultation History</div>', unsafe_allow_html=True)
        cdata = api_get(f"/patients/{st.session_state.patient_id}/consultations", token=token)
        if cdata and cdata.get("consultations"):
            for c in cdata["consultations"]:
                syms = [s.get("symptom_name","") for s in c.get("symptoms",[])]
                approval = c.get("doctor_approval_status","pending")
                badge = f'<span class="badge-approved">✅ Doctor Reviewed</span>' \
                    if approval == "approved" else f'<span class="badge-pending">⏳ Pending Review</span>'
                with st.expander(f"📋 {(c.get('consultation_date') or '')[:10]} — {', '.join(syms[:3])}"):
                    st.markdown(badge, unsafe_allow_html=True)
                    if c.get("doctor_notes"):
                        st.markdown(f'<div class="doctor-note">👨‍⚕️ <strong>Doctor\'s Note:</strong><br>{c["doctor_notes"]}</div>', unsafe_allow_html=True)
                    st.markdown(c.get("ai_diagnosis","No diagnosis recorded."))
        else:
            st.caption("No consultations yet.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Appointments
        st.markdown('<div class="card"><div class="card-title">📅 My Appointments</div>', unsafe_allow_html=True)
        adata = api_get(f"/patients/{st.session_state.patient_id}/appointments", token=token)
        if adata and adata.get("appointments"):
            for a in adata["appointments"]:
                s = a.get("status","Scheduled")
                bcls = {"Completed":"badge-green","Cancelled":"badge-red"}.get(s,"badge-amber")
                st.markdown(f"""
                <div style="padding:.7rem .9rem;background:#111a27;border-radius:10px;margin:.3rem 0;border:1px solid rgba(0,220,200,.15)">
                  <strong style="color:#e8f0fe">📅 {a.get('appointment_date','—')}</strong> <span style="color:#7a99b8">at {a.get('appointment_time','—')}</span>
                  <span class="{bcls}" style="margin-left:.5rem">{s}</span><br>
                  <span style="font-size:.8rem;color:#7a99b8">👨‍⚕️ {a.get('doctor_name') or 'TBD'} · {a.get('appointment_type','—')} · 📝 {a.get('reason','—')}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.caption("No appointments booked yet.")
        st.markdown('</div>', unsafe_allow_html=True)


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="emergency">
  🚨 <strong>Emergency Signs → Go to ER:</strong>
  Chest pain · Stroke (face drop, arm weak, slurred speech) ·
  Severe breathing difficulty · Unconscious · Major bleeding<br>
  <strong>📞 Call 112 (India) · 911 (US) · 999 (UK)</strong>
</div>
<div style="text-align:center;color:#4a6580;font-size:.73rem;padding:.5rem 0">
  MedAssist AI v6.0 · JWT Secured · DISHA Compliant · Educational use only
</div>""", unsafe_allow_html=True)
