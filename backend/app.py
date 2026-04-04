from flask import Flask, request, jsonify, render_template
import joblib
import numpy as np
import sqlite3
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Load model
model = joblib.load("best_model.pkl")
scaler = joblib.load("scaler.pkl")

# DB INIT
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        result TEXT,
        date TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ROUTES
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/predict-page")
def predict_page():
    return render_template("predict.html")

# REGISTER
@app.route("/register", methods=["POST"])
def register():
    data = request.json

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO patients (name, email, password) VALUES (?, ?, ?)",
        (data["name"], data["email"], data["password"])
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "User registered successfully"})

# LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM patients WHERE email=? AND password=?",
        (data["email"], data["password"])
    )

    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"message": "Login successful"})
    else:
        return jsonify({"error": "Invalid credentials"})

# PREDICT
@app.route("/predict", methods=["POST"])
def predict():
    data = request.json

    input_data = [
        data["age"],
        data["sex"],
        data["chest_pain_type"],
        data["resting_bp_s"],
        data["cholesterol"],
        data["fasting_blood_sugar"],
        data["resting_ecg"],
        data["max_heart_rate"],
        data["exercise_angina"],
        data["oldpeak"],
        data["st_slope"]
    ]

    input_array = np.array([input_data])
    input_scaled = scaler.transform(input_array)

    prediction = model.predict(input_scaled)[0]

    result = "High Risk" if prediction == 1 else "Low Risk"

    # SAVE TO DB
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    email = data.get("email", "guest")

    cursor.execute(
        "INSERT INTO predictions (email, result, date) VALUES (?, ?, ?)",
        (email, result, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )

    conn.commit()
    conn.close()

    return jsonify({"prediction": result})

# HISTORY
@app.route("/history", methods=["POST"])
def history():
    data = request.json
    email = data["email"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT result, date FROM predictions WHERE email=? ORDER BY id DESC",
        (email,)
    )

    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        history.append({
            "result": row[0],
            "date": row[1]
        })

    return jsonify(history)

if __name__ == "__main__":
    app.run(debug=True)