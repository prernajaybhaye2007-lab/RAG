import sqlite3
import hashlib
import datetime
import io
import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Security Helper
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, hashed_password: str) -> bool:
    return hash_password(password) == hashed_password

# Database Setup
def init_db():
    conn = sqlite3.connect("scheme_assistant.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT,
            full_name TEXT,
            age INTEGER,
            education TEXT,
            income REAL,
            state TEXT,
            category TEXT
        )
    """)
    
    # Schemes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schemes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            ministry TEXT,
            min_age INTEGER,
            max_age INTEGER,
            max_income REAL,
            education_req TEXT,
            benefits TEXT,
            documents TEXT
        )
    """)
    
    # Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_username TEXT,
            action TEXT,
            timestamp TEXT
        )
    """)

    # Applications Tracker Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            scheme_id INTEGER,
            status TEXT,
            last_updated TEXT,
            UNIQUE(username, scheme_id)
        )
    """)
    
    # Seed Admin User if not exists
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_admin_pass = hash_password("admin123")
        cursor.execute("""
            INSERT INTO users (username, password, role, full_name, age, education, income, state, category)
            VALUES ('admin', ?, 'admin', 'System Administrator', 35, 'Post Graduate', 0.0, 'National', 'General')
        """, (hashed_admin_pass,))
        
    # Seed Sample Schemes if empty
    cursor.execute("SELECT COUNT(*) FROM schemes")
    if cursor.fetchone()[0] == 0:
        sample_schemes = [
            ("Start-up India Seed Fund Scheme", "Ministry of Commerce and Industry", 18, 60, 10000000.0, "Graduate", 
             "Financial assistance up to Rs. 20 Lakhs for proof of concept, prototype development, and market entry.", 
             "Aadhar Card, PAN Card, Startup Recognition Certificate (DPIIT), Business Plan, Bank Account Details"),
            
            ("Pradhan Mantri Kaushal Vikas Yojana (PMKVY)", "Ministry of Skill Development", 15, 45, 500000.0, "High School", 
             "Industry-relevant skill training with free assessment, certification, and monetary rewards upon completion.", 
             "Aadhar Card, Bank Passbook, Educational Certificates, Passport Size Photograph"),
            
            ("National Scholarship Portal (NSP) - Post Matric", "Ministry of Minority Affairs", 16, 30, 250000.0, "Under Graduate", 
             "Tuition fee waiver and maintenance allowance for higher education studies.", 
             "Aadhar Card, Income Certificate, Caste Certificate (if applicable), Previous Year Marksheet, Fee Receipt")
        ]
        cursor.executemany("""
            INSERT INTO schemes (title, ministry, min_age, max_age, max_income, education_req, benefits, documents)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_schemes)
        
    conn.commit()
    conn.close()

init_db()

# Helper Functions
def get_connection():
    return sqlite3.connect("scheme_assistant.db", check_same_thread=False)

def log_audit(admin_user, action_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO audit_logs (admin_username, action, timestamp) VALUES (?, ?, ?)",
                   (admin_user, action_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def authenticate(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and verify_password(password, user[2]):
        return user
    return None

def register_user(username, password, full_name, age, education, income, state, category):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        hashed_pass = hash_password(password)
        cursor.execute("""
            INSERT INTO users (username, password, role, full_name, age, education, income, state, category)
            VALUES (?, ?, 'citizen', ?, ?, ?, ?, ?, ?)
        """, (username, hashed_pass, full_name, age, education, income, state, category))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def generate_pdf_kit(user_name, matched_schemes):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = styles["Heading1"]
    body_style = styles["BodyText"]

    story.append(Paragraph(f"Citizen Application Kit for {user_name}", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", body_style))
    story.append(Spacer(1, 18))

    for scheme in matched_schemes:
        story.append(Paragraph(f"<b>Scheme:</b> {scheme['title']}", styles["Heading2"]))
        story.append(Paragraph(f"<b>Ministry:</b> {scheme['ministry']}", body_style))
        story.append(Paragraph(f"<b>Benefits:</b> {scheme['benefits']}", body_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Mandatory Documents Checklist:</b>", body_style))
        
        docs = scheme['documents'].split(",")
        for d in docs:
            story.append(Paragraph(f"[  ] {d.strip()}", body_style))
        story.append(Spacer(1, 14))

    doc.build(story)
    buffer.seek(0)
    return buffer

# Streamlit Configuration
st.set_page_config(page_title="Citizen Scheme Navigator", layout="wide")

TRANSLATIONS = {
    "English": {
        "title": "Government Scheme Eligibility & Citizen Application Assistant",
        "welcome": "Discover government schemes matching your profile and track your application checklist.",
        "benefits": "Benefits in Simple Terms",
        "checklist": "Mandatory Document Checklist",
        "status": "Application Status",
        "save": "Save Profile",
        "download": "Download Complete Application Kit (PDF)"
    },
    "Hindi": {
        "title": "नागरिक योजना नेविगेटर और सहायक",
        "welcome": "अपनी प्रोफ़ाइल से मेल खाने वाली सरकारी योजनाओं की खोज करें और अपने आवेदन की प्रगति को ट्रैक करें।",
        "benefits": "सरल शब्दों में लाभ",
        "checklist": "अनिवार्य दस्तावेजों की सूची",
        "status": "आवेदन की स्थिति",
        "save": "प्रोफ़ाइल सहेजें",
        "download": "संपूर्ण आवेदन किट डाउनलोड करें (PDF)"
    }
}

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""
    st.session_state["full_name"] = ""

lang = st.sidebar.selectbox("Choose Language / भाषा चुनें", ["English", "Hindi"])
t = TRANSLATIONS[lang]

# Login / Registration View
if not st.session_state["logged_in"]:
    st.title(t["title"])
    st.markdown(t["welcome"])
    
    tab1, tab2 = st.tabs(["Login", "Register New Account"])
    
    with tab1:
        st.subheader("Account Login")
        login_user = st.text_input("Username", key="login_user")
        login_pass = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login"):
            user = authenticate(login_user, login_pass)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["username"] = user[1]
                st.session_state["role"] = user[3]
                st.session_state["full_name"] = user[4]
                st.success(f"Welcome back, {user[4]}!")
                st.rerun()
            else:
                st.error("Invalid username or password.")
                
    with tab2:
        st.subheader("Citizen Registration")
        reg_user = st.text_input("Choose Username")
        reg_pass = st.text_input("Choose Password", type="password")
        reg_name = st.text_input("Full Name")
        reg_age = st.number_input("Age", min_value=10, max_value=100, value=25)
        reg_edu = st.selectbox("Highest Education Level", ["High School", "Under Graduate", "Graduate", "Post Graduate", "None"])
        reg_income = st.number_input("Annual Family Income (Rs.)", min_value=0.0, step=10000.0, value=300000.0)
        reg_state = st.text_input("State of Residence", value="Maharashtra")
        reg_cat = st.selectbox("Category", ["General", "OBC", "SC", "ST"])
        
        if st.button("Register"):
            if reg_user and reg_pass and reg_name:
                success = register_user(reg_user, reg_pass, reg_name, reg_age, reg_edu, reg_income, reg_state, reg_cat)
                if success:
                    st.success("Registration successful! Please switch to the Login tab.")
                else:
                    st.error("Username already exists. Choose another.")
            else:
                st.warning("Please fill in all required fields.")

else:
    # Navigation Sidebar
    st.sidebar.markdown(f"**User:** {st.session_state['full_name']}")
    st.sidebar.markdown(f"**Role:** `{st.session_state['role'].upper()}`")
    
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.session_state["role"] = ""
        st.session_state["full_name"] = ""
        st.rerun()

    # Admin View
    if st.session_state["role"] == "admin":
        st.title("Admin Dashboard & Governance Control")
        admin_tab1, admin_tab2, admin_tab3 = st.tabs(["Manage Schemes", "Audit Logs", "Registered Citizens"])
        
        with admin_tab1:
            st.subheader("Add New Scheme")
            with st.form("add_scheme"):
                title = st.text_input("Scheme Title")
                ministry = st.text_input("Nodal Ministry")
                c1, c2 = st.columns(2)
                with c1:
                    min_age = st.number_input("Min Age", 0, 100, 18)
                    max_age = st.number_input("Max Age", 0, 100, 60)
                with c2:
                    max_income = st.number_input("Max Income (Rs.)", 0.0, 10000000.0, 500000.0)
                    education_req = st.selectbox("Education Required", ["None", "High School", "Under Graduate", "Graduate", "Post Graduate"])
                benefits = st.text_area("Benefits Description")
                documents = st.text_area("Mandatory Documents (Comma Separated)")
                
                if st.form_submit_button("Publish Scheme"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO schemes (title, ministry, min_age, max_age, max_income, education_req, benefits, documents)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, ministry, min_age, max_age, max_income, education_req, benefits, documents))
                    conn.commit()
                    conn.close()
                    log_audit(st.session_state["username"], f"Added new scheme: {title}")
                    st.success("Scheme published successfully!")

            st.subheader("Existing Schemes")
            conn = get_connection()
            schemes_df = pd.read_sql("SELECT * FROM schemes", conn)
            conn.close()
            st.dataframe(schemes_df, use_container_width=True)

        with admin_tab2:
            st.subheader("System Security Audit Logs")
            conn = get_connection()
            audit_df = pd.read_sql("SELECT * FROM audit_logs ORDER BY id DESC", conn)
            conn.close()
            st.dataframe(audit_df, use_container_width=True)

        with admin_tab3:
            st.subheader("Registered Citizens")
            conn = get_connection()
            users_df = pd.read_sql("SELECT id, username, full_name, age, education, income, state, category FROM users WHERE role='citizen'", conn)
            conn.close()
            st.dataframe(users_df, use_container_width=True)

    # Citizen View
    else:
        st.title(t["title"])
        st.markdown(t["welcome"])
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT age, education, income, state, category FROM users WHERE username = ?", (st.session_state["username"],))
        u_age, u_edu, u_income, u_state, u_cat = cursor.fetchone()
        conn.close()

        with st.expander("Profile & Criteria Settings", expanded=False):
            with st.form("edit_profile"):
                new_age = st.number_input("Age", value=u_age)
                new_edu = st.selectbox("Education Level", ["None", "High School", "Under Graduate", "Graduate", "Post Graduate"], 
                                       index=["None", "High School", "Under Graduate", "Graduate", "Post Graduate"].index(u_edu) if u_edu in ["None", "High School", "Under Graduate", "Graduate", "Post Graduate"] else 0)
                new_income = st.number_input("Annual Family Income (Rs.)", value=u_income)
                new_state = st.text_input("State", value=u_state)
                new_cat = st.selectbox("Category", ["General", "OBC", "SC", "ST"], index=["General", "OBC", "SC", "ST"].index(u_cat) if u_cat in ["General", "OBC", "SC", "ST"] else 0)
                
                if st.form_submit_button(t["save"]):
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE users SET age=?, education=?, income=?, state=?, category=? WHERE username=?
                    """, (new_age, new_edu, new_income, new_state, new_cat, st.session_state["username"]))
                    conn.commit()
                    conn.close()
                    st.success("Profile updated!")
                    st.rerun()

        edu_rank = {"None": 0, "High School": 1, "Under Graduate": 2, "Graduate": 3, "Post Graduate": 4}
        user_rank = edu_rank.get(u_edu, 0)

        conn = get_connection()
        schemes_df = pd.read_sql("SELECT * FROM schemes", conn)
        conn.close()

        matched_schemes = []
        for _, row in schemes_df.iterrows():
            req_rank = edu_rank.get(row["education_req"], 0)
            if (row["min_age"] <= u_age <= row["max_age"]) and (u_income <= row["max_income"]) and (user_rank >= req_rank):
                matched_schemes.append(row)

        if matched_schemes:
            pdf_bytes = generate_pdf_kit(st.session_state["full_name"], matched_schemes)
            st.download_button(
                label=t["download"],
                data=pdf_bytes,
                file_name=f"Scheme_Application_Kit_{st.session_state['username']}.pdf",
                mime="application/pdf"
            )

            st.divider()

            for scheme in matched_schemes:
                with st.container(border=True):
                    st.markdown(f"### {scheme['title']}")
                    st.caption(f"**Ministry:** {scheme['ministry']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"#### {t['benefits']}")
                        st.info(scheme['benefits'])
                    with col2:
                        st.markdown(f"#### {t['checklist']}")
                        docs = scheme['documents'].split(",")
                        for d in docs:
                            st.checkbox(d.strip(), key=f"doc_{scheme['id']}_{d.strip()}")

                    st.markdown(f"#### {t['status']}")
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT status FROM user_applications WHERE username=? AND scheme_id=?", 
                                   (st.session_state["username"], scheme['id']))
                    status_record = cursor.fetchone()
                    conn.close()
                    
                    current_status = status_record[0] if status_record else "Discovered"
                    
                    status_options = ["Discovered", "Documents Collected", "Applied", "Under Review", "Approved"]
                    new_status = st.selectbox(
                        "Update your progress:", 
                        status_options, 
                        index=status_options.index(current_status),
                        key=f"status_select_{scheme['id']}"
                    )
                    
                    if new_status != current_status:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO user_applications (username, scheme_id, status, last_updated)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(username, scheme_id) DO UPDATE SET status=?, last_updated=?
                        """, (st.session_state["username"], scheme['id'], new_status, datetime.datetime.now().strftime("%Y-%m-%d"),
                              new_status, datetime.datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        conn.close()
                        st.success(f"Status updated to: {new_status}")
        else:
            st.warning("No schemes found matching your current profile. Try adjusting your income or education criteria.")