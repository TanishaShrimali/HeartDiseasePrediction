from flask import Flask, request, jsonify, render_template
import sqlite3
import joblib
import numpy as np
from flask_cors import CORS
from datetime import datetime
import json
import re
import bcrypt
from pathlib import Path
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from io import BytesIO
from flask import send_file
from fpdf import FPDF

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "database.db"
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"
DEFAULT_ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "").strip()
DEFAULT_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()

PREDICTION_FIELD_LABELS = {
    "age": "Age",
    "sex": "Sex",
    "chest_pain_type": "Chest Pain Type",
    "resting_bp_s": "Resting Blood Pressure",
    "cholesterol": "Cholesterol",
    "fasting_blood_sugar": "Fasting Blood Sugar",
    "resting_ecg": "Resting ECG",
    "max_heart_rate": "Max Heart Rate",
    "exercise_angina": "Exercise Angina",
    "oldpeak": "Oldpeak",
    "st_slope": "ST Slope"
}

def get_db_connection():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=OFF")
    return conn

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def is_production():
    return os.environ.get("FLASK_ENV", "").strip().lower() == "production"

def get_email_settings():
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ.get("SMTP_USERNAME", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    from_email = os.environ.get("SMTP_FROM_EMAIL", username).strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "true").strip().lower() != "false"

    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "from_email": from_email,
        "use_tls": use_tls
    }

