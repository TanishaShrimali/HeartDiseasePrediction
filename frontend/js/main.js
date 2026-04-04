// ================= CONFIG =================
const API_URL = "http://127.0.0.1:5000";

// ================= LOGIN =================
async function loginUser() {
    const email = document.getElementById("email")?.value;
    const password = document.getElementById("password")?.value;
    const role = document.getElementById("role")?.value;

    if (!email || !password || !role) {
        alert("Please fill all fields");
        return;
    }

    let endpoint = "";

    if (role === "patient") endpoint = "/login";
    else if (role === "admin") endpoint = "/admin-login";
    else if (role === "doctor") endpoint = "/doctor-login";

    try {
        const res = await fetch(API_URL + endpoint, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(
                role === "admin"
                    ? { username: email, password }
                    : { email, password }
            )
        });

        const data = await res.json();

        if (data.message) {
            localStorage.setItem("user", email);
            localStorage.setItem("role", role);

            if (role === "patient") window.location.href = "patient_dashboard.html";
            if (role === "admin") window.location.href = "admin_dashboard.html";
            if (role === "doctor") window.location.href = "doctor_dashboard.html";
        } else {
            alert(data.error || "Login failed");
        }

    } catch (err) {
        alert("Server error");
    }
}

// ================= REGISTER =================
async function registerUser() {
    const name = document.getElementById("name")?.value;
    const email = document.getElementById("email")?.value;
    const password = document.getElementById("password")?.value;

    if (!name || !email || !password) {
        alert("Fill all fields");
        return;
    }

    try {
        const res = await fetch(API_URL + "/register", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ name, email, password })
        });

        const data = await res.json();

        if (data.message) {
            alert("Registered successfully");
            window.location.href = "login.html";
        } else {
            alert(data.error);
        }

    } catch (err) {
        alert("Server error");
    }
}

// ================= PREDICT =================
async function predict() {
    const data = {
        age: Number(document.getElementById("age")?.value),
        sex: Number(document.getElementById("sex")?.value),
        chest_pain_type: Number(document.getElementById("cp")?.value),
        resting_bp_s: Number(document.getElementById("trestbps")?.value),
        cholesterol: Number(document.getElementById("chol")?.value),
        fasting_blood_sugar: Number(document.getElementById("fbs")?.value),
        resting_ecg: Number(document.getElementById("restecg")?.value),
        max_heart_rate: Number(document.getElementById("thalach")?.value),
        exercise_angina: Number(document.getElementById("exang")?.value),
        oldpeak: Number(document.getElementById("oldpeak")?.value),
        st_slope: Number(document.getElementById("slope")?.value)
    };

    if (!data.age) {
        alert("Please fill required fields");
        return;
    }

    try {
        const res = await fetch(API_URL + "/predict", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(data)
        });

        const result = await res.json();

        document.getElementById("result").innerText =
            "Result: " + result.prediction;

        const doctorDiv = document.getElementById("doctors");

        if (doctorDiv) {
            if (result.doctors.length > 0) {
                doctorDiv.innerHTML = result.doctors.map(d =>
                    `<div class="p-3 bg-white rounded shadow mb-2">
                        <b>${d.name}</b><br>
                        ${d.specialization}<br>
                        ${d.location}
                    </div>`
                ).join("");
            } else {
                doctorDiv.innerHTML = "No doctor needed";
            }
        }

        // Save history locally (optional)
        let logs = JSON.parse(localStorage.getItem("searchLogs")) || [];
        logs.push({
            date: new Date().toLocaleString(),
            result: result.prediction
        });
        localStorage.setItem("searchLogs", JSON.stringify(logs));

    } catch (err) {
        alert("Prediction failed");
    }
}

// ================= FEEDBACK =================
async function submitFeedback() {
    const name = document.getElementById("fbName")?.value;
    const message = document.getElementById("fbMessage")?.value;

    if (!name || !message) {
        alert("Fill all fields");
        return;
    }

    try {
        const res = await fetch(API_URL + "/add-feedback", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ name, message })
        });

        const data = await res.json();

        if (data.message) {
            alert("Feedback submitted");
            document.getElementById("fbName").value = "";
            document.getElementById("fbMessage").value = "";
        }

    } catch (err) {
        alert("Error submitting feedback");
    }
}

// ================= ADMIN =================

// Load Feedback
async function loadFeedback() {
    try {
        const res = await fetch(API_URL + "/view-feedback");
        const data = await res.json();

        const table = document.getElementById("feedbackTable");

        if (table) {
            table.innerHTML = data.map(f =>
                `<tr class="border-b">
                    <td class="p-2">${f.name}</td>
                    <td class="p-2">${f.message}</td>
                </tr>`
            ).join("");
        }
    } catch (err) {
        console.log(err);
    }
}

// Load Patients
async function loadPatients() {
    try {
        const res = await fetch(API_URL + "/view-patients");
        const data = await res.json();
        console.log("Patients:", data);
    } catch (err) {
        console.log(err);
    }
}

// Load Doctors
async function loadDoctors() {
    try {
        const res = await fetch(API_URL + "/view-doctors");
        const data = await res.json();
        console.log("Doctors:", data);
    } catch (err) {
        console.log(err);
    }
}

// Notifications
async function loadNotifications() {
    try {
        const res = await fetch(API_URL + "/notifications");
        const data = await res.json();

        if (document.getElementById("totalPatients")) {
            document.getElementById("totalPatients").innerText = data.total_patients;
        }

        if (document.getElementById("totalFeedback")) {
            document.getElementById("totalFeedback").innerText = data.total_feedback;
        }
    } catch (err) {
        console.log(err);
    }
}

// ================= UI HELPERS =================

// Section Switch (Patient Dashboard)
function showSection(sectionId) {
    const sections = ["predict", "profile", "history", "feedback"];

    sections.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
    });

    const active = document.getElementById(sectionId);
    if (active) active.style.display = "block";
}

// Logout
function logout() {
    localStorage.clear();
    window.location.href = "login.html";
}

// Load Profile + History
window.onload = function () {

    // Profile
    if (document.getElementById("profileEmail")) {
        document.getElementById("profileEmail").innerText =
            localStorage.getItem("user") || "user@mail.com";
    }

    // History
    const historyList = document.getElementById("historyList");
    if (historyList) {
        let logs = JSON.parse(localStorage.getItem("searchLogs")) || [];

        historyList.innerHTML = logs.map(log =>
            `<div class="p-3 bg-white rounded shadow">
                ${log.date} → ${log.result}
            </div>`
        ).join("");
    }

    // Admin auto-load
    loadFeedback();
    loadNotifications();
};