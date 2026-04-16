function patientFetchJson(path, options = {}) {
  return fetch(path, options).then((res) => res.json());
}

function getPatientEmail() {
  return localStorage.getItem("user") || "";
}

function escapePatientHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function ensurePatientSession() {
  const protectedNode = document.querySelector("[data-patient-page='true']");
  if (!protectedNode) {
    return true;
  }

  if (typeof window.requireRoleSession === "function") {
    return window.requireRoleSession("patient");
  }

  const email = getPatientEmail();
  if (!email) {
    window.location.href = "login.html";
    return false;
  }

  return true;
}

function validatePatientPredictionPayload(payload) {
  const rules = {
    age: { min: 1, max: 120, label: "Age" },
    sex: { min: 0, max: 1, label: "Sex" },
    chest_pain_type: { min: 0, max: 3, label: "Chest pain type" },
    resting_bp_s: { min: 60, max: 250, label: "Resting blood pressure" },
    cholesterol: { min: 80, max: 700, label: "Cholesterol" },
    fasting_blood_sugar: { min: 0, max: 1, label: "Fasting blood sugar" },
    resting_ecg: { min: 0, max: 2, label: "Resting ECG" },
    max_heart_rate: { min: 40, max: 250, label: "Max heart rate" },
    exercise_angina: { min: 0, max: 1, label: "Exercise angina" },
    oldpeak: { min: 0, max: 10, label: "Oldpeak" },
    st_slope: { min: 0, max: 2, label: "ST slope" }
  };

  for (const [field, rule] of Object.entries(rules)) {
    const value = payload[field];
    if (Number.isNaN(value)) {
      return `${rule.label} is required.`;
    }
    if (value < rule.min || value > rule.max) {
      return `${rule.label} must be between ${rule.min} and ${rule.max}.`;
    }
  }

  return null;
}