# ================= LOAD MODEL =================
model = joblib.load(BEST_MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

# ================= DATABASE =================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # PATIENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(patients)")
    patient_columns = [row[1] for row in cursor.fetchall()]
    if "created_at" not in patient_columns:
        cursor.execute("ALTER TABLE patients ADD COLUMN created_at TEXT")
    cursor.execute("UPDATE patients SET created_at=? WHERE created_at IS NULL OR created_at=''", (current_timestamp(),))

    # DOCTORS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        location TEXT,
        email TEXT,
        password TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(doctors)")
    doctor_columns = [row[1] for row in cursor.fetchall()]
    if "specialization" not in doctor_columns:
        cursor.execute("ALTER TABLE doctors ADD COLUMN specialization TEXT")
    if "location" not in doctor_columns:
        cursor.execute("ALTER TABLE doctors ADD COLUMN location TEXT")
    if "email" not in doctor_columns:
        cursor.execute("ALTER TABLE doctors ADD COLUMN email TEXT")
    if "password" not in doctor_columns:
        cursor.execute("ALTER TABLE doctors ADD COLUMN password TEXT")
    if "created_at" not in doctor_columns:
        cursor.execute("ALTER TABLE doctors ADD COLUMN created_at TEXT")
    cursor.execute("UPDATE doctors SET created_at=? WHERE created_at IS NULL OR created_at=''", (current_timestamp(),))

    # PREDICTIONS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        result TEXT,
        date TEXT,
        details TEXT
    )
    """)

    # FEEDBACK
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("PRAGMA table_info(predictions)")
    prediction_columns = [row[1] for row in cursor.fetchall()]
    if "details" not in prediction_columns:
        cursor.execute("ALTER TABLE predictions ADD COLUMN details TEXT")

    cursor.execute("PRAGMA table_info(feedback)")
    feedback_columns = [row[1] for row in cursor.fetchall()]
    if "email" not in feedback_columns:
        cursor.execute("ALTER TABLE feedback ADD COLUMN email TEXT")

    if DEFAULT_ADMIN_USERNAME and DEFAULT_ADMIN_PASSWORD:
        cursor.execute("SELECT id FROM admins WHERE username=?", (DEFAULT_ADMIN_USERNAME,))
        admin_exists = cursor.fetchone()
    else:
        admin_exists = True

    if not admin_exists:
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            (DEFAULT_ADMIN_USERNAME, hash_password_value(DEFAULT_ADMIN_PASSWORD))
        )

    migrate_passwords_to_bcrypt(cursor, "patients", "id")
    migrate_passwords_to_bcrypt(cursor, "doctors", "id")
    migrate_passwords_to_bcrypt(cursor, "admins", "id")

    conn.commit()
    conn.close()

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
NAME_PATTERN = re.compile(r"^[A-Za-z ]+$")

def is_bcrypt_hash(value):
    return isinstance(value, str) and value.startswith(("$2a$", "$2b$", "$2y$"))

def hash_password_value(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def prepare_password_for_storage(password):
    if is_bcrypt_hash(password):
        return password
    return hash_password_value(password)

def verify_password_value(plain_password, stored_password):
    if not isinstance(plain_password, str) or not isinstance(stored_password, str):
        return False

    if is_bcrypt_hash(stored_password):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                stored_password.encode("utf-8")
            )
        except ValueError:
            return False

    return plain_password == stored_password

def migrate_passwords_to_bcrypt(cursor, table_name, identifier_column):
    cursor.execute(f"SELECT {identifier_column}, password FROM {table_name}")
    rows = cursor.fetchall()

    for row_id, password in rows:
        if isinstance(password, str) and password and not is_bcrypt_hash(password):
            cursor.execute(
                f"UPDATE {table_name} SET password=? WHERE {identifier_column}=?",
                (hash_password_value(password), row_id)
            )

def validate_account_input(name=None, email=None, password=None):
    if name is not None:
        if not isinstance(name, str) or not name.strip():
            return "Name is required"
        cleaned_name = name.strip()
        if len(cleaned_name) < 2 or len(cleaned_name) > 60:
            return "Name must be between 2 and 60 characters"
        if not NAME_PATTERN.match(cleaned_name):
            return "Name should contain only letters and spaces"

    if email is not None:
        if not isinstance(email, str) or not EMAIL_PATTERN.match(email.strip()):
            return "Invalid email format"

    if password is not None:
        if not isinstance(password, str) or len(password.strip()) < 8 or len(password.strip()) > 64:
            return "Password must be between 8 and 64 characters"

    return None

def format_prediction_details(data):
    return [
        {"label": PREDICTION_FIELD_LABELS[key], "value": data.get(key)}
        for key in PREDICTION_FIELD_LABELS
        if key in data
    ]

def format_prediction_details_from_values(values):
    detail_rows = []
    labels = list(PREDICTION_FIELD_LABELS.values())
    for index, label in enumerate(labels):
        value = values[index] if index < len(values) else ""
        detail_rows.append({"label": label, "value": value})
    return detail_rows

def get_prediction_precautions(result):
    if result == "High Risk":
        return [
            "Schedule a doctor consultation as early as possible.",
            "Seek urgent medical help if there is chest pain, fainting, or breathing difficulty.",
            "Avoid smoking, heavy alcohol use, and high-fat meals until reviewed by a doctor.",
            "Monitor blood pressure, sugar, and cholesterol regularly.",
            "Continue only doctor-approved exercise and medication plans."
        ]

    return [
        "Maintain regular exercise, balanced food choices, and good sleep.",
        "Keep routine checks for blood pressure, cholesterol, and blood sugar.",
        "Avoid smoking and limit alcohol intake.",
        "Repeat screening if symptoms appear or risk factors increase."
    ]

def build_prediction_email_html(patient_name, email, result, prediction_date, details, precautions, doctors):
    doctor_block = ""
    if doctors:
        doctor_rows = "".join(
            f"<li><strong>{doctor['name']}</strong> - {doctor['specialization']}, {doctor['location']}"
            + (f" ({doctor['email']})" if doctor.get("email") else "")
            + "</li>"
            for doctor in doctors
        )
        doctor_block = f"""
        <h3 style="margin-top:24px;color:#0f172a;">Recommended Doctors</h3>
        <ul style="padding-left:18px;color:#334155;line-height:1.7;">{doctor_rows}</ul>
        """

    detail_rows = "".join(
        f"<tr><td style='padding:10px 12px;border-bottom:1px solid #e2e8f0;color:#334155;'>{item['label']}</td>"
        f"<td style='padding:10px 12px;border-bottom:1px solid #e2e8f0;font-weight:700;color:#0f172a;'>{item['value']}</td></tr>"
        for item in details
    )
    precaution_rows = "".join(
        f"<li style='margin-bottom:8px;'>{item}</li>"
        for item in precautions
    )

    status_color = "#f43f5e" if result == "High Risk" else "#10b981"
    status_note = "Doctor consultation is recommended." if result == "High Risk" else "Continue preventive care and healthy habits."

    return f"""
    <div style="font-family:Arial,sans-serif;background:#f8fafc;padding:24px;color:#0f172a;">
      <div style="max-width:760px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:24px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#0f172a,#0f4c81,#0891b2);padding:28px 32px;color:white;">
          <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.2em;text-transform:uppercase;color:#bfdbfe;">CardioGuard Prediction Report</p>
          <h1 style="margin:12px 0 0;font-size:30px;line-height:1.2;">Your Heart Risk Result</h1>
          <p style="margin:10px 0 0;font-size:15px;color:#dbeafe;">Generated on {prediction_date} for {email}</p>
        </div>
        <div style="padding:32px;">
          <p style="margin:0 0 16px;font-size:16px;color:#334155;">Hello {patient_name or 'Patient'},</p>
          <div style="border-radius:20px;padding:20px;background:#f8fafc;border:1px solid #e2e8f0;">
            <p style="margin:0;font-size:12px;font-weight:700;letter-spacing:0.18em;text-transform:uppercase;color:#64748b;">Prediction Status</p>
            <p style="margin:12px 0 4px;font-size:34px;font-weight:800;color:{status_color};">{result}</p>
            <p style="margin:0;color:#475569;">{status_note}</p>
          </div>

          <h3 style="margin-top:28px;color:#0f172a;">Submitted Details</h3>
          <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
            <tbody>{detail_rows}</tbody>
          </table>

          <h3 style="margin-top:24px;color:#0f172a;">Suggested Precautions</h3>
          <ul style="padding-left:18px;color:#334155;line-height:1.7;">{precaution_rows}</ul>

          {doctor_block}

          <div style="margin-top:28px;padding:18px;border-radius:18px;background:#eff6ff;border:1px solid #bfdbfe;">
            <p style="margin:0 0 8px;font-weight:700;color:#1d4ed8;">Important Note</p>
            <p style="margin:0;color:#1e3a8a;line-height:1.6;">
              This report is generated from the selected machine learning model and supports screening only. It does not replace professional diagnosis or emergency care.
            </p>
          </div>
        </div>
      </div>
    </div>
    """

def send_prediction_report_email(recipient_email, patient_name, result, prediction_date, details, precautions, doctors):
    settings = get_email_settings()
    if not settings["host"] or not settings["from_email"]:
        return False, "Email settings are not configured."

    subject = f"CardioGuard Prediction Report - {result}"
    html_body = build_prediction_email_html(
        patient_name=patient_name,
        email=recipient_email,
        result=result,
        prediction_date=prediction_date,
        details=details,
        precautions=precautions,
        doctors=doctors
    )

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings["from_email"]
    message["To"] = recipient_email
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings["host"], settings["port"], timeout=20) as server:
            if settings["use_tls"]:
                server.starttls()
            if settings["username"] and settings["password"]:
                server.login(settings["username"], settings["password"])
            server.sendmail(settings["from_email"], [recipient_email], message.as_string())
        return True, "Prediction report email sent successfully."
    except Exception as error:
        return False, f"Prediction saved, but email could not be sent: {error}"

def build_prediction_report_pdf(patient_name, email, result, prediction_date, details, precautions, doctors):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 10, "CardioGuard Prediction Report", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.ln(2)
    pdf.cell(0, 8, f"Patient: {patient_name}", ln=True)
    pdf.cell(0, 8, f"Email: {email}", ln=True)
    pdf.cell(0, 8, f"Generated: {prediction_date}", ln=True)

    pdf.ln(4)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Prediction Result: {result}", ln=True)

    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 8, "This report is generated from the selected machine learning model and is intended for screening support only. It does not replace professional diagnosis or emergency care.")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 10, "Submitted Details", ln=True)
    pdf.set_font("Arial", "", 11)
    for item in details:
        pdf.multi_cell(0, 8, f"{item['label']}: {item['value']}")

    pdf.ln(3)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 10, "Suggested Precautions", ln=True)
    pdf.set_font("Arial", "", 11)
    for index, precaution in enumerate(precautions, start=1):
        pdf.multi_cell(0, 8, f"{index}. {precaution}")

    if doctors:
        pdf.ln(3)
        pdf.set_font("Arial", "B", 13)
        pdf.cell(0, 10, "Recommended Doctors", ln=True)
        pdf.set_font("Arial", "", 11)
        for doctor in doctors:
            doctor_line = f"{doctor['name']} - {doctor.get('specialization', 'Doctor')}, {doctor['location']}"
            if doctor.get("email"):
                doctor_line += f" ({doctor['email']})"
            pdf.multi_cell(0, 8, doctor_line)

    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    return BytesIO(pdf_bytes)

init_db()

def validate_prediction_input(data):
    rules = {
        "age": (1, 120),
        "sex": (0, 1),
        "chest_pain_type": (0, 3),
        "resting_bp_s": (60, 250),
        "cholesterol": (80, 700),
        "fasting_blood_sugar": (0, 1),
        "resting_ecg": (0, 2),
        "max_heart_rate": (40, 250),
        "exercise_angina": (0, 1),
        "oldpeak": (0, 10),
        "st_slope": (0, 2),
    }

    for field, (minimum, maximum) in rules.items():
        if field not in data:
            return f"{field} is required"
        try:
            value = float(data[field])
        except (TypeError, ValueError):
            return f"{field} must be a number"
        if value < minimum or value > maximum:
            return f"{field} must be between {minimum} and {maximum}"

    email_error = validate_account_input(email=data.get("email"))
    if email_error:
        return email_error

    return None

# ================= PAGE ROUTES =================
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/index.html")
def home_file():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/login.html")
def login_file():
    return render_template("login.html")

@app.route("/register.html")
def register_file():
    return render_template("register.html")

@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")

@app.route("/forgot_password.html")
def forgot_password_file():
    return render_template("forgot_password.html")

@app.route("/predict-page")
def predict_page():
    return render_template("predict.html")

@app.route("/patient-dashboard")
def patient_dashboard_page():
    return render_template("patient_dashboard.html")

@app.route("/patient_dashboard.html")
def patient_dashboard_file():
    return render_template("patient_dashboard.html")

@app.route("/patient-predict")
def patient_predict_page():
    return render_template("patient_predict.html")

@app.route("/patient_predict.html")
def patient_predict_file():
    return render_template("patient_predict.html")

@app.route("/patient-mydetail")
def patient_mydetail_page():
    return render_template("patient_mydetail.html")

@app.route("/patient_mydetail.html")
def patient_mydetail_file():
    return render_template("patient_mydetail.html")

@app.route("/patient-history")
def patient_history_page():
    return render_template("patient_history.html")

@app.route("/patient_history.html")
def patient_history_file():
    return render_template("patient_history.html")

@app.route("/patient-feedback")
def patient_feedback_page():
    return render_template("patient_feedback.html")

@app.route("/patient_feedback.html")
def patient_feedback_file():
    return render_template("patient_feedback.html")

@app.route("/doctor-dashboard")
def doctor_dashboard_page():
    return render_template("doctor_dashboard.html")

@app.route("/doctor_dashboard.html")
def doctor_dashboard_file():
    return render_template("doctor_dashboard.html")

@app.route("/doctor-patient-records")
def doctor_patient_records_page():
    return render_template("doctor_patientrecords.html")

@app.route("/doctor_patientrecords.html")
def doctor_patient_records_file():
    return render_template("doctor_patientrecords.html")

@app.route("/admin-dashboard")
def admin_dashboard_page():
    return render_template("admin_dashboard.html")

@app.route("/admin_dashboard.html")
def admin_dashboard_file():
    return render_template("admin_dashboard.html")

@app.route("/admin-manage-doctors")
def admin_manage_doctors_page():
    return render_template("admin_managedoctors.html")

@app.route("/admin_managedoctors.html")
def admin_manage_doctors_file():
    return render_template("admin_managedoctors.html")

@app.route("/admin-view-patients")
def admin_view_patients_page():
    return render_template("admin_viewpatients.html")

@app.route("/admin_viewpatients.html")
def admin_view_patients_file():
    return render_template("admin_viewpatients.html")

@app.route("/admin-view-feedback")
def admin_view_feedback_page():
    return render_template("admin_viewfeedbacks.html")

@app.route("/admin_viewfeedbacks.html")
def admin_view_feedback_file():
    return render_template("admin_viewfeedbacks.html")

# ================= PATIENT =================

# REGISTER
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    validation_error = validate_account_input(
        name=data.get("name"),
        email=data.get("email"),
        password=data.get("password")
    )
    if validation_error:
        return jsonify({"error": validation_error})

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO patients (name, email, password, created_at) VALUES (?, ?, ?, ?)",
            (
                data["name"].strip(),
                data["email"].strip().lower(),
                prepare_password_for_storage(data["password"].strip()),
                current_timestamp()
            )
        )
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"})

    conn.commit()
    conn.close()

    return jsonify({"message": "Registered successfully"})

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    validation_error = validate_account_input(
        email=data.get("email"),
        password=data.get("password")
    )
    if validation_error:
        return jsonify({"error": validation_error})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, password FROM patients WHERE email=?",
        (data["email"].strip().lower(),)
    )

    user = cursor.fetchone()
    conn.close()

    if user and verify_password_value(data["password"], user[1]):
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"})

# MY DETAILS
@app.route("/my-details", methods=["POST"])
def my_details():
    email = request.json["email"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name, email FROM patients WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"error": "Patient not found"}), 404

    return jsonify({
        "name": user[0],
        "email": user[1]
    })

@app.route("/update-patient-profile", methods=["POST"])
def update_patient_profile():
    data = request.json
    current_email = (data.get("current_email") or "").strip().lower()
    new_name = (data.get("name") or "").strip()
    new_email = (data.get("email") or "").strip().lower()
    new_password = (data.get("password") or "").strip()

    if not current_email:
        return jsonify({"error": "Current email is required"})

    validation_error = validate_account_input(name=new_name, email=new_email)
    if validation_error:
        return jsonify({"error": validation_error})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, password FROM patients WHERE email=?", (current_email,))
    existing_patient = cursor.fetchone()

    if not existing_patient:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    stored_password = existing_patient[1]
    password_to_store = stored_password

    if new_password:
        password_error = validate_account_input(password=new_password)
        if password_error:
            conn.close()
            return jsonify({"error": password_error})
        password_to_store = prepare_password_for_storage(new_password)

    try:
        cursor.execute(
            """
            UPDATE patients
            SET name=?, email=?, password=?
            WHERE email=?
            """,
            (new_name, new_email, password_to_store, current_email)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already registered"})

    conn.close()

    return jsonify({
        "message": "Profile updated successfully",
        "name": new_name,
        "email": new_email
    })

# ================= PREDICTION =================

@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    validation_error = validate_prediction_input(data)
    if validation_error:
        return jsonify({"error": validation_error})

    input_data = [
        data["age"], data["sex"], data["chest_pain_type"],
        data["resting_bp_s"], data["cholesterol"],
        data["fasting_blood_sugar"], data["resting_ecg"],
        data["max_heart_rate"], data["exercise_angina"],
        data["oldpeak"], data["st_slope"]
    ]

    input_scaled = scaler.transform([input_data])
    prediction = model.predict(input_scaled)[0]

    result = "High Risk" if prediction == 1 else "Low Risk"
    prediction_date = current_timestamp()
    detail_summary = format_prediction_details(data)
    precautions = get_prediction_precautions(result)

    # SAVE
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM patients WHERE email=?", (data["email"],))
    patient_row = cursor.fetchone()
    patient_name = patient_row[0] if patient_row else "Patient"

    cursor.execute(
        "INSERT INTO predictions (email, result, date, details) VALUES (?, ?, ?, ?)",
        (
            data["email"],
            result,
            prediction_date,
            json.dumps(input_data)
        )
    )

    # DOCTOR SUGGESTION
    doctors = []
    if result == "High Risk":
        cursor.execute("SELECT name, specialization, location, email FROM doctors")
        rows = cursor.fetchall()

        for d in rows:
            doctors.append({
                "name": d[0],
                "specialization": d[1],
                "location": d[2],
                "email": d[3]
            })

    conn.commit()
    conn.close()

    return jsonify({
        "prediction": result,
        "doctors": doctors,
        "email_ready": True,
        "email_message": "Prediction saved. Click 'Email Me' if you want this report sent to your email."
    })

# HISTORY
@app.route("/history", methods=["POST"])
def history():
    email = request.json["email"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result, date, details, id FROM predictions WHERE email=? ORDER BY id DESC",
        (email,)
    )

    data = cursor.fetchall()
    conn.close()

    result = []
    for row in data:
        result.append({
            "id": row[3] if len(row) > 3 else None,
            "result": row[0],
            "date": row[1],
            "details": json.loads(row[2]) if row[2] else []
        })

    return jsonify(result)

@app.route("/email-prediction-report", methods=["POST"])
def email_prediction_report():
    email = (request.json.get("email") or "").strip().lower()
    email_error = validate_account_input(email=email)
    if email_error:
        return jsonify({"error": email_error})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM patients WHERE email=?", (email,))
    patient_row = cursor.fetchone()
    if not patient_row:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    patient_name = patient_row[0]

    cursor.execute(
        "SELECT result, date, details FROM predictions WHERE email=? ORDER BY id DESC LIMIT 1",
        (email,)
    )
    prediction_row = cursor.fetchone()
    if not prediction_row:
        conn.close()
        return jsonify({"error": "No prediction report available to email"}), 404

    result = prediction_row[0]
    prediction_date = prediction_row[1]
    details = json.loads(prediction_row[2]) if prediction_row[2] else []
    labeled_details = format_prediction_details_from_values(details)
    precautions = get_prediction_precautions(result)

    doctors = []
    if result == "High Risk":
        cursor.execute("SELECT name, specialization, location, email FROM doctors")
        rows = cursor.fetchall()
        for row in rows:
            doctors.append({
                "name": row[0],
                "specialization": row[1],
                "location": row[2],
                "email": row[3]
            })

    conn.close()

    email_sent, email_message = send_prediction_report_email(
        recipient_email=email,
        patient_name=patient_name,
        result=result,
        prediction_date=prediction_date,
        details=labeled_details,
        precautions=precautions,
        doctors=doctors
    )

    return jsonify({
        "email_sent": email_sent,
        "email_message": email_message
    })

@app.route("/download-prediction-report", methods=["GET"])
def download_prediction_report():
    email = (request.args.get("email") or "").strip().lower()
    prediction_id = request.args.get("prediction_id")
    email_error = validate_account_input(email=email)
    if email_error:
        return jsonify({"error": email_error}), 400

    if not prediction_id or not str(prediction_id).isdigit():
        return jsonify({"error": "Prediction id is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM patients WHERE email=?", (email,))
    patient_row = cursor.fetchone()
    if not patient_row:
        conn.close()
        return jsonify({"error": "Patient not found"}), 404

    patient_name = patient_row[0]

    cursor.execute(
        "SELECT result, date, details FROM predictions WHERE id=? AND email=?",
        (int(prediction_id), email)
    )
    prediction_row = cursor.fetchone()
    if not prediction_row:
        conn.close()
        return jsonify({"error": "Prediction report not found"}), 404

    result = prediction_row[0]
    prediction_date = prediction_row[1]
    details = json.loads(prediction_row[2]) if prediction_row[2] else []
    labeled_details = format_prediction_details_from_values(details)
    precautions = get_prediction_precautions(result)

    doctors = []
    if result == "High Risk":
        cursor.execute("SELECT name, specialization, location, email FROM doctors")
        rows = cursor.fetchall()
        for row in rows:
            doctors.append({
                "name": row[0],
                "specialization": row[1],
                "location": row[2],
                "email": row[3]
            })

    conn.close()

    pdf_buffer = build_prediction_report_pdf(
        patient_name=patient_name,
        email=email,
        result=result,
        prediction_date=prediction_date,
        details=labeled_details,
        precautions=precautions,
        doctors=doctors
    )

    safe_stamp = prediction_date.replace(":", "-").replace(" ", "_")
    filename = f"cardioguard_report_{safe_stamp}.pdf"
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )

# ================= DOCTOR =================

# DOCTOR LOGIN
@app.route("/doctor-login", methods=["POST"])
def doctor_login():
    data = request.json
    validation_error = validate_account_input(
        email=data.get("email"),
        password=data.get("password")
    )
    if validation_error:
        return jsonify({"error": validation_error})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, password FROM doctors WHERE email=?",
        (data["email"].strip().lower(),)
    )

    user = cursor.fetchone()
    conn.close()

    if user and verify_password_value(data["password"], user[1]):
        return jsonify({"message": "Doctor login successful"})
    return jsonify({"error": "Invalid credentials"})

# SEARCH DOCTOR
@app.route("/search-doctor", methods=["POST"])
def search_doctor():
    keyword = request.json["keyword"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, specialization, location FROM doctors WHERE name LIKE ? OR location LIKE ? OR specialization LIKE ?",
        (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
    )

    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "name": row[0],
            "specialization": row[1],
            "location": row[2]
        })

    return jsonify(result)

# ================= FEEDBACK =================

@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json
    validation_error = validate_account_input(
        name=data.get("name"),
        email=data.get("email")
    )
    if validation_error:
        return jsonify({"error": validation_error})
    if not isinstance(data.get("message"), str) or len(data["message"].strip()) < 5 or len(data["message"].strip()) > 1000:
        return jsonify({"error": "Feedback message must be between 5 and 1000 characters"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO feedback (name, email, message) VALUES (?, ?, ?)",
        (data["name"], data.get("email", ""), data["message"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Feedback submitted"})

# ================= ADMIN =================

# ADMIN LOGIN
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.json

    username = data.get("username") or data.get("email")
    if not isinstance(username, str) or len(username.strip()) < 3:
        return jsonify({"error": "Username is required"})
    password_error = validate_account_input(password=data.get("password"))
    if password_error:
        return jsonify({"error": password_error})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password FROM admins WHERE username=?",
        (username.strip(),)
    )
    admin = cursor.fetchone()
    conn.close()

    if admin and verify_password_value(data["password"], admin[1]):
        return jsonify({"message": "Admin login successful"})
    return jsonify({"error": "Invalid credentials"})

# ADD DOCTOR
@app.route("/add-doctor", methods=["POST"])
def add_doctor():
    data = request.json
    validation_error = validate_account_input(
        name=data.get("name"),
        email=data.get("email"),
        password=data.get("password")
    )
    if validation_error:
        return jsonify({"error": validation_error})
    if not isinstance(data.get("specialization"), str) or not data["specialization"].strip():
        return jsonify({"error": "Specialization is required"})
    if not isinstance(data.get("location"), str) or not data["location"].strip():
        return jsonify({"error": "Location is required"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO doctors (name, specialization, location, email, password, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (
            data["name"].strip(),
            data["specialization"].strip(),
            data["location"].strip(),
            data["email"].strip().lower(),
            prepare_password_for_storage(data["password"].strip()),
            current_timestamp()
        )
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Doctor added"})

# UPDATE DOCTOR
@app.route("/update-doctor", methods=["POST"])
def update_doctor():
    data = request.json
    doctor_id = data.get("id")
    if not doctor_id:
        return jsonify({"error": "Doctor id is required"})

    validation_error = validate_account_input(
        name=data.get("name"),
        email=data.get("email"),
        password=data.get("password")
    )
    if validation_error:
        return jsonify({"error": validation_error})
    if not isinstance(data.get("specialization"), str) or not data["specialization"].strip():
        return jsonify({"error": "Specialization is required"})
    if not isinstance(data.get("location"), str) or not data["location"].strip():
        return jsonify({"error": "Location is required"})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE doctors
        SET name=?, specialization=?, location=?, email=?, password=?
        WHERE id=?
        """,
        (
            data["name"].strip(),
            data["specialization"].strip(),
            data["location"].strip(),
            data["email"].strip().lower(),
            prepare_password_for_storage(data["password"].strip()),
            doctor_id
        )
    )
    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if not updated:
        return jsonify({"error": "Doctor not found"})

    return jsonify({"message": "Doctor updated"})

