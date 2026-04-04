from flask import Flask, request, jsonify
import joblib
import numpy as np
import sqlite3
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load model and scaler
model = joblib.load("best_model.pkl")
scaler = joblib.load("scaler.pkl")

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
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        specialization TEXT,
        location TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        message TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS doctor_login (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT
    )
    """)
    
    conn.commit()
    conn.close()
init_db()
@app.route("/")
def home():
    return "Backend is running!"

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json

        # Convert input into correct order
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

        # Connect to DB
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        if prediction == 1:
            result = "High Risk"

            # Fetch cardiologists
            cursor.execute(
                "SELECT * FROM doctors WHERE specialization=?",
                ("Cardiologist",)
            )

            doctors = cursor.fetchall()

            doctor_list = []
            for doc in doctors:
                doctor_list.append({
                    "name": doc[1],
                    "specialization": doc[2],
                    "location": doc[3]
                })

        else:
            result = "Low Risk"
            doctor_list = []

        conn.close()

        return jsonify({
            "prediction": result,
            "doctors": doctor_list
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        })
@app.route("/register", methods=["POST"])
def register():
    try:
        data = request.json
        print("DATA RECEIVED:", data)  # 👈 ADD THIS

        name = data["name"]
        email = data["email"]
        password = data["password"]
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO patients (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "User registered successfully"})
    
    except Exception as e:
        print("ERROR:", e)  # 👈 ADD THIS
        return jsonify({"error": str(e)})
@app.route("/login", methods=["POST"])
def login():
    try:
        data = request.json
        print("LOGIN DATA:", data)

        email = data["email"]
        password = data["password"]
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM patients WHERE email=? AND password=?",
            (email, password)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return jsonify({"message": "Login successful"})
        else:
            return jsonify({"error": "Invalid credentials"})
    
    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)})
@app.route("/add-doctor", methods=["POST"])
def add_doctor():
    try:
        data = request.json
        
        name = data["name"]
        specialization = data["specialization"]
        location = data["location"]
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO doctors (name, specialization, location) VALUES (?, ?, ?)",
            (name, specialization, location)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Doctor added successfully"})
    
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/search-doctor", methods=["GET"])
def search_doctor():
    try:
        location = request.args.get("location")
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM doctors WHERE location=?",
            (location,)
        )
        
        doctors = cursor.fetchall()
        conn.close()
        
        result = []
        for doc in doctors:
            result.append({
                "id": doc[0],
                "name": doc[1],
                "specialization": doc[2],
                "location": doc[3]
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/add-feedback", methods=["POST"])
def add_feedback():
    try:
        data = request.json
        
        name = data["name"]
        message = data["message"]
        
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO feedback (name, message) VALUES (?, ?)",
            (name, message)
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Feedback submitted"})
    
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/view-feedback", methods=["GET"])
def view_feedback():
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM feedback")
        data = cursor.fetchall()
        
        conn.close()
        
        result = []
        for row in data:
            result.append({
                "id": row[0],
                "name": row[1],
                "message": row[2]
            })
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)})
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.json
    
    if data["username"] == "admin" and data["password"] == "admin123":
        return jsonify({"message": "Admin login successful"})
    else:
        return jsonify({"error": "Invalid credentials"})
@app.route("/view-doctors", methods=["GET"])
def view_doctors():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()
    
    conn.close()
    
    result = []
    for doc in doctors:
        result.append({
            "id": doc[0],
            "name": doc[1],
            "specialization": doc[2],
            "location": doc[3]
        })
    
    return jsonify(result)
@app.route("/view-patients", methods=["GET"])
def view_patients():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM patients")
    patients = cursor.fetchall()
    
    conn.close()
    
    result = []
    for p in patients:
        result.append({
            "id": p[0],
            "name": p[1],
            "email": p[2]
        })
    
    return jsonify(result)
@app.route("/doctor-login", methods=["POST"])
def doctor_login():
    data = request.json
    
    email = data["email"]
    password = data["password"]
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM doctor_login WHERE email=? AND password=?",
        (email, password)
    )
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({"message": "Doctor login successful"})
    else:
        return jsonify({"error": "Invalid credentials"})
@app.route("/notifications", methods=["GET"])
def notifications():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Count patients
    cursor.execute("SELECT COUNT(*) FROM patients")
    patient_count = cursor.fetchone()[0]
    
    # Count feedback
    cursor.execute("SELECT COUNT(*) FROM feedback")
    feedback_count = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        "total_patients": patient_count,
        "total_feedback": feedback_count
    })
@app.route("/add-doctor-login", methods=["POST"])
def add_doctor_login():
    data = request.json
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO doctor_login (email, password) VALUES (?, ?)",
        (data["email"], data["password"])
    )
    
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Doctor login created"})

if __name__ == "__main__":
    app.run(debug=True)