import streamlit as st
import uuid
from datetime import datetime
import numpy as np
import pandas as pd
import os
import sys
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import plotly.express as px
from pathlib import Path
import hashlib
import smtplib
import requests  
import resend
from email.mime.text import MIMEText
import threading
import time
from dotenv import load_dotenv

# 1. Page Config (MUST be very first Streamlit call)
st.set_page_config(layout="wide")

# 2. Load .env and define PROJECT_ROOT first
load_dotenv()  
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = Path(__file__).resolve().parent.parent

from agents import (
    run_orchestration, build_simple_view, init_db, save_submission,
    retrieve_similar_bugs, root_cause_agent,
    duplicate_detection_agent, remediation_agent,
    COMPONENT_MERGE_MAP, compute_defect_analytics, cluster_root_causes,
    add_resolved_bug_to_kb
)

init_db()

# 3. Database paths
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEV_DB_PATH = DATA_DIR / "Developer_Submission.db"
AUTH_DB_PATH = DATA_DIR / "auth_users.db"
BUG_DB_PATH = DATA_DIR / "bug_submissions.db"


# =====================================================================
# 🗄️ AUTHENTICATION & USER HELPERS
# =====================================================================
def init_auth_db():
    conn = sqlite3.connect(AUTH_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT
        )
    """)
    conn.commit()
    conn.close()

init_auth_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(email: str, password: str) -> tuple[bool, str]:
    if not email.strip() or not password.strip():
        return False, "Email and password cannot be empty."
    conn = sqlite3.connect(AUTH_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (email, password_hash, created_at, last_login) VALUES (?, ?, ?, ?)",
            (email.strip().lower(), hash_password(password), datetime.now().isoformat(), None)
        )
        conn.commit()
        conn.close()
        return True, "Account registered successfully! You can now log in."
    except sqlite3.IntegrityError:
        conn.close()
        return False, "This email is already registered."
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {e}"

def verify_user(email: str, password: str) -> bool:
    conn = sqlite3.connect(AUTH_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    if row and row[0] == hash_password(password):
        cursor.execute("UPDATE users SET last_login = ? WHERE email = ?", (datetime.now().isoformat(), email.strip().lower()))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

# =====================================================================
# 📧 RESEND MANUAL DISPATCHER (With Stack Trace Included)
# =====================================================================
resend.api_key = os.getenv("Resend_API") or os.getenv("RESEND_API_KEY", "")

def send_verification_email_api(recipient_email: str, bug_id: str, stack_trace: str = "") -> bool:
    """Sends verification reminder with the original stack trace via Resend API."""
    if not resend.api_key:
        st.error("Resend API key not found in .env file.")
        return False

    trace_display = stack_trace.strip() if stack_trace and stack_trace.strip() else "No stack trace provided."

    params: resend.Emails.SendParams = {
        "from": "Bug Diagnosis System <onboarding@resend.dev>",
        "to": [recipient_email],
        "subject": f"Action Required: Verify Fix Outcome for Bug {bug_id}",
        "html": f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #0f172a; line-height: 1.6;">
                <h3 style="color: #0284c7;">Defect Verification Required</h3>
                <p>Hello,</p>
                <p>You submitted ticket <strong>{bug_id}</strong>, which is currently pending outcome review.</p>
                
                <div style="background-color: #f1f5f9; border-left: 4px solid #0284c7; padding: 12px; margin: 15px 0; border-radius: 4px;">
                    <h4 style="margin: 0 0 8px 0; color: #334155;">Original Submitted Stack Trace / Log:</h4>
                    <pre style="background: #1e293b; color: #f8fafc; padding: 10px; border-radius: 6px; overflow-x: auto; font-size: 13px; font-family: monospace;"><code>{trace_display}</code></pre>
                </div>

                <p>Please log in to the portal and confirm the outcome:</p>
                <ul>
                    <li><strong>✅ Fix Worked</strong>: Appends fix to verified knowledge repository.</li>
                    <li><strong>❌ Fix Did Not Work</strong>: Flags defect for further root-cause investigation.</li>
                </ul>
                <br>
                <p><em>Intelligent 🐞 Bug Diagnosis Platform</em></p>
            </body>
        </html>
        """
    }
    try:
        resend.Emails.send(params)
        return True
    except Exception as e:
        st.error(f"Failed to send email for {bug_id}: {e}")
        return False