# DELETE DOCTOR
@app.route("/delete-doctor", methods=["POST"])
def delete_doctor():
    data = request.json
    doctor_id = data.get("id")
    if not doctor_id:
        return jsonify({"error": "Doctor id is required"})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM doctors WHERE id=?", (doctor_id,))
    conn.commit()
    deleted = cursor.rowcount
    conn.close()

    if not deleted:
        return jsonify({"error": "Doctor not found"})

    return jsonify({"message": "Doctor deleted"})

# VIEW DOCTORS
@app.route("/view-doctors", methods=["GET"])
def view_doctors():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, specialization, location, email FROM doctors")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "specialization": row[2],
            "location": row[3],
            "email": row[4]
        })

    return jsonify(result)

# VIEW PATIENTS
@app.route("/view-patients", methods=["GET"])
def view_patients():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, email FROM patients")
    rows = cursor.fetchall()
    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "name": row[1],
            "email": row[2]
        })

    return jsonify(result)

# DELETE PATIENT
@app.route("/delete-patient", methods=["POST"])
def delete_patient():
    data = request.json
    patient_id = data.get("id")
    if not patient_id:
        return jsonify({"error": "Patient id is required"})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM patients WHERE id=?", (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        conn.close()
        return jsonify({"error": "Patient not found"})

    patient_email = patient[0]
    cursor.execute("DELETE FROM predictions WHERE email=?", (patient_email,))
    cursor.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    conn.commit()
    conn.close()

    return jsonify({"message": "Patient deleted"})

