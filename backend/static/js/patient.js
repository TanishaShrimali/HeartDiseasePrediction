function patientFetchJson(path, options = {}) {
  return fetch(`http://127.0.0.1:5000${path}`, options).then((res) => res.json());
}

function getPatientEmail() {
  return localStorage.getItem("user") || "";
}

function setPatientEmail(email) {
  localStorage.setItem("user", email);
}

let latestPredictionAvailableForEmail = false;

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

    const editName = document.getElementById("edit-patient-name");
    const editEmail = document.getElementById("edit-patient-email");
    const editPassword = document.getElementById("edit-patient-password");
    const editConfirmPassword = document.getElementById("edit-patient-confirm-password");
    const profileStatus = document.getElementById("patient-profile-status");
    if (editName) editName.value = data.name;
    if (editEmail) editEmail.value = data.email;
    if (editPassword) editPassword.value = "";
    if (editConfirmPassword) editConfirmPassword.value = "";
    if (profileStatus) profileStatus.textContent = "Edit your details and save when ready.";

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

async function submitPatientProfileUpdate(event) {
  event.preventDefault();

  const currentEmail = getPatientEmail();
  const name = document.getElementById("edit-patient-name")?.value.trim() || "";
  const email = document.getElementById("edit-patient-email")?.value.trim().toLowerCase() || "";
  const password = document.getElementById("edit-patient-password")?.value.trim() || "";
  const confirmPassword = document.getElementById("edit-patient-confirm-password")?.value.trim() || "";
  const statusEl = document.getElementById("patient-profile-status");

  if (!name || !email) {
    alert("Name and email are required.");
    return;
  }

  if (name.length < 2 || name.length > 60 || !/^[A-Za-z ]+$/.test(name)) {
    alert("Name must contain only letters and spaces, and be between 2 and 60 characters.");
    return;
  }

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    alert("Enter a valid email address.");
    return;
  }

  if (password) {
    if (password.length < 8 || password.length > 64) {
      alert("Password must be between 8 and 64 characters.");
      return;
    }
    if (password !== confirmPassword) {
      alert("New password and confirm password must match.");
      return;
    }
  }

  if (statusEl) {
    statusEl.textContent = "Saving profile...";
  }

  try {
    const data = await patientFetchJson("/update-patient-profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_email: currentEmail, name, email, password })
    });

    if (data.error) {
      throw new Error(data.error);
    }

    setPatientEmail(data.email);
    if (statusEl) {
      statusEl.textContent = data.message || "Profile updated successfully.";
    }
    await loadPatientProfile();
    await loadPatientDashboard();
  } catch (error) {
    if (statusEl) {
      statusEl.textContent = error.message || "Unable to update profile.";
    }
    alert(error.message || "Unable to update profile.");
  }
}

function resetPatientProfileForm() {
  loadPatientProfile();
}

function downloadPatientPredictionReport(predictionId) {
  const email = getPatientEmail();
  if (!email || !predictionId) {
    return;
  }

  const url = `http://127.0.0.1:5000/download-prediction-report?email=${encodeURIComponent(email)}&prediction_id=${encodeURIComponent(predictionId)}`;
  window.open(url, "_blank");
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
      tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-sm text-slate-500">No prediction history found.</td></tr>';
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
          <td class="px-4 py-4">
            <button type="button" class="rounded-xl bg-blue-50 px-4 py-2 text-xs font-bold text-blue-700 hover:bg-blue-100" data-download-report-id="${escapePatientHtml(item.id)}">Download PDF</button>
          </td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll("[data-download-report-id]").forEach((button) => {
      button.addEventListener("click", () => {
        downloadPatientPredictionReport(button.getAttribute("data-download-report-id"));
      });
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-sm text-rose-600">Unable to load history.</td></tr>';
  }
}

async function submitPatientPrediction(event) {
  event.preventDefault();

  const email = getPatientEmail();
  const resultEl = document.getElementById("patient-predict-result");
  const doctorsEl = document.getElementById("patient-predict-doctors");
  const emailStatusEl = document.getElementById("patient-predict-email-status");
  const emailButton = document.getElementById("patient-email-report-button");
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
    latestPredictionAvailableForEmail = Boolean(data.email_ready);
    if (emailButton) {
      emailButton.classList.toggle("hidden", !latestPredictionAvailableForEmail);
      emailButton.disabled = false;
    }
    if (emailStatusEl) {
      emailStatusEl.textContent = data.email_message || "Prediction report status unavailable.";
    }

    if (data.doctors && data.doctors.length) {
      doctorsEl.innerHTML = data.doctors.map((doctor) => `
        <div class="rounded-2xl bg-white/10 p-4 text-sm text-blue-50">
          <div class="font-bold">${escapePatientHtml(doctor.name)}</div>
          <div class="mt-1 text-blue-100">${escapePatientHtml(doctor.specialization || "Doctor")} - ${escapePatientHtml(doctor.location)}</div>
          <div class="mt-1 text-blue-200">${escapePatientHtml(doctor.email || "Email not available")}</div>
        </div>
      `).join("");
    }
  } catch (error) {
    resultEl.textContent = "Unable to submit prediction.";
    latestPredictionAvailableForEmail = false;
    if (emailButton) {
      emailButton.classList.add("hidden");
      emailButton.disabled = false;
    }
    if (emailStatusEl) {
      emailStatusEl.textContent = "Email report not available because the prediction could not be completed.";
    }
  }
}

async function emailLatestPredictionReport() {
  const email = getPatientEmail();
  const emailStatusEl = document.getElementById("patient-predict-email-status");
  const emailButton = document.getElementById("patient-email-report-button");

  if (!email || !latestPredictionAvailableForEmail) {
    return;
  }

  if (emailStatusEl) {
    emailStatusEl.textContent = "Sending your prediction report...";
  }
  if (emailButton) {
    emailButton.disabled = true;
  }

  try {
    const data = await patientFetchJson("/email-prediction-report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });

    if (data.error) {
      throw new Error(data.error);
    }

    if (emailStatusEl) {
      emailStatusEl.textContent = data.email_message || "Prediction report email status unavailable.";
    }
  } catch (error) {
    if (emailStatusEl) {
      emailStatusEl.textContent = error.message || "Unable to send the email report.";
    }
  } finally {
    if (emailButton) {
      emailButton.disabled = false;
    }
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

  const profileForm = document.getElementById("patient-profile-form");
  if (profileForm) {
    profileForm.addEventListener("submit", submitPatientProfileUpdate);
  }

  const profileReset = document.getElementById("patient-profile-reset");
  if (profileReset) {
    profileReset.addEventListener("click", resetPatientProfileForm);
  }

  const emailReportButton = document.getElementById("patient-email-report-button");
  if (emailReportButton) {
    emailReportButton.addEventListener("click", emailLatestPredictionReport);
  }
});