def get_pending_review_bugs():
    """Fetches tickets pending verification along with their submitted trace/description."""
    if not BUG_DB_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(BUG_DB_PATH, timeout=10.0)
        cursor = conn.cursor()
        # Changed stack_trace -> description
        cursor.execute("""
            SELECT bug_id, severity, component, description, timestamp 
            FROM bug_submissions 
            WHERE status IS NULL 
               OR status = '' 
               OR LOWER(status) LIKE '%pending%'
            ORDER BY timestamp DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        st.error(f"Error fetching pending tickets: {e}")
        return []

def get_ticket_recipient_email(bug_id: str):
    """Finds reporter email associated with the bug or falls back to current active user."""
    target_email = None
    if DEV_DB_PATH.exists():
        try:
            conn_dev = sqlite3.connect(DEV_DB_PATH, timeout=5.0)
            cursor_dev = conn_dev.cursor()
            cursor_dev.execute("SELECT reporter_name FROM Developer_Submission WHERE bug_id = ?", (bug_id,))
            res = cursor_dev.fetchone()
            conn_dev.close()
            if res and "@" in str(res[0]):
                target_email = res[0].strip()
        except Exception:
            pass

    if not target_email and AUTH_DB_PATH.exists():
        try:
            conn_auth = sqlite3.connect(AUTH_DB_PATH, timeout=5.0)
            cursor_auth = conn_auth.cursor()
            cursor_auth.execute("SELECT email FROM users ORDER BY last_login DESC LIMIT 1")
            auth_res = cursor_auth.fetchone()
            conn_auth.close()
            if auth_res and "@" in str(auth_res[0]):
                target_email = auth_res[0].strip()
        except Exception:
            pass

    return target_email or st.session_state.get("user_email")

# =====================================================================
# 🎨 CUSTOM CSS
# =====================================================================
st.markdown(
    """
    <style>
    header[data-testid="stHeader"], .stAppHeader {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E2E8F0 !important;
    }
    .stApp {
        background-color: #F8FAFC !important;
        font-size: 1.05rem !important;
    }
    p, span, label {
        color: #0F172A;
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #CBD5E1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
        color: #0369A1 !important;
        font-weight: 800 !important;
        font-size: 1.15rem !important;
        margin-bottom: 10px;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 10px;
        width: 100%;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label {
        width: 100% !important;
        min-height: 52px !important;
        background: #F1F5F9 !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 8px !important;
        color: #1E293B !important;
        font-weight: 700 !important;
        font-size: 1.0rem !important;
        padding: 0 16px !important;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
        border-color: #0284C7 !important;
        background: #E0F2FE !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
    [data-testid="stSidebar"] div[role="radiogroup"] > label:has(input:checked) {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        border: 1px solid #0284C7 !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35) !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p,
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05) !important;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #0284C7 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.6rem 1.3rem !important;
        box-shadow: 0 2px 4px rgba(2, 132, 199, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #0369A1 0%, #075985 100%) !important;
        box-shadow: 0 4px 10px rgba(2, 132, 199, 0.35) !important;
    }
    div.stButton > button p, div.stButton > button span {
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }
    .stTextArea textarea {
        background-color: #FFFFFF !important;
        border: 2px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 8px !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 1.0rem !important;
        font-weight: 500 !important;
    }
    .stTextInput input {
        background-color: #FFFFFF !important;
        border: 2px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 8px !important;
        font-size: 1.0rem !important;
        font-weight: 600 !important;
    }
    div[data-baseweb="select"] {
        background-color: #FFFFFF !important;
        border: 2px solid #CBD5E1 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * {
        background-color: transparent !important;
        color: #0F172A !important;
        font-weight: 600 !important;
    }
    [data-testid="stFileUploader"] section {
        background-color: #F8FAFC !important;
        border: 2px dashed #94A3B8 !important;
        border-radius: 8px !important;
        color: #1E293B !important;
    }
    div[data-testid="stAlert"] {
        background-color: #FFFFFF !important;
        border: 2px solid #0284C7 !important;
        border-radius: 10px !important;
        padding: 16px 20px !important;
        box-shadow: 0 2px 6px rgba(2, 132, 199, 0.1) !important;
    }
    .badge-bug-id {
        background-color: #FFFFFF !important;
        color: #0284C7 !important;
        border: 2px solid #0284C7 !important;
        padding: 6px 14px !important;
        border-radius: 8px !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        display: inline-block !important;
    }
    .badge-filter-box {
        background: #E0F2FE !important;
        color: #0369A1 !important;
        border: 1px solid #BAE6FD !important;
        padding: 6px 12px !important;
        border-radius: 6px !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        display: inline-block;
        margin-bottom: 6px;
    }
    .badge-verified-kb {
        background: #DCFCE7 !important;
        color: #15803D !important;
        border: 1px solid #86EFAC !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    .badge-unresolved {
        background: #FEE2E2 !important;
        color: #B91C1C !important;
        border: 1px solid #FCA5A5 !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    .badge-pending {
        background: #FEF3C7 !important;
        color: #B45309 !important;
        border: 1px solid #FDE68A !important;
        padding: 6px 14px !important;
        border-radius: 20px !important;
        font-weight: 700 !important;
        font-size: 0.9rem !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: flex;
        flex-direction: column;
        height: 100%;
    }
    .sidebar-bottom-anchor {
        margin-top: auto !important;
        padding-top: 20px;
        border-top: 1px solid #CBD5E1;
    }
    .logout-btn-wrapper button {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #B91C1C !important;
        font-weight: 700 !important;
        width: 100% !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 4px rgba(239, 68, 68, 0.25) !important;
    }
    .logout-btn-wrapper button:hover {
        background: linear-gradient(135deg, #DC2626 0%, #991B1B 100%) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =====================================================================
# 🔐 AUTHENTICATION GATEWAY
# =====================================================================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.authenticated:
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_center, col_r = st.columns([1, 1.5, 1])
    
    with col_center:
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; margin-bottom: 0;'>🔐 Secure Access Portal</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; font-size: 14px; margin-top: 4px;'>Intelligent 🐞 Bug Diagnosis Platform</p>", unsafe_allow_html=True)
            st.divider()
            
            auth_mode = st.radio("Choose Action", ["Login", "Create Account"], horizontal=True, label_visibility="collapsed")
            email_input = st.text_input("Email Address", placeholder="developer@company.com")
            pass_input = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if auth_mode == "Login":
                if st.button("🚀 Log In", width="stretch"):
                    if verify_user(email_input, pass_input):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email_input.strip().lower()
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
            else:
                if st.button("📝 Register New Account", width="stretch"):
                    success, msg = register_user(email_input, pass_input)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                        
    st.stop()

# =====================================================================
# 🧭 SIDEBAR NAVIGATION
# =====================================================================
page = st.sidebar.radio(
    "Creation of Intelligent 🐞 Diagnosis Platform with Fix Recommendation Assistance",
    ["🏠 Dashboard", "1️⃣Submit Bug", "2️⃣Analytics Dashboard", "🧠Knowledge Base", "3️⃣About The App", "📚User Guide"]
)

st.sidebar.markdown('<div class="sidebar-bottom-anchor"></div>', unsafe_allow_html=True)
with st.sidebar.container():
    st.markdown(f"**👤 User:** `{st.session_state.user_email}`")
    st.markdown('<div class="logout-btn-wrapper">', unsafe_allow_html=True)
    if st.button("🚪 Log Out", key="sidebar_bottom_logout_btn", width="stretch"):
        st.session_state.authenticated = False
        st.session_state.user_email = ""
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================================
# 📄 PAGE 1: SUBMIT BUG
# =====================================================================
if page == "1️⃣Submit Bug":
    st.title(" Submit Defect logs")
    st.markdown('<span class="badge-filter-box">Paste your bug report or stack trace below - analysis runs automatically.</span>', unsafe_allow_html=True)

    @st.cache_resource
    def load_retrieval_components():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model = SentenceTransformer('all-MiniLM-L6-v2')
        embeddings = np.load(os.path.join(base_dir, "embeddings_real.npy"))
        metadata = pd.read_csv(os.path.join(base_dir, "chunks_metadata.csv"))
        return model, embeddings, metadata

    model, kb_embeddings, kb_metadata = load_retrieval_components()

    col_intake, col_meta = st.columns([1.6, 1.1])

    with col_intake:
        with st.container(border=True):
            st.markdown('<span class="badge-filter-box">📝 Bug Report / Stack Trace</span>', unsafe_allow_html=True)
            bug_report = st.text_area(
                "Bug Report / Stack Trace",
                height=300,
                key="bug_report_input",
                placeholder="Paste code trace logs, compile exception lines, or runtime errors here...",
                label_visibility="collapsed"
            )

            st.markdown('<span class="badge-filter-box">📂 Or Upload a Bug Report File (.txt, .log)</span>', unsafe_allow_html=True)
            uploaded_file = st.file_uploader(
                "Or upload a bug report file",
                type=["txt", "log"],
                key="bug_file_uploader",
                label_visibility="collapsed"
            )

            st.markdown('<span class="badge-filter-box">🎯 Similar Bugs Retrieval Depth</span>', unsafe_allow_html=True)
            top_n = st.slider(
                "Number of similar bugs to retrieve",
                min_value=3,
                max_value=15,
                value=5,
                key="top_n_slider",
                label_visibility="collapsed"
            )

    with col_meta:
        with st.container(border=True):
            st.markdown("##### 📌 METADATA CONTEXT")
            
            st.caption("Project Name")
            project_name = st.text_input(
                "Project Name", 
                value="AI Smart Bug Analyzer", 
                key="meta_proj_name", 
                label_visibility="collapsed"
            )
            
            st.caption("Reporter Email / Name *")
            reporter_name = st.text_input(
                "Reporter Name", 
                value=st.session_state.user_email, 
                key="meta_rep_name", 
                label_visibility="collapsed"
            )
            
            st.caption("Developer Department")
            dev_dept = st.selectbox(
                "Developer Department",
                ["Backend Core API", "Frontend UI", "Py coder", "DevOps / Infra", "QA & Testing", "Database / Data Eng"],
                key="meta_dev_dept",
                label_visibility="collapsed"
            )
            
            st.caption("Group Number")
            group_num = st.selectbox(
                "Group Number",
                ["Group 1", "Group 2", "Group 3", "Group 4", "Group 5"],
                key="meta_group_num",
                label_visibility="collapsed"
            )

    final_text = ""
    if uploaded_file is not None:
        final_text = uploaded_file.read().decode("utf-8")
    elif bug_report.strip() != "":
        final_text = bug_report.strip()

    if "last_analyzed_text" not in st.session_state:
        st.session_state.last_analyzed_text = ""
    if "last_top_n" not in st.session_state:
        st.session_state.last_top_n = top_n
    if "combined_result" not in st.session_state:
        st.session_state.combined_result = None
    if "bug_record" not in st.session_state:
        st.session_state.bug_record = None
    if "retrieved_bugs" not in st.session_state:
        st.session_state.retrieved_bugs = []
    if "root_cause_result" not in st.session_state:
        st.session_state.root_cause_result = None
    if "duplicate_result" not in st.session_state:
        st.session_state.duplicate_result = []
    if "remediation_result" not in st.session_state:
        st.session_state.remediation_result = None

    should_analyze = (
        final_text != "" and
        (final_text != st.session_state.last_analyzed_text or top_n != st.session_state.last_top_n)
    )

    if final_text == "":
        st.info("Waiting for a bug report to be pasted or uploaded...")

    elif should_analyze:
        st.session_state.last_analyzed_text = final_text
        st.session_state.last_top_n = top_n

        bug_record = {
            "bug_id": "BUG-" + str(uuid.uuid4())[:8],
            "description": final_text,
            "stack_trace": final_text,
            "timestamp": datetime.now().isoformat(),
            "source": "user_submission"
        }
        st.session_state.bug_record = bug_record

        # Step 1: Triage + Log Analysis
        with st.spinner("Running Triage and Log Analysis..."):
            combined_result = run_orchestration(
                title=final_text[:80],
                description=final_text,
                stack_trace=final_text,
                bug_id=bug_record["bug_id"]
            )
            st.session_state.combined_result = combined_result

        triage_result = combined_result["triage"]
        log_result = combined_result["log_analysis"]

        # Step 2: Retrieve similar historical bugs
        with st.spinner("Retrieving similar historical bugs..."):
            try:
                retrieved_bugs = retrieve_similar_bugs(
                    final_text, model, kb_embeddings, kb_metadata, top_n=top_n
                )
            except Exception as e:
                retrieved_bugs = []
                st.session_state.retrieval_error = str(e)
            st.session_state.retrieved_bugs = retrieved_bugs

        # Step 3: Root Cause Agent
        with st.spinner("Analyzing root cause..."):
            try:
                root_cause_result = root_cause_agent(
                    bug_id=bug_record["bug_id"],
                    severity=triage_result["severity"],
                    component=triage_result["component"],
                    error_type=log_result["error_type"],
                    failure_location=log_result["failure_location"],
                    code_path=log_result["code_path"],
                    retrieved_bugs=retrieved_bugs
                )
            except Exception as e:
                root_cause_result = {
                    "root_cause_hypothesis": "Root cause analysis could not be completed due to a system error.",
                    "confidence": 0.0,
                    "supporting_evidence": [],
                    "error": str(e)
                }
            st.session_state.root_cause_result = root_cause_result

        # Step 4: Duplicate Detection Agent
        with st.spinner("Checking for duplicate submissions..."):
            try:
                duplicate_result = duplicate_detection_agent(
                    new_description=final_text,
                    error_type=log_result["error_type"],
                    component=triage_result["component"],
                    reasoning=log_result["reasoning"],
                    model=model,
                    top_n=top_n
                )
            except Exception as e:
                duplicate_result = []
                st.session_state.duplicate_error = str(e)
            st.session_state.duplicate_result = duplicate_result

        # Step 5: Remediation Agent
        with st.spinner("Generating fix recommendation..."):
            try:
                remediation_result = remediation_agent(
                    bug_id=bug_record["bug_id"],
                    severity=triage_result["severity"],
                    component=triage_result["component"],
                    error_type=log_result["error_type"],
                    failure_location=log_result["failure_location"],
                    code_path=log_result["code_path"],
                    description=final_text,
                    root_cause=root_cause_result["root_cause_hypothesis"],
                    historical_references=root_cause_result["supporting_evidence"],
                    duplicate_bug=duplicate_result if duplicate_result else None
                )
            except Exception as e:
                remediation_result = {
                    "recommended_fix": "A fix recommendation could not be generated due to a system error.",
                    "fix_steps": [], "code_example": {}, "validation_steps": [],
                    "prevention": "", "confidence": 0.0,
                    "reasoning": "Remediation agent failed.", "references_used": [],
                    "error": str(e)
                }
            st.session_state.remediation_result = remediation_result

        # Step 6: Save to SQLite
        with st.spinner("Saving submission..."):
            simple_view_for_db = build_simple_view(combined_result)
            save_submission(
                simple_view_for_db,
                bug_record["description"],
                bug_record["timestamp"],
                root_cause_hypothesis=root_cause_result["root_cause_hypothesis"],
                recommended_fix=remediation_result["recommended_fix"]
            )
            
            try:
                conn = sqlite3.connect(DEV_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO Developer_Submission 
                    (bug_id, project_name, reporter_name, developer_department, group_number, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (bug_record["bug_id"], project_name, reporter_name, dev_dept, group_num, bug_record["timestamp"]))
                conn.commit()
                conn.close()
            except Exception as e:
                st.warning(f"Could not log metadata context: {e}")

    # Display Results
    if st.session_state.combined_result is not None:
        bug_record = st.session_state.bug_record
        combined_result = st.session_state.combined_result
        simple_view = build_simple_view(combined_result)
        retrieved_bugs = st.session_state.retrieved_bugs
        root_cause_result = st.session_state.root_cause_result
        duplicate_result = st.session_state.duplicate_result
        remediation_result = st.session_state.remediation_result

        st.success("Bug report received and analyzed")
        st.subheader("Analysis Summary")

        col1, col2, col3 = st.columns(3)
        col1.metric("Severity", simple_view["severity"])
        col2.metric("Priority", simple_view["priority"])
        col3.metric("Component", simple_view["component"])

        st.write(f"**Error Type:** {simple_view['error_type']}")
        st.write(f"**Failure Location:** {simple_view['failure_location']}")

        if root_cause_result:
            hyp = root_cause_result['root_cause_hypothesis']
            st.write(f"**Root Cause (summary):** {hyp[:150]}{'...' if len(hyp) > 150 else ''}")

        if duplicate_result:
            st.write(f"**Duplicates Found:** {len(duplicate_result)} similar past submission(s)")
        else:
            st.write("**Duplicates Found:** None — this appears to be a new issue")

        if remediation_result:
            fix = remediation_result['recommended_fix']
            st.write(f"**Recommended Fix (summary):** {fix[:150]}{'...' if len(fix) > 150 else ''}")

        if st.button("Show full details (all agents)", key="show_full_details"):
            st.subheader("Full Combined Result (Triage + Log Analysis)")
            st.json(combined_result)
            st.subheader("Full Root Cause Result")
            st.json(root_cause_result)
            st.subheader("Full Duplicate Detection Result")
            st.json(duplicate_result)
            st.subheader("Full Remediation Result")
            st.json(remediation_result)

        st.divider()

        st.subheader("Root Cause Analysis")
        if root_cause_result:
            confidence = root_cause_result.get("confidence", 0.0)
            st.write(f"**Hypothesis:** {root_cause_result['root_cause_hypothesis']}")
            st.write(f"**Confidence:** {confidence:.2f}")
            if confidence < 0.6:
                st.warning("Limited historical evidence available — this is a best-guess hypothesis, not a confirmed cause.")
            if root_cause_result.get("supporting_evidence"):
                st.write("**Supporting Evidence:**")
                for ev in root_cause_result["supporting_evidence"]:
                    st.write(f"- `{ev['bug_id']}` — {ev['summary']}")
            else:
                st.write("No supporting historical evidence was found for this hypothesis.")

        st.divider()

        st.subheader("Duplicate Bugs")
        if duplicate_result:
            for d in duplicate_result:
                st.write(f"**`{d['bug_id']}`** — {d['label'].upper()} match ({d['similarity']*100:.1f}% similar)")
                st.write(d["explanation"])
                st.write("---")
        else:
            st.info("No similar past submissions found — this appears to be a new issue.")

        st.divider()

        st.subheader("Recommended Fix")
        if remediation_result:
            st.write(f"**{remediation_result['recommended_fix']}**")
            st.write(f"**Confidence:** {remediation_result.get('confidence', 0.0):.2f}")

            if remediation_result.get("fix_steps"):
                st.write("**Fix Steps:**")
                for i, step in enumerate(remediation_result["fix_steps"], 1):
                    st.write(f"{i}. {step}")

            if remediation_result.get("code_example"):
                ce = remediation_result["code_example"]
                if ce.get("before") or ce.get("after"):
                    col_before, col_after = st.columns(2)
                    with col_before:
                        st.write("**Before:**")
                        st.code(ce.get("before", "").replace("\\n", "\n"))
                    with col_after:
                        st.write("**After:**")
                        st.code(ce.get("after", "").replace("\\n", "\n"))

            if remediation_result.get("validation_steps"):
                st.write("**Validation Steps:**")
                for step in remediation_result["validation_steps"]:
                    st.write(f"- {step}")

            if remediation_result.get("prevention"):
                st.write(f"**Prevention Tip:** {remediation_result['prevention']}")

            if remediation_result.get("reasoning"):
                st.write(f"**Reasoning:** {remediation_result['reasoning']}")

            if remediation_result.get("references_used"):
                st.write("**References Used:**")
                for ref in remediation_result["references_used"]:
                    match_info = f" ({ref['match']}, {ref['similarity']*100:.0f}%)" if "match" in ref else ""
                    st.write(f"- `{ref['bug_id']}`{match_info} — {ref.get('summary', '')}")

            st.divider()

            st.subheader("Confirm Fix Outcome")
            current_bug_id = bug_record["bug_id"]
            status_key = f"fix_status_{current_bug_id}"

            if status_key not in st.session_state:
                st.session_state[status_key] = None

            if st.session_state[status_key] is None:
                col_worked, col_not_worked = st.columns(2)

                with col_worked:
                    if st.button("✅ Fix Worked", key=f"worked_{current_bug_id}"):
                        try:
                            add_resolved_bug_to_kb(
                                bug_id=current_bug_id,
                                description=bug_record["description"],
                                error_type=simple_view["error_type"],
                                severity=simple_view["severity"],
                                recommended_fix=remediation_result["recommended_fix"]
                            )

                            conn = sqlite3.connect(BUG_DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_added_to_kb", current_bug_id))
                            conn.commit()
                            conn.close()

                            st.cache_resource.clear()
                            st.session_state[status_key] = "resolved_added_to_kb"
                            st.success("Marked as resolved — added to knowledge base for future recommendations.")
                            st.rerun()

                        except Exception as e:
                            conn = sqlite3.connect(BUG_DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("resolved_kb_append_failed", current_bug_id))
                            conn.commit()
                            conn.close()

                            st.session_state[status_key] = "resolved_kb_append_failed"
                            st.error(f"Fix marked as resolved, but adding it to the knowledge base failed: {e}")
                            st.rerun()

                with col_not_worked:
                    if st.button("❌ Fix Did Not Work", key=f"notworked_{current_bug_id}"):
                        conn = sqlite3.connect(BUG_DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE bug_submissions SET status = ? WHERE bug_id = ?", ("unresolved", current_bug_id))
                        conn.commit()
                        conn.close()

                        st.session_state[status_key] = "unresolved"
                        st.info("Marked as unresolved — not added to the knowledge base.")
                        st.rerun()

            else:
                status_display = {
                    "resolved_added_to_kb": "✅ Resolved — added to knowledge base",
                    "resolved_kb_append_failed": "⚠️ Resolved, but knowledge base update failed",
                    "unresolved": "❌ Marked as unresolved"
                }
                st.write(f"**Status:** {status_display.get(st.session_state[status_key], st.session_state[status_key])}")

        st.divider()

        st.subheader("Submitted Bug Record")
        st.json(bug_record)

        st.subheader(f"Similar Past Bugs (Historical Knowledge Base, Top {top_n})")
        if retrieved_bugs:
            for rank, r in enumerate(retrieved_bugs, 1):
                st.write(f"**{rank}. {r['title']}**")
                st.write(f"Severity: {r['severity']} | Source: {r['source_dataset']} | Similarity: {r['similarity']:.2f}")
                st.write("---")
        else:
            st.info("No similar historical bugs were retrieved.")

# =====================================================================
# 📊 PAGE 2: ANALYTICS DASHBOARD
# =====================================================================
elif page == "2️⃣Analytics Dashboard":
    st.subheader("Defect Pattern Analytics")

    if st.button("🔄 Refresh Analytics", key="refresh_analytics_btn"):
        conn = sqlite3.connect(BUG_DB_PATH)
        analytics_df = pd.read_sql("SELECT * FROM bug_submissions", conn)
        conn.close()

        analytics_df['component_normalized'] = analytics_df['component'].replace(COMPONENT_MERGE_MAP)
        analytics_result = compute_defect_analytics(analytics_df)
        st.session_state.analytics_result = analytics_result

    if "analytics_result" in st.session_state:
        result = st.session_state.analytics_result

        top_sev_label, top_sev_pct = "N/A", "0%"
        if result.get("severity_breakdown") and len(result["severity_breakdown"]) > 0:
            sorted_sev = sorted(result["severity_breakdown"], key=lambda x: x["count"], reverse=True)
            top_sev_label = sorted_sev[0]["label"]
            top_sev_pct = f"{sorted_sev[0]['percent']}%"

        top_comp_label, top_comp_pct = "N/A", "0%"
        if result.get("component_breakdown") and len(result["component_breakdown"]) > 0:
            sorted_comp = sorted(result["component_breakdown"], key=lambda x: x["count"], reverse=True)
            top_comp_label = sorted_comp[0]["label"]
            top_comp_pct = f"{sorted_comp[0]['percent']}%"

        top_rc_label, top_rc_count = "N/A", "0 bugs"
        if result.get("root_cause_breakdown") and len(result["root_cause_breakdown"]) > 0:
            top_rc = result["root_cause_breakdown"][0]
            top_rc_label = top_rc["label"]
            top_rc_count = f"{top_rc['count']} bugs ({top_rc['percent']}%)"

        m1, m2, m3, m4, m5 = st.columns(5)
        
        with m1:
            with st.container(border=True):
                st.caption("📊 TOTAL SUBMISSIONS")
                st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>📁 {result['total_submissions']}</h3>", unsafe_allow_html=True)
                st.caption("Aggregated DB Entries")

        with m2:
            with st.container(border=True):
                st.caption("✅ CLASSIFIED")
                st.markdown(f"<h3 style='margin:0; color:#4ade80;'>🛡️ {result['classified_count']}</h3>", unsafe_allow_html=True)
                st.caption("Fully Categorized")

        with m3:
            with st.container(border=True):
                st.caption("⚠️ UNKNOWN RATE")
                st.markdown(f"<h3 style='margin:0; color:#fbbf24;'>⚡ {result['unknown_rate']}%</h3>", unsafe_allow_html=True)
                st.caption("Extraction Fallback")

        with m4:
            with st.container(border=True):
                st.caption("🧩 TOP COMPONENT")
                st.markdown(f"<h3 style='margin:0; color:#67e8f9; font-size: 1.25rem;'>⚙️ {top_comp_label}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume Share: {top_comp_pct}")

        with m5:
            with st.container(border=True):
                st.caption("🚨 TOP SEVERITY")
                st.markdown(f"<h3 style='margin:0; color:#f87171; font-size: 1.25rem;'>🔥 {top_sev_label}</h3>", unsafe_allow_html=True)
                st.caption(f"Dominant: {top_sev_pct}")

        st.caption(
            f"{result['classified_count']} of {result['total_submissions']} submissions were fully classified. "
            f"{result['unknown_count']} had an unclassified component due to a pipeline/LLM extraction issue."
        )

        st.divider()

        # Side-by-Side Breakdown Charts
        c_sev, c_comp = st.columns([1.5, 3])

        with c_sev:
            with st.container(border=True):
                st.markdown("##### 🎯 Severity Breakdown")
                severity_df = pd.DataFrame(result["severity_breakdown"])
                if not severity_df.empty:
                    fig_severity = px.pie(
                        severity_df, 
                        names="label", 
                        values="count", 
                        hover_data=["percent"],
                        hole=0.45,
                        color_discrete_sequence=['#3b82f6', '#ef4444', '#f59e0b', '#10b981']
                    )
                    fig_severity.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f472b6', size=12),
                        legend=dict(font=dict(color='#f472b6', size=11)),
                        margin=dict(t=20, b=20, l=10, r=10),
                        height=360
                    )
                    st.plotly_chart(fig_severity, width="stretch")
                else:
                    st.info("No severity records available.")

        with c_comp:
            with st.container(border=True):
                st.markdown("##### 🧩 Component Breakdown")
                component_df = pd.DataFrame(result["component_breakdown"])
                if not component_df.empty:
                    fig_component = px.pie(
                        component_df, 
                        names="label", 
                        values="count", 
                        hover_data=["percent"],
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    fig_component.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#ff79c6', size=11),
                        legend=dict(font=dict(color='#ff79c6', size=11)),
                        margin=dict(t=20, b=20, l=10, r=10),
                        height=360
                    )
                    st.plotly_chart(fig_component, width="stretch")
                else:
                    st.info("No component records available.")

        st.divider()

        # Root Cause Patterns & Fix Mitigations
        col_rc, col_fixes = st.columns([1.1, 1.0])

        with col_rc:
            with st.container(border=True, height=430):
                st.markdown("##### 🧬 Root Cause Patterns (Semantic Clustering)")
                st.info(f"**Dominant Root Cause:** {top_rc_label} ({top_rc_count})")
                st.caption("Note: compound submissions may describe several unrelated errors in one report.")
                
                for cluster in result["root_cause_breakdown"]:
                    with st.expander(f"{cluster['label']} — {cluster['count']} bugs ({cluster['percent']}%)"):
                        if len(cluster["distinct_error_types"]) > 1:
                            st.caption(f"Merges error types: {', '.join(cluster['distinct_error_types'])}")
                        st.write("**Bug IDs:**", ", ".join(cluster["bug_ids"]))

        with col_fixes:
            with st.container(border=True, height=430):
                rf_top_col, rf_slide_col = st.columns([1.8, 1.2])
                with rf_top_col:
                    st.markdown("##### 💡 Fix Recommendations")
                with rf_slide_col:
                    limit_fixes = st.slider("Count", min_value=2, max_value=8, value=3, key="limit_fixes_slider")

                conn = sqlite3.connect(BUG_DB_PATH)
                recent_fixes_df = pd.read_sql(
                    f"SELECT bug_id, recommended_fix, root_cause_hypothesis, status, timestamp FROM bug_submissions WHERE recommended_fix IS NOT NULL AND recommended_fix != '' ORDER BY timestamp DESC LIMIT {limit_fixes}", 
                    conn
                )
                conn.close()

                if not recent_fixes_df.empty:
                    for _, row in recent_fixes_df.iterrows():
                        with st.container(border=True):
                            ts = row['timestamp'][:10] if row['timestamp'] else ''
                            status_val = row['status'] or 'pending'
                            
                            if status_val == 'resolved_added_to_kb':
                                badge_html = '<span class="badge-verified-kb">🛡️ Verified in Vector DB</span>'
                            elif 'failed' in status_val or status_val == 'unresolved':
                                badge_html = '<span class="badge-unresolved">⚠️ Unresolved</span>'
                            else:
                                badge_html = '<span class="badge-pending">⏳ Pending Review</span>'
                                
                            st.markdown(
                                f"""
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                    <span class="badge-bug-id">🐞 {row['bug_id']} <span style="opacity:0.6; font-weight: normal;">| {ts}</span></span>
                                    {badge_html}
                                </div>
                                """, 
                                unsafe_allow_html=True
                            )
                            
                            fix_preview = row['recommended_fix']
                            if len(fix_preview) > 130:
                                fix_preview = fix_preview[:130] + "..."
                            st.write(f"**Fix:** {fix_preview}")
                else:
                    st.info("No recent remediation fixes found in the database.")

        st.divider()

        # Monthly Activity Chart
        with st.container(border=True):
            chart_head_col, chart_filter_col = st.columns([2.6, 1.4])
            
            with chart_head_col:
                st.markdown("##### 📈 Monthly Bug Submissions Velocity")
                st.caption("Defect submission frequency timeline across dates.")

            activity_df = pd.DataFrame(result["submission_activity"])
            
            if not activity_df.empty:
                activity_df['date_str'] = activity_df['date'].astype(str)
                
                def extract_month(d_val):
                    try:
                        return pd.to_datetime(d_val).strftime('%Y-%m')
                    except Exception:
                        return str(d_val)[:7]

                activity_df['month'] = activity_df['date'].apply(extract_month)
                available_months = ["All Months"] + sorted(activity_df['month'].unique().tolist(), reverse=True)

                with chart_filter_col:
                    st.markdown('<span class="badge-filter-box">📅 Filter by Month</span>', unsafe_allow_html=True)
                    selected_month = st.selectbox(
                        "Select Month", 
                        options=available_months, 
                        index=0, 
                        key="analytics_month_filter",
                        label_visibility="collapsed"
                    )

                if selected_month != "All Months":
                    filtered_activity_df = activity_df[activity_df['month'] == selected_month]
                else:
                    filtered_activity_df = activity_df

                if not filtered_activity_df.empty:
                    fig_activity = px.bar(
                        filtered_activity_df, 
                        x="date", 
                        y="count",
                        text="count",
                        color_discrete_sequence=['#0284C7']
                    )
                    fig_activity.update_traces(
                        textposition='outside', 
                        textfont=dict(color='#0F172A', size=14)
                    )
                    fig_activity.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        margin=dict(t=40, b=40, l=40, r=20),
                        height=420,
                        xaxis=dict(
                            showgrid=True,
                            gridcolor='#E2E8F0',
                            linecolor='#334155',
                            linewidth=2,
                            title=dict(text="Submission Date", font=dict(color="#0F172A", size=14)),
                            tickfont=dict(color="#0F172A", size=12)
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='#E2E8F0',
                            linecolor='#334155',
                            linewidth=2,
                            title=dict(text="Defect Count", font=dict(color="#0F172A", size=14)),
                            tickfont=dict(color="#0F172A", size=12)
                        )
                    )
                    st.plotly_chart(fig_activity, width="stretch")
                else:
                    st.warning(f"No submission activity logged for {selected_month}.")
            else:
                st.info("No activity logs available.")

    else:
        st.info("Click 'Refresh Analytics' to compute the current defect pattern analytics.")

# =====================================================================
# 📖 PAGE 3: ABOUT THE APP
# =====================================================================
elif page == "3️⃣About The App":
    st.title("About the App")
    md_path = PROJECT_ROOT / "README.md"
    if md_path.exists():
        st.markdown(md_path.read_text(encoding="utf-8"))
    else:
        st.warning("`README.md` not found in project root.")

# =====================================================================
# 📚 PAGE 4: USER GUIDE
# =====================================================================
elif page == "📚User Guide":
    st.title("📚 User Guide")
    md_path = PROJECT_ROOT / "docs" / "User_guide.md"
    if md_path.exists():
        st.markdown(md_path.read_text(encoding="utf-8"))
    else:
        st.warning("`docs/User_guide.md` not found.")

# =====================================================================
# 🧠 PAGE 5: KNOWLEDGE BASE
# =====================================================================
elif page == "🧠Knowledge Base":
    st.title("🧠 Knowledge Base Repository")
    st.caption("Aggregated vector repository and historical resolutions.")

    KB_CSV_PATH = PROJECT_ROOT / "data" / "knowledge_base_with_severity.csv"

    if os.path.exists(KB_CSV_PATH):
        kb_df = pd.read_csv(KB_CSV_PATH)
        total_kb_size = len(kb_df)

        total_fixed_till_now = 0
        if BUG_DB_PATH.exists():
            try:
                conn = sqlite3.connect(BUG_DB_PATH)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM bug_submissions 
                    WHERE status = 'resolved_added_to_kb'
                """)
                total_fixed_till_now = cursor.fetchone()[0]
                conn.close()
            except Exception:
                total_fixed_till_now = 0

        sev_col = next((c for c in kb_df.columns if "severity_mapped" in c.lower()), None)
        if sev_col and not kb_df[sev_col].dropna().empty:
            top_severity = kb_df[sev_col].mode().iloc[0]
            top_severity_count = int((kb_df[sev_col] == top_severity).sum())
        else:
            top_severity = "N/A"
            top_severity_count = 0

        comp_col = next((c for c in kb_df.columns if any(k in c.lower() for k in ["component", "module", "service"])), None)
        if comp_col and not kb_df[comp_col].dropna().empty:
            top_component = kb_df[comp_col].mode().iloc[0]
            top_component_count = int((kb_df[comp_col] == top_component).sum())
        else:
            top_component = "N/A"
            top_component_count = 0

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            with st.container(border=True):
                st.caption("📦 TOTAL KB SIZE")
                st.markdown(f"<h3 style='margin:0; color:#38bdf8;'>📚 {total_kb_size}</h3>", unsafe_allow_html=True)
                st.caption("Base Indexed Bugs")

        with k2:
            with st.container(border=True):
                st.caption("✅ FIXED ROWS ADDED TILL NOW")
                st.markdown(f"<h3 style='margin:0; color:#4ade80;'>🛡️ {total_fixed_till_now}</h3>", unsafe_allow_html=True)
                st.caption("Verified & Added to KB")

        with k3:
            with st.container(border=True):
                st.caption("🚨 DOMINANT SEVERITY")
                st.markdown(f"<h3 style='margin:0; color:#fbbf24; font-size: 1.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>🔥 {top_severity}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume: {top_severity_count} entries")

        with k4:
            with st.container(border=True):
                st.caption("🧩 FREQUENT COMPONENT")
                st.markdown(f"<h3 style='margin:0; color:#f472b6; font-size: 1.15rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>⚙️ {top_component}</h3>", unsafe_allow_html=True)
                st.caption(f"Volume: {top_component_count} entries")

        st.divider()

        with st.container(border=True):
            tb_col1, tb_col2 = st.columns([2.5, 1.5])
            with tb_col1:
                st.markdown("##### 📋 Knowledge Base Records")
            with tb_col2:
                search_query = st.text_input("🔍 Search KB", placeholder="🔍 Filter by keyword, fix, or module...", label_visibility="collapsed")

            display_df = kb_df
            if search_query.strip():
                mask = display_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False, na=False).any(), axis=1)
                display_df = display_df[mask]

            st.dataframe(display_df, width="stretch", height=450)
            st.caption(f"Showing {len(display_df)} base records + {total_fixed_till_now} dynamic verified fixes.")

    else:
        st.error(f"❌ File not found at: `{KB_CSV_PATH}`. Please check the path.")

# =====================================================================
# 🏠 PAGE 6: TELEMETRY DASHBOARD
# =====================================================================
elif page == "🏠 Dashboard":
    st.title("📊 Telemetry Dashboard")
    st.markdown('<p style="font-size: 16px; color: #FF4B4B; font-weight: 600;">Real-time telemetry of ingested defect tickets and resolution tracking.</p>', unsafe_allow_html=True)

    total_bugs = 0
    total_critical = 0
    total_kb_size = 29161
    top_dev_name = "Developer"
    top_dev_count = 0
    submissions_df = pd.DataFrame()

    kb_csv_path = PROJECT_ROOT / "data" / "knowledge_base_with_severity.csv"
    if kb_csv_path.exists():
        try:
            kb_df = pd.read_csv(kb_csv_path)
            total_kb_size = len(kb_df)
        except Exception:
            pass

    if BUG_DB_PATH.exists():
        try:
            conn = sqlite3.connect(BUG_DB_PATH)
            submissions_df = pd.read_sql("SELECT * FROM bug_submissions ORDER BY timestamp DESC", conn)
            conn.close()

            if not submissions_df.empty:
                total_bugs = len(submissions_df)
                if 'severity' in submissions_df.columns:
                    crit_mask = submissions_df['severity'].astype(str).str.lower().str.strip().isin(['critical', 'blocker', 'fatal'])
                    total_critical = int(crit_mask.sum())
        except Exception as e:
            submissions_df = pd.DataFrame()

    if DEV_DB_PATH.exists():
        try:
            conn_dev = sqlite3.connect(DEV_DB_PATH)
            dev_df = pd.read_sql("SELECT reporter_name FROM Developer_Submission", conn_dev)
            conn_dev.close()

            if not dev_df.empty and 'reporter_name' in dev_df.columns:
                clean_devs = dev_df['reporter_name'].dropna().astype(str).str.strip()
                clean_devs = clean_devs[clean_devs != ""]
                if not clean_devs.empty:
                    top_dev_name = clean_devs.mode().iloc[0]
                    top_dev_count = int((clean_devs == top_dev_name).sum())
        except Exception:
            pass

    if top_dev_count == 0 and total_bugs > 0:
        top_dev_name = st.session_state.get("user_email", "Developer").split("@")[0]
        top_dev_count = total_bugs

    # Metric Ribbon
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        with st.container(border=True):
            st.markdown('<p style="font-size: 15px; color: #091540; margin: 0; font-weight: 700;"> 📁 TOTAL SUBMITTED </p>', unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin: 8px 0; color:#38bdf8;'>🐞 {total_bugs}</h3>", unsafe_allow_html=True)
            st.markdown('<p style="font-size: 14px; color: #091540; margin: 0; font-weight: 600;"> All Ingested Tickets </p>', unsafe_allow_html=True)

    with m2:
        with st.container(border=True):
            st.markdown('<p style="font-size: 15px; color: #091540; margin: 0; font-weight: 700;"> 🚨 CRITICAL BUGS </p>', unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin: 8px 0; color:#f87171;'>🔥 {total_critical}</h3>", unsafe_allow_html=True)
            st.markdown('<p style="font-size: 14px; color: #091540; margin: 0; font-weight: 600;"> Fatal & Blocker Defects </p>', unsafe_allow_html=True)

    with m3:
        with st.container(border=True):
            st.markdown('<p style="font-size: 15px; color: #091540; margin: 0; font-weight: 700;"> 🧠 KNOWLEDGE BASE SIZE </p>', unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin: 8px 0; color:#4ade80;'>📚 {total_kb_size}</h3>", unsafe_allow_html=True)
            st.markdown('<p style="font-size: 14px; color: #091540; margin: 0; font-weight: 600;"> Base Indexed Bug Records </p>', unsafe_allow_html=True)

    with m4:
        with st.container(border=True):
            st.markdown('<p style="font-size: 15px; color: #091540; margin: 0; font-weight: 700;"> 🏆 TOP CONTRIBUTOR </p>', unsafe_allow_html=True)
            st.markdown(f"<h3 style='margin: 8px 0; color:#fbbf24; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>👨‍💻 {top_dev_name}</h3>", unsafe_allow_html=True)
            st.markdown(f'<p style="font-size: 14px; color: #091540; margin: 0; font-weight: 600;"> {top_dev_count} Submissions logged </p>', unsafe_allow_html=True)

    st.divider()

    # =====================================================================
    # 🔔 PENDING REVIEWS & MANUAL EMAIL TRIGGER (With Stack Trace)
    # =====================================================================
    pending_bugs = get_pending_review_bugs()

    with st.container(border=True):
        st.markdown(f"##### ⏳ Pending Verification Reviews ({len(pending_bugs)})")
        st.caption("Tickets awaiting outcome confirmation. Click remind to send an email with the stack trace included.")

        if pending_bugs:
            for b_id, b_sev, b_comp, b_trace, b_time in pending_bugs[:5]: # Shows top 5 pending
                p_col1, p_col2, p_col3, p_btn = st.columns([2, 2, 2, 1.5])
                with p_col1:
                    st.markdown(f"**🐞 `{b_id}`**")
                with p_col2:
                    st.write(f"**Component:** {b_comp or 'N/A'}")
                with p_col3:
                    st.write(f"**Date:** {b_time[:10] if b_time else 'N/A'}")
                with p_btn:
                    if st.button("📧 Remind", key=f"manual_remind_{b_id}", width="stretch"):
                        recipient = get_ticket_recipient_email(b_id)
                        if recipient:
                            success = send_verification_email_api(recipient, b_id, stack_trace=b_trace or "")
                            if success:
                                st.success(f"Email sent to {recipient} with stack trace!")
                        else:
                            st.warning(f"No valid email found for {b_id}")
        else:
            st.success("🎉 All bug tickets have been verified!")

    st.divider()

    # Telemetry Feed Table
    with st.container(border=True):
        t_head, t_search = st.columns([2.6, 1.4])
        with t_head:
            st.markdown("##### 🗂️ Ingested Defect Tickets")
            st.caption("Direct telemetry feed from `bug_submissions.db`.")
        with t_search:
            db_search = st.text_input("Search Database", placeholder="Filter by ID, component, severity...", label_visibility="collapsed")

        if not submissions_df.empty:
            cols_to_show = [c for c in ['bug_id', 'severity', 'priority', 'component', 'error_type', 'status', 'timestamp', 'recommended_fix'] if c in submissions_df.columns]
            table_df = submissions_df[cols_to_show].copy()

            if db_search.strip():
                mask = table_df.astype(str).apply(lambda row: row.str.contains(db_search, case=False, na=False).any(), axis=1)
                table_df = table_df[mask]

            st.dataframe(table_df, width="stretch", height=450)
            st.caption(f"Displaying {len(table_df)} of {total_bugs} total records.")
        else:
            st.info("No bug records found in `bug_submissions.db`. Submit a bug to populate telemetry.")