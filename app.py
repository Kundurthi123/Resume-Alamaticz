import streamlit as st
import os
import shutil
import sqlite3
import pandas as pd
import json
import gc
import base64
from datetime import datetime
from typing import List
from dotenv import load_dotenv

# LangChain & AI Imports
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_classic.chains import RetrievalQA
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
import plotly.express as px
import plotly.graph_objects as go

# --- Setup & Configuration ---
load_dotenv()
st.set_page_config(page_title="Hire AI | Intelligent Recruitment", layout="wide", page_icon="🎯")

CHROMA_PATH = "chroma_db"
UPLOAD_DIR = "static"
STATS_DB = "stats.db"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Database & Storage ---
def init_db():
    conn = sqlite3.connect(STATS_DB)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_metadata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            full_name TEXT,
            total_experience REAL DEFAULT 0.0,
            pega_experience REAL DEFAULT 0.0,
            skills TEXT,
            certifications TEXT,
            ctc TEXT,
            notice_period TEXT,
            current_organization TEXT,
            email TEXT,
            phone TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Migration: Add columns if they don't exist
    cursor.execute("PRAGMA table_info(candidate_metadata)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    for col in ['current_organization', 'email', 'phone']:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE candidate_metadata ADD COLUMN {col} TEXT")
    conn.commit()
    conn.close()

def get_metadata_df():
    conn = sqlite3.connect(STATS_DB)
    try:
        df = pd.read_sql_query("SELECT * FROM candidate_metadata ORDER BY timestamp DESC", conn)
        if 'id' in df.columns: df = df.drop(columns=['id'])
    except:
        df = pd.DataFrame()
    conn.close()
    return df