# VIEW FEEDBACK
@app.route("/view-feedback", methods=["GET"])
def view_feedback():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM feedback")
    rows = cursor.fetchall()
    conn.close()

    return jsonify(rows)

# FORGOT PASSWORD
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json
    role = (data.get("role") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if role not in {"patient", "doctor"}:
        return jsonify({"error": "Select patient or doctor"})

    validation_error = validate_account_input(email=email, password=password)
    if validation_error:
        return jsonify({"error": validation_error})

    table_name = "patients" if role == "patient" else "doctors"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE {table_name} SET password=? WHERE email=?",
        (prepare_password_for_storage(password), email)
    )
    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if not updated:
        return jsonify({"error": f"{role.title()} account not found"})

    return jsonify({"message": f"{role.title()} password updated successfully"})

# NOTIFICATIONS
@app.route("/notifications", methods=["GET"])
def notifications():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM patients")
    patients = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM doctors")
    doctors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions")
    predictions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM feedback")
    feedback_count = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_users": patients,
        "total_predictions": predictions,
        "total_doctors": doctors,
        "total_feedback": feedback_count
    })

@app.route("/admin-analytics", methods=["GET"])
def admin_analytics():
    conn = get_db_connection()
    cursor = conn.cursor()

    labels = []
    prediction_series = []
    patient_growth = []
    doctor_growth = []

    for offset in range(6, -1, -1):
        day = datetime.now().date().fromordinal(datetime.now().date().toordinal() - offset)
        day_key = day.strftime("%Y-%m-%d")
        labels.append(day.strftime("%d %b"))

        cursor.execute("SELECT COUNT(*) FROM predictions WHERE date(date)=?", (day_key,))
        prediction_series.append(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM patients WHERE date(created_at)=?", (day_key,))
        patient_growth.append(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM doctors WHERE date(created_at)=?", (day_key,))
        doctor_growth.append(cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE result='High Risk'")
    high_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions WHERE result='Low Risk'")
    low_risk = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM predictions")
    total_predictions = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "labels": labels,
        "prediction_series": prediction_series,
        "risk_levels": {
            "high": high_risk,
            "low": low_risk,
            "total": total_predictions
        },
        "user_growth": {
            "patients": patient_growth,
            "doctors": doctor_growth,
            "total": [patient_growth[index] + doctor_growth[index] for index in range(len(labels))]
        }
    })

# ================= RUN =================
if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=not is_production()
    )
