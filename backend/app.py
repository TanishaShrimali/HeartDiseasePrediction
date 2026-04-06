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

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DB_PATH = DATA_DIR / "database.db"
BEST_MODEL_PATH = MODELS_DIR / "best_model.pkl"
SCALER_PATH = MODELS_DIR / "scaler.pkl"

def get_db_connection():
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=MEMORY")
    conn.execute("PRAGMA synchronous=OFF")
    return conn

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
        password TEXT
    )
    """)

    # DOCTORS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        location TEXT,
        email TEXT,
        password TEXT
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

    cursor.execute("SELECT id FROM admins WHERE username=?", ("admin",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", hash_password_value("admin123"))
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
            "INSERT INTO patients (name, email, password) VALUES (?, ?, ?)",
            (
                data["name"].strip(),
                data["email"].strip().lower(),
                prepare_password_for_storage(data["password"].strip())
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

    # SAVE
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO predictions (email, result, date, details) VALUES (?, ?, ?, ?)",
        (
            data["email"],
            result,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            json.dumps(input_data)
        )
    )

    # DOCTOR SUGGESTION
    doctors = []
    if result == "High Risk":
        cursor.execute("SELECT name, location FROM doctors")
        rows = cursor.fetchall()

        for d in rows:
            doctors.append({
                "name": d[0],
                "location": d[1]
            })

    conn.commit()
    conn.close()

    return jsonify({
        "prediction": result,
        "doctors": doctors
    })

# HISTORY
@app.route("/history", methods=["POST"])
def history():
    email = request.json["email"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result, date, details FROM predictions WHERE email=? ORDER BY id DESC",
        (email,)
    )

    data = cursor.fetchall()
    conn.close()

    result = []
    for row in data:
        result.append({
            "result": row[0],
            "date": row[1],
            "details": json.loads(row[2]) if row[2] else []
        })

    return jsonify(result)

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
        "INSERT INTO doctors (name, specialization, location, email, password) VALUES (?, ?, ?, ?, ?)",
        (
            data["name"].strip(),
            data["specialization"].strip(),
            data["location"].strip(),
            data["email"].strip().lower(),
            prepare_password_for_storage(data["password"].strip())
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

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