def save_to_db(df: pd.DataFrame):
    conn = sqlite3.connect(STATS_DB)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidate_metadata")
    df.to_sql('candidate_metadata', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()

def log_candidate(data: dict):
    conn = sqlite3.connect(STATS_DB)
    cols = ['filename', 'full_name', 'total_experience', 'pega_experience', 'skills', 'certifications', 'ctc', 'notice_period', 'current_organization', 'email', 'phone']
    vals = [data.get(c, 'N/A') for c in cols]
    cursor = conn.cursor()
    cursor.execute(f"INSERT INTO candidate_metadata ({','.join(cols)}) VALUES ({','.join(['?']*len(cols))})", vals)
    conn.commit()
    conn.close()

init_db()

# --- AI & Models ---
@st.cache_resource
def load_models():
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    llm = ChatGroq(temperature=0.1, model_name="llama-3.1-8b-instant", groq_api_key=GROQ_API_KEY)
    return embeddings, llm

# --- UI Helpers ---
def get_base64(path):
    if not os.path.exists(path): return None
    with open(path, "rb") as f: return base64.b64encode(f.read()).decode()

logo_b64 = get_base64("logo.png")

# --- Authentication Logic ---
def init_session_state():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = "login"  # login | register | forgot
    if 'login_tab' not in st.session_state:
        st.session_state.login_tab = "Gmail"  # Gmail | Mobile

def login_page():
    # --- Background using Alamaticzs logo image ---
    bg_b64 = get_base64("alamaticzs_bg.png") or get_base64("logo.png")
    bg_style = f'background-image: url("data:image/png;base64,{bg_b64}"); background-size: cover; background-position: center; background-repeat: no-repeat;' if bg_b64 else ''
    
    mode = st.session_state.auth_mode
    tab  = st.session_state.login_tab

    # ── Outer wrapper with background ──
    st.markdown(f"""
    <style>
    .auth-backdrop {{
        {bg_style}
        position: fixed; inset: 0; z-index: -1;
        filter: brightness(0.25) blur(2px);
    }}
    .auth-overlay {{
        position: fixed; inset: 0; z-index: -1;
        background: linear-gradient(135deg,rgba(1,22,39,0.85) 0%,rgba(2,48,71,0.7) 100%);
    }}
    .auth-card {{
        background: rgba(2,36,56,0.82);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255,183,3,0.45);
        border-radius: 24px;
        padding: 2.5rem 2.2rem 2rem;
        width: 100%;
        max-width: 430px;
        margin: auto;
        box-shadow: 0 8px 40px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,183,3,0.12);
    }}
    .auth-brand {{
        text-align: center;
        margin-bottom: 1.8rem;
    }}
    .auth-brand-title {{
        font-family: 'Outfit', sans-serif;
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FFB703, #FB8500);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 0.04rem;
        text-transform: uppercase;
    }}
    .auth-brand-sub {{
        font-size: 0.82rem;
        color: #8ECAE6;
        letter-spacing: 0.12rem;
        text-transform: uppercase;
        margin-top: 2px;
    }}
    .auth-tab-row {{
        display: flex;
        gap: 8px;
        margin-bottom: 1.5rem;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 4px;
    }}
    .auth-tabs-wrapper {{ margin-bottom: 1rem; }}
    .auth-link {{
        background: none; border: none;
        color: #FFB703; cursor: pointer;
        font-size: 0.88rem; font-weight: 600;
        text-decoration: underline; padding: 0;
    }}
    .auth-divider {{
        display: flex; align-items: center; gap: 12px;
        margin: 1.2rem 0;
        color: #8ECAE6; font-size: 0.82rem;
    }}
    .auth-divider::before, .auth-divider::after {{
        content: ''; flex: 1;
        height: 1px; background: rgba(142,202,230,0.3);
    }}
    .auth-footer {{
        text-align: center; margin-top: 1.5rem;
        color: #8ECAE6; font-size: 0.8rem;
    }}
    /* Inner card centering wrapper */
    .auth-center-wrap {{
        display: flex; justify-content: center;
        align-items: center; min-height: 90vh;
        flex-direction: column;
    }}
    </style>
    <div class="auth-backdrop"></div>
    <div class="auth-overlay"></div>
    """, unsafe_allow_html=True)

    # Centre the card
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        # ── Brand Header ──
        logo_img_auth = f'<img src="data:image/png;base64,{bg_b64}" style="height:64px; border-radius:10px; margin-bottom:10px;">' if bg_b64 else '🎯'
        st.markdown(f"""
        <div class="auth-card">
            <div class="auth-brand">
                {logo_img_auth}
                <div class="auth-brand-title">Alamaticzs Solutions</div>
                <div class="auth-brand-sub">{'Sign in to your account' if mode=='login' else 'Create a new account' if mode=='register' else 'Reset your password'}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if mode == "login":
            # ── Login Tab Toggle ──
            tab_col1, tab_col2 = st.columns(2)
            with tab_col1:
                if st.button("📧 Gmail / Email",
                             use_container_width=True,
                             type="primary" if tab == "Gmail" else "secondary",
                             key="tab_gmail"):
                    st.session_state.login_tab = "Gmail"
                    st.rerun()
            with tab_col2:
                if st.button("📱 Mobile Number",
                             use_container_width=True,
                             type="primary" if tab == "Mobile" else "secondary",
                             key="tab_mobile"):
                    st.session_state.login_tab = "Mobile"
                    st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)

            if tab == "Gmail":
                email = st.text_input("Email / Gmail", placeholder="you@gmail.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")

                # Forgot password row
                fp_col, _ = st.columns([1, 1])
                with fp_col:
                    if st.button("Forgot password?", key="btn_forgot"):
                        st.session_state.auth_mode = "forgot"
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔐  SIGN IN", use_container_width=True, type="primary", key="btn_login_gmail"):
                    if email and password:
                        # Accept any non-empty credentials, set name from email
                        st.session_state.logged_in = True
                        st.session_state.user_name = email.split('@')[0].title()
                        st.rerun()
                    else:
                        st.error("Please enter your email and password.")

            else:  # Mobile tab
                mobile = st.text_input("Mobile Number", placeholder="+91 98765 43210", key="login_mobile")
                password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass_m")

                fp_col, _ = st.columns([1, 1])
                with fp_col:
                    if st.button("Forgot password?", key="btn_forgot_m"):
                        st.session_state.auth_mode = "forgot"
                        st.rerun()

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔐  SIGN IN", use_container_width=True, type="primary", key="btn_login_mobile"):
                    if mobile and password:
                        st.session_state.logged_in = True
                        st.session_state.user_name = "User"
                        st.rerun()
                    else:
                        st.error("Please enter your mobile number and password.")

            # ── Create account link ──
            st.markdown("<div style='text-align:center; margin-top:1rem; color:#8ECAE6; font-size:0.9rem;'>Don't have an account?</div>", unsafe_allow_html=True)
            if st.button("✨  Create New Account", use_container_width=True, type="secondary", key="btn_go_register"):
                st.session_state.auth_mode = "register"
                st.rerun()

        elif mode == "register":
            full_name = st.text_input("Full Name", placeholder="John Doe", key="reg_name")
            reg_email = st.text_input("Email / Gmail", placeholder="you@gmail.com", key="reg_email")
            reg_mobile = st.text_input("Mobile Number (optional)", placeholder="+91 98765 43210", key="reg_mobile")
            reg_pass   = st.text_input("Password", type="password", placeholder="Create a strong password", key="reg_pass")
            reg_pass2  = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="reg_pass2")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀  CREATE ACCOUNT", use_container_width=True, type="primary", key="btn_register"):
                if not full_name or not reg_email or not reg_pass:
                    st.error("Please fill in Name, Email, and Password.")
                elif reg_pass != reg_pass2:
                    st.error("Passwords do not match!")
                else:
                    st.success(f"Account created for {full_name}! Please sign in.")
                    st.session_state.auth_mode = "login"
                    st.rerun()

            st.markdown("<div style='text-align:center; margin-top:1rem; color:#8ECAE6; font-size:0.9rem;'>Already have an account?</div>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True, type="secondary", key="btn_back_login"):
                st.session_state.auth_mode = "login"
                st.rerun()

        elif mode == "forgot":
            st.markdown("<p style='color:#8ECAE6; font-size:0.9rem; text-align:center; margin-bottom:1.2rem;'>Enter your registered email or mobile number. We'll send you a reset link.</p>", unsafe_allow_html=True)
            fp_input = st.text_input("Email or Mobile Number", placeholder="you@gmail.com  or  +91 98765 43210", key="fp_input")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📨  SEND RESET LINK", use_container_width=True, type="primary", key="btn_send_reset"):
                if fp_input:
                    st.success("✅ Reset link sent! Check your email / SMS inbox.")
                else:
                    st.error("Please enter your email or mobile number.")

            if st.button("← Back to Sign In", use_container_width=True, type="secondary", key="btn_back_from_forgot"):
                st.session_state.auth_mode = "login"
                st.rerun()

    # Footer
    st.markdown("""
    <div style="text-align:center; padding: 2rem 0 1rem; color:#8ECAE6; font-size:0.78rem;">
        © 2025 Alamaticzs Solutions. All Rights Reserved. &nbsp;|&nbsp; Innovation • Excellence • Reliability
    </div>
    """, unsafe_allow_html=True)

def profile_header():
    # CSS for top-right profile
    st.markdown(f"""
    <style>
    .top-right-profile {{
        position: fixed;
        top: 15px;
        right: 25px;
        z-index: 999;
        display: flex;
        align-items: center;
        gap: 12px;
        background: rgba(2, 48, 71, 0.9);
        padding: 8px 18px;
        border-radius: 40px;
        border: 1px solid var(--gold);
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}
    .profile-icon {{
        width: 32px;
        height: 32px;
        background: var(--gold);
        border-radius: 50%;
        display: flex;
        justify-content: center;
        align-items: center;
        color: var(--navy);
        font-weight: 800;
        font-family: var(--fh);
    }}
    .user-name {{
        color: white;
        font-weight: 600;
        font-family: var(--fb);
        font-size: 0.9rem;
    }}
    </style>
    <div class="top-right-profile">
        <span class="user-name">{st.session_state.user_name}</span>
        <div class="profile-icon">{st.session_state.user_name[0] if st.session_state.user_name else 'H'}</div>
    </div>
    """, unsafe_allow_html=True)

# --- Styling & CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');

:root {
    --primary:   #FB8500; /* Logo Orange */
    --gold:      #FFB703; /* Logo Gold */
    --navy:      #023047; /* Logo Deep Navy */
    --sky:       #219EBC; /* Logo Light Blue */
    --text:      #FFFFFF;
    --text-dim:  #8ECAE6;
    --card-bg:   rgba(2, 48, 71, 0.6);
    --border:    rgba(33, 158, 188, 0.3);
    --fh: 'Outfit', sans-serif;
    --fb: 'Inter', sans-serif;
}

html, body, [class*="css"] { 
    font-family: var(--fb) !important; 
    background-color: var(--navy) !important;
}

.stApp {
    background: radial-gradient(circle at top right, #051923, #023047) !important;
    color: var(--text) !important;
}

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { display: none !important; }

/* ── Heading Styling ── */
.title-font {
    font-family: var(--fh) !important;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.1rem;
}

/* ── Sidebar Styling ── */
[data-testid="stSidebar"] { 
    background: #011627 !important; 
    border-right: 1px solid var(--border) !important; 
}

.sb-brand {
    display:flex; align-items:center; gap:12px;
    padding:1.5rem 1.2rem; border-bottom:1px solid var(--border); margin-bottom:1.5rem;
}

.sb-brand-name {
    font-family:var(--fh); font-size:1.5rem; font-weight:800; color: var(--gold);
}

/* Sidebar Nav Buttons Styling */
[data-testid="stSidebarNav"] { display: none; }
div[role="radiogroup"] { display: flex; flex-direction: column; gap: 8px; padding: 0 12px; }
div[role="radiogroup"] label > div:first-child { display: none !important; }
div[role="radiogroup"] label { padding: 0 !important; margin: 0 !important; width: 100% !important; }

div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
    padding: 12px 18px !important;
    border-radius: 12px !important;
    color: #8ECAE6 !important;
    font-weight: 500 !important;
    transition: all 0.3s ease !important;
    border: 1px solid transparent !important;
}

div[role="radiogroup"] label:hover div[data-testid="stMarkdownContainer"] {
    background: rgba(255, 183, 3, 0.1) !important;
    color: var(--gold) !important;
}

div[role="radiogroup"] label[data-selected="true"] div[data-testid="stMarkdownContainer"] {
    background: linear-gradient(90deg, var(--primary), var(--gold)) !important;
    color: #fff !important;
    box-shadow: 0 8px 15px rgba(251, 133, 0, 0.2) !important;
}

/* ── Page Header ── */
.pg-header {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 15px;
    padding: 1rem 0;
    margin-bottom: 2rem;
    width: 100%;
    border-bottom: 1px solid var(--border);
}

/* ── Cards ── */
.card {
    background: var(--card-bg);
    padding: 1.5rem;
    border-radius: 20px;
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    margin-bottom: 1.5rem;
}

.card-title {
    font-size: 1.25rem;
    font-weight: 700;
    font-family: var(--fh);
    color: var(--gold);
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Custom Table/Dataframe Overrides */
.stDataFrame {
    border-radius: 10px;
    border: 1px solid var(--border) !important;
}

/* Visibility Fixes for Dark Mode */
.stApp p, .stApp span, .stApp label, .stApp li {
    color: #FFFFFF !important;
}

[data-testid="stExpander"] {
    background-color: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 15px !important;
}

[data-testid="stExpander"] summary {
    background-color: rgba(0, 0, 0, 0.2) !important;
    color: var(--gold) !important;
    border-radius: 15px 15px 0 0 !important;
}

[data-testid="stExpander"] summary p {
    color: var(--gold) !important;
    font-weight: 700 !important;
    font-size: 1.1rem !important;
}

[data-testid="stFileUploader"] {
    background-color: rgba(0, 0, 0, 0.3) !important;
    padding: 2rem !important;
    border: 2px dashed var(--sky) !important;
    border-radius: 15px !important;
}

[data-testid="stFileUploader"] section {
    background-color: transparent !important;
    color: #FFFFFF !important;
}

[data-testid="stVerticalBlock"] > div > div > div[style*="background-color: white"] {
    background-color: transparent !important;
}

[data-testid="stFileUploaderInstructions"] p {
    color: #FFFFFF !important;
    font-weight: 600 !important;
}

[data-testid="stFileUploaderFileName"] {
    color: var(--gold) !important;
    font-weight: 700 !important;
}

.stAlert p {
    color: #FFFFFF !important;
}

.stDataFrame [role="columnheader"] {
    background-color: var(--navy) !important;
    color: var(--gold) !important;
}

.stDataFrame [role="gridcell"] {
    color: #FFFFFF !important;
}
</style>
""", unsafe_allow_html=True)

# --- Execution ---
init_session_state()

if not st.session_state.logged_in:
    login_page()
else:
    profile_header()
    
    # Load Models
    embeddings, llm = load_models()
    
    # --- Sidebar Nav ---
    with st.sidebar:
        logo_img_sb = f'<img src="data:image/png;base64,{logo_b64}" style="height:40px;">' if logo_b64 else '🎯'
        st.markdown(f'<div class="sb-brand">{logo_img_sb}<span class="sb-brand-name">Hire AI</span></div>', unsafe_allow_html=True)
        page = st.radio("Navigation", ["Hire Dashboard", "Upload Resume", "Chat with Hire"], label_visibility="collapsed")
        
        st.markdown("<br>"*10, unsafe_allow_html=True)
        if st.button("LOGOUT", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

    # --- Header ---
    logo_img = f'<img src="data:image/png;base64,{logo_b64}" style="height:50px;">' if logo_b64 else '🎯'
    st.markdown(f"""
    <div class="pg-header">
        {logo_img}
        <div class="title-font" style="font-size: 2rem; color: var(--gold); margin-left: 15px;">Alamaticzs solution</div>
    </div>
    """, unsafe_allow_html=True)

    # --- Page Content ---
    if page == "Hire Dashboard":
        st.subheader("📊 Candidate Analytics")
        df = get_metadata_df()
        
        if df.empty:
            st.info("No candidates analyzed yet. Go to 'Upload Resume' to start.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="card"><div class="card-title">Experience Comparison</div>', unsafe_allow_html=True)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df['full_name'], y=df['total_experience'], name='Total Exp', marker_color='#FB8500'))
                fig.add_trace(go.Bar(x=df['full_name'], y=df['pega_experience'], name='Pega Exp', marker_color='#FFB703'))
                fig.update_layout(barmode='group', template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
                st.plotly_chart(fig, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
            with col2:
                st.markdown('<div class="card"><div class="card-title">Notice Period Overview</div>', unsafe_allow_html=True)
                fig2 = px.bar(df, x='full_name', y='notice_period', color='notice_period', template='plotly_dark')
                fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400, showlegend=False)
                st.plotly_chart(fig2, use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)

    elif page == "Upload Resume":
        st.subheader("📤 Resume Processing")
        
        with st.expander("Upload Resumes", expanded=True):
            uploaded_files = st.file_uploader("Select Resumes (PDF/DOCX)", type=["pdf", "docx"], accept_multiple_files=True)
            if st.button("Analyze Resumes", use_container_width=True):
                if uploaded_files:
                    with st.spinner("AI is extracting data..."):
                        all_docs = []
                        for file in uploaded_files:
                            path = os.path.join(UPLOAD_DIR, file.name)
                            with open(path, "wb") as f: f.write(file.getbuffer())
                            
                            if file.name.endswith(".pdf"):
                                from langchain_community.document_loaders import PyMuPDFLoader
                                loader = PyMuPDFLoader(path)
                            else:
                                loader = Docx2txtLoader(path)
                            
                            docs = loader.load()
                            text = "\n".join([d.page_content for d in docs])
                            
                            # Extraction Logic
                            prompt_extract = """
                            Extract candidate information from the resume text into JSON format.
                            Fields: full_name, total_experience (number), pega_experience (number), skills (comma separated), certifications (comma separated), ctc, notice_period, current_organization, email, phone.
                            Return ONLY pure JSON.
                            """
                            try:
                                resp = llm.invoke([HumanMessage(content=f"{prompt_extract}\n\nResume:\n{text[:6000]}")])
                                data = json.loads(resp.content.strip().split('```json')[1].split('```')[0].strip() if '```json' in resp.content else resp.content.strip())
                                data['filename'] = file.name
                                log_candidate(data)
                            except:
                                log_candidate({"filename": file.name, "full_name": file.name})
                            
                            for d in docs: d.metadata['source'] = file.name
                            all_docs.extend(docs)
                        
                        if all_docs:
                            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
                            chunks = text_splitter.split_documents(all_docs)
                            Chroma.from_documents(chunks, embeddings, persist_directory=CHROMA_PATH)
                        
                        st.success("Analysis Complete!")
                        st.rerun()
        
        st.markdown("---")
        st.subheader("📋 Candidate Data Table")
        df = get_metadata_df()
        if not df.empty:
            cols = ['filename', 'full_name', 'total_experience', 'pega_experience', 'skills', 'certifications', 'ctc', 'notice_period', 'current_organization', 'email', 'phone']
            df = df[cols]
            
            column_config = {
                "filename": st.column_config.LinkColumn("File Name", validate=r"^/static/.*", display_text=r"^/static/(.*)"),
                "current_organization": "Organization", "email": "Email", "phone": "Phone"
            }
            
            display_df = df.copy()
            display_df['filename'] = display_df['filename'].apply(lambda x: f"/static/{x}")
            
            edited_df = st.data_editor(display_df, column_config=column_config, num_rows="dynamic", use_container_width=True, height=500)
            
            if st.button("Save Changes"):
                save_df = edited_df.copy()
                save_df['filename'] = save_df['filename'].apply(lambda x: x.replace("/static/", ""))
                save_to_db(save_df)
                st.success("Data Saved!")
                st.rerun()

    elif page == "Chat with Hire":
        st.subheader("💬 Chat with Hire AI")
        if not os.path.exists(CHROMA_PATH):
            st.warning("Please upload resumes first.")
        else:
            if "messages" not in st.session_state: st.session_state.messages = []
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            if prompt := st.chat_input("Ask about candidates..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"): st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
                    retriever = db.as_retriever(search_kwargs={"k": 5})
                    qa_prompt = PromptTemplate(template="""Answer based on resume context ONLY.
                    Context: {context} Question: {question} Answer:""", input_variables=["context", "question"])
                    qa = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=retriever, chain_type_kwargs={"prompt": qa_prompt})
                    ans = qa.invoke(prompt)['result']
                    st.markdown(ans)
                    st.session_state.messages.append({"role": "assistant", "content": ans})

    st.markdown('<br><br>', unsafe_allow_html=True)