async function loadPatientDashboard() {
  const emailEl = document.getElementById("patient-dashboard-email");
  const predictionsEl = document.getElementById("patient-dashboard-predictions");
  const latestEl = document.getElementById("patient-dashboard-latest");
  if (!emailEl && !predictionsEl && !latestEl) {
    return;
  }

  const email = getPatientEmail();
  if (!email) return;

  emailEl && (emailEl.textContent = email);

  try {
    const history = await patientFetchJson("/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    if (predictionsEl) predictionsEl.textContent = history.length;
    if (latestEl) latestEl.textContent = history.length ? history[0].result : "No predictions yet";
  } catch (error) {
    if (predictionsEl) predictionsEl.textContent = "-";
    if (latestEl) latestEl.textContent = "Unable to load";
  }
}

async function loadPatientProfile() {
  const nameEl = document.getElementById("patient-name");
  const emailEl = document.getElementById("patient-email");
  const recordEl = document.getElementById("patient-record-id");
  if (!nameEl && !emailEl && !recordEl) {
    return;
  }

  const email = getPatientEmail();
  if (!email) return;

  try {
    const data = await patientFetchJson("/my-details", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    if (data.error) {
      throw new Error(data.error);
    }

    if (nameEl) nameEl.textContent = data.name;
    if (emailEl) emailEl.textContent = data.email;
    if (recordEl) recordEl.textContent = `Patient Email: ${data.email}`;

    const feedbackName = document.getElementById("feedback-name");
    const feedbackEmail = document.getElementById("feedback-email");
    if (feedbackName) feedbackName.value = data.name;
    if (feedbackEmail) feedbackEmail.value = data.email;
  } catch (error) {
    if (nameEl) nameEl.textContent = "Unavailable";
    if (emailEl) emailEl.textContent = email;
    if (recordEl) recordEl.textContent = "Profile unavailable";
  }
}

async function loadPatientHistory() {
  const tbody = document.getElementById("patient-history-body");
  const countEl = document.getElementById("patient-history-count");
  if (!tbody) {
    return;
  }

  const email = getPatientEmail();
  if (!email) return;

  try {
    const history = await patientFetchJson("/history", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    if (countEl) {
      countEl.textContent = history.length;
    }

    if (!history.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="px-4 py-8 text-center text-sm text-slate-500">No prediction history found.</td></tr>';
      return;
    }

    tbody.innerHTML = history.map((item) => {
      const statusClass = item.result === "High Risk"
        ? 'bg-rose-100 text-rose-700'
        : 'bg-emerald-100 text-emerald-700';
      return `
        <tr>
          <td class="px-4 py-4 text-sm text-slate-700">${escapePatientHtml(item.date)}</td>
          <td class="px-4 py-4 text-sm font-semibold text-slate-900">${escapePatientHtml(item.result)}</td>
          <td class="px-4 py-4"><span class="rounded-full px-3 py-1 text-xs font-bold ${statusClass}">${escapePatientHtml(item.result)}</span></td>
        </tr>
      `;
    }).join("");
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="3" class="px-4 py-8 text-center text-sm text-rose-600">Unable to load history.</td></tr>';
  }
}

async function submitPatientPrediction(event) {
  event.preventDefault();

  const email = getPatientEmail();
  const resultEl = document.getElementById("patient-predict-result");
  const doctorsEl = document.getElementById("patient-predict-doctors");
  if (!email) {
    window.location.href = "login.html";
    return;
  }

  const payload = {
    email,
    age: Number(document.getElementById("predict-age").value),
    sex: Number(document.getElementById("predict-sex").value),
    chest_pain_type: Number(document.getElementById("predict-cp").value),
    resting_bp_s: Number(document.getElementById("predict-bp").value),
    cholesterol: Number(document.getElementById("predict-chol").value),
    fasting_blood_sugar: Number(document.getElementById("predict-fbs").value),
    resting_ecg: Number(document.getElementById("predict-ecg").value),
    max_heart_rate: Number(document.getElementById("predict-heart-rate").value),
    exercise_angina: Number(document.getElementById("predict-angina").value),
    oldpeak: Number(document.getElementById("predict-oldpeak").value),
    st_slope: Number(document.getElementById("predict-slope").value)
  };

  if (Object.values(payload).some((value) => Number.isNaN(value))) {
    alert("Please fill in all prediction fields.");
    return;
  }

  const validationError = validatePatientPredictionPayload(payload);
  if (validationError) {
    alert(validationError);
    return;
  }

  try {
    const data = await patientFetchJson("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (data.prediction === "High Risk") {
      resultEl.textContent = "High Risk - Doctor consultation recommended";
    } else {
      resultEl.textContent = data.prediction || "Prediction complete";
    }
    doctorsEl.innerHTML = "";

    if (data.doctors && data.doctors.length) {
      doctorsEl.innerHTML = data.doctors.map((doctor) => `
        <div class="rounded-2xl bg-white/10 p-4 text-sm text-blue-50">
          <div class="font-bold">${escapePatientHtml(doctor.name)}</div>
          <div class="mt-1 text-blue-100">${escapePatientHtml(doctor.location)}</div>
        </div>
      `).join("");
    }
  } catch (error) {
    resultEl.textContent = "Unable to submit prediction.";
  }
}

async function submitPatientFeedback(event) {
  event.preventDefault();

  const name = document.getElementById("feedback-name")?.value.trim() || "";
  const email = document.getElementById("feedback-email")?.value.trim() || getPatientEmail();
  const message = document.getElementById("feedback-message")?.value.trim() || "";

  if (!name || !message) {
    alert("Please complete the feedback form.");
    return;
  }

  if (name.length < 2 || name.length > 60 || !/^[A-Za-z ]+$/.test(name)) {
    alert("Name must contain only letters and spaces, and be between 2 and 60 characters.");
    return;
  }

  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    alert("Enter a valid email address.");
    return;
  }

  if (message.length < 5 || message.length > 1000) {
    alert("Feedback must be between 5 and 1000 characters.");
    return;
  }

  try {
    const data = await patientFetchJson("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, message })
    });

    alert(data.message || "Feedback submitted");
    document.getElementById("feedback-message").value = "";
  } catch (error) {
    alert("Unable to submit feedback.");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (!ensurePatientSession()) {
    return;
  }

  loadPatientDashboard();
  loadPatientProfile();
  loadPatientHistory();

  const predictForm = document.getElementById("patient-predict-form");
  if (predictForm) {
    predictForm.addEventListener("submit", submitPatientPrediction);
  }

  const feedbackForm = document.getElementById("patient-feedback-form");
  if (feedbackForm) {
    feedbackForm.addEventListener("submit", submitPatientFeedback);
  }
});
