let editingDoctorId = null;

function adminFetchJson(path, options = {}) {
  return fetch(path, options).then((res) => res.json());
}

function ensureAdminSession() {
  if (typeof window.requireRoleSession === "function") {
    return window.requireRoleSession("admin");
  }

  return true;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function isAdminEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function renderBarChart(containerId, labels, values, options = {}) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }

  if (!labels.length || !values.length) {
    container.innerHTML = '<div class="flex h-full items-center justify-center rounded-3xl border border-dashed border-slate-200 text-sm font-semibold text-slate-400">No chart data available.</div>';
    return;
  }

  const maxValue = Math.max(...values, 1);
  const barColor = options.barColor || "from-blue-500 to-cyan-400";
  const valueColor = options.valueColor || "text-slate-900";

  container.innerHTML = `
    <div class="flex h-full items-end gap-3 rounded-[1.5rem] bg-slate-50 p-5">
      ${labels.map((label, index) => {
        const value = values[index] ?? 0;
        const height = Math.max((value / maxValue) * 100, value > 0 ? 12 : 4);
        return `
          <div class="flex min-w-0 flex-1 flex-col items-center justify-end gap-3">
            <span class="text-xs font-bold ${valueColor}">${value}</span>
            <div class="flex h-52 w-full items-end">
              <div class="w-full rounded-t-2xl bg-gradient-to-t ${barColor} shadow-lg" style="height:${height}%"></div>
            </div>
            <span class="text-center text-xs font-semibold text-slate-500">${escapeHtml(label)}</span>
          </div>
        `;
      }).join("")}
    </div>
  `;
}

function renderGroupedBarChart(containerId, labels, seriesA, seriesB) {
  const container = document.getElementById(containerId);
  if (!container) {
    return;
  }

  if (!labels.length) {
    container.innerHTML = '<div class="flex h-full items-center justify-center rounded-3xl border border-dashed border-slate-200 text-sm font-semibold text-slate-400">No chart data available.</div>';
    return;
  }

  const maxValue = Math.max(...seriesA, ...seriesB, 1);

  container.innerHTML = `
    <div class="h-full rounded-[1.5rem] bg-slate-50 p-5">
      <div class="mb-5 flex flex-wrap gap-4 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
        <span class="inline-flex items-center gap-2"><span class="h-3 w-3 rounded-full bg-blue-500"></span>Patients</span>
        <span class="inline-flex items-center gap-2"><span class="h-3 w-3 rounded-full bg-cyan-500"></span>Doctors</span>
      </div>
      <div class="flex h-[13.5rem] items-end gap-3">
        ${labels.map((label, index) => {
          const patients = seriesA[index] ?? 0;
          const doctors = seriesB[index] ?? 0;
          const patientHeight = Math.max((patients / maxValue) * 100, patients > 0 ? 12 : 4);
          const doctorHeight = Math.max((doctors / maxValue) * 100, doctors > 0 ? 12 : 4);
          return `
            <div class="flex min-w-0 flex-1 flex-col items-center gap-3">
              <div class="flex h-52 w-full items-end justify-center gap-2">
                <div class="w-full max-w-[1.15rem] rounded-t-2xl bg-blue-500 shadow-sm" style="height:${patientHeight}%"></div>
                <div class="w-full max-w-[1.15rem] rounded-t-2xl bg-cyan-500 shadow-sm" style="height:${doctorHeight}%"></div>
              </div>
              <div class="text-center">
                <div class="text-[11px] font-bold text-slate-900">${patients + doctors}</div>
                <div class="text-xs font-semibold text-slate-500">${escapeHtml(label)}</div>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

function updateRiskVisuals(riskLevels) {
  const total = riskLevels.total || 0;
  const high = riskLevels.high || 0;
  const low = riskLevels.low || 0;
  const highPercent = total ? Math.round((high / total) * 100) : 0;
  const lowPercent = total ? Math.round((low / total) * 100) : 0;

  const ring = document.getElementById("admin-risk-ring");
  const highCount = document.getElementById("admin-high-risk-count");
  const lowCount = document.getElementById("admin-low-risk-count");
  const highBar = document.getElementById("admin-high-risk-bar");
  const lowBar = document.getElementById("admin-low-risk-bar");
  const riskRate = document.getElementById("admin-risk-rate");

  if (ring) {
    ring.style.background = `conic-gradient(#f43f5e 0 ${highPercent}%, #10b981 ${highPercent}% 100%)`;
    ring.innerHTML = `
      <div class="flex h-36 w-36 flex-col items-center justify-center rounded-full bg-white text-center shadow-inner">
        <span class="text-xs font-bold uppercase tracking-[0.2em] text-slate-500">High Risk</span>
        <span class="mt-2 text-4xl font-extrabold text-slate-900">${highPercent}%</span>
      </div>
    `;
  }

  if (highCount) highCount.textContent = `${high} (${highPercent}%)`;
  if (lowCount) lowCount.textContent = `${low} (${lowPercent}%)`;
  if (highBar) highBar.style.width = `${highPercent}%`;
  if (lowBar) lowBar.style.width = `${lowPercent}%`;
  if (riskRate) riskRate.textContent = `${highPercent}%`;
}

function updateAdminInsights(labels, predictionSeries, userGrowth, riskLevels) {
  const busiestDayEl = document.getElementById("admin-busiest-day");
  const growthDayEl = document.getElementById("admin-growth-day");
  const summaryEl = document.getElementById("admin-summary-line");
  const predictions7El = document.getElementById("admin-seven-day-predictions");
  const users7El = document.getElementById("admin-seven-day-users");

  const busiestPredictionValue = Math.max(...predictionSeries, 0);
  const busiestPredictionIndex = predictionSeries.indexOf(busiestPredictionValue);
  const totalNewUsers = userGrowth.total.reduce((sum, value) => sum + value, 0);
  const highestGrowthValue = Math.max(...userGrowth.total, 0);
  const highestGrowthIndex = userGrowth.total.indexOf(highestGrowthValue);
  const totalPredictions = predictionSeries.reduce((sum, value) => sum + value, 0);

  if (busiestDayEl) {
    busiestDayEl.textContent = busiestPredictionValue > 0 ? `${labels[busiestPredictionIndex]} (${busiestPredictionValue} predictions)` : "No recent prediction activity";
  }

  if (growthDayEl) {
    growthDayEl.textContent = highestGrowthValue > 0 ? `${labels[highestGrowthIndex]} (${highestGrowthValue} new users)` : "No recent user growth";
  }

  if (predictions7El) {
    predictions7El.textContent = totalPredictions;
  }

  if (users7El) {
    users7El.textContent = totalNewUsers;
  }

  if (summaryEl) {
    if (!riskLevels.total) {
      summaryEl.textContent = "There are no prediction records yet, so risk distribution and activity trends will appear as patients start using the system.";
    } else {
      summaryEl.textContent = `${riskLevels.high} high-risk and ${riskLevels.low} low-risk predictions are currently stored. The chart area above reflects the latest 7-day activity and new account creation pattern.`;
    }
  }
}

async function loadAdminAnalytics() {
  const predictionChart = document.getElementById("admin-prediction-chart");
  const userGrowthChart = document.getElementById("admin-user-growth-chart");
  const riskRing = document.getElementById("admin-risk-ring");

  if (!predictionChart && !userGrowthChart && !riskRing) {
    return;
  }

  try {
    const data = await adminFetchJson("/admin-analytics");
    renderBarChart("admin-prediction-chart", data.labels || [], data.prediction_series || [], {
      barColor: "from-blue-600 via-cyan-500 to-emerald-400"
    });
    renderGroupedBarChart("admin-user-growth-chart", data.labels || [], data.user_growth?.patients || [], data.user_growth?.doctors || []);
    updateRiskVisuals(data.risk_levels || { high: 0, low: 0, total: 0 });
    updateAdminInsights(data.labels || [], data.prediction_series || [], data.user_growth || { total: [] }, data.risk_levels || { high: 0, low: 0, total: 0 });
  } catch (error) {
    if (predictionChart) {
      predictionChart.innerHTML = '<div class="flex h-full items-center justify-center rounded-3xl border border-dashed border-rose-200 text-sm font-semibold text-rose-600">Unable to load prediction analytics.</div>';
    }
    if (userGrowthChart) {
      userGrowthChart.innerHTML = '<div class="flex h-full items-center justify-center rounded-3xl border border-dashed border-rose-200 text-sm font-semibold text-rose-600">Unable to load growth analytics.</div>';
    }
    const summaryEl = document.getElementById("admin-summary-line");
    if (summaryEl) {
      summaryEl.textContent = "Analytics are temporarily unavailable.";
    }
  }
}

function setDoctorFormMode(mode) {
  const title = document.getElementById("doctor-form-title");
  const button = document.getElementById("doctor-form-submit");
  const cancel = document.getElementById("doctor-form-cancel");

  if (mode === "edit") {
    if (title) title.textContent = "Edit Doctor";
    if (button) button.textContent = "Save Changes";
    if (cancel) cancel.classList.remove("hidden");
    return;
  }

  if (title) title.textContent = "Add Doctor";
  if (button) button.textContent = "Add Doctor";
  if (cancel) cancel.classList.add("hidden");
}

function resetDoctorForm() {
  const form = document.getElementById("add-doctor-form");
  if (form) {
    form.reset();
  }
  editingDoctorId = null;
  setDoctorFormMode("add");
}

function startDoctorEdit(doctor) {
  editingDoctorId = doctor.id;
  document.getElementById("doctor-name").value = doctor.name || "";
  document.getElementById("doctor-specialization").value = doctor.specialization || "";
  document.getElementById("doctor-location").value = doctor.location || "";
  document.getElementById("doctor-email").value = doctor.email || "";
  document.getElementById("doctor-password").value = "";
  setDoctorFormMode("edit");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function deleteDoctor(id, name) {
  if (!confirm(`Delete doctor account for ${name}?`)) {
    return;
  }

  try {
    const data = await adminFetchJson("/delete-doctor", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });

    if (data.message) {
      if (editingDoctorId === id) {
        resetDoctorForm();
      }
      loadDoctorsTable();
      loadAdminDashboard();
      loadAdminAnalytics();
      return;
    }

    alert(data.error || "Unable to delete doctor.");
  } catch (error) {
    alert("Unable to connect to the server.");
  }
}

async function deletePatient(id, name) {
  if (!confirm(`Delete patient account for ${name}? This will also remove that patient's prediction history.`)) {
    return;
  }

  try {
    const data = await adminFetchJson("/delete-patient", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id })
    });

    if (data.message) {
      loadPatientsTable();
      loadAdminDashboard();
      loadAdminAnalytics();
      return;
    }

    alert(data.error || "Unable to delete patient.");
  } catch (error) {
    alert("Unable to connect to the server.");
  }
}

async function loadAdminDashboard() {
  const patientsEl = document.getElementById("admin-total-patients");
  const doctorsEl = document.getElementById("admin-total-doctors");
  const predictionsEl = document.getElementById("admin-total-predictions");
  const feedbackEl = document.getElementById("admin-total-feedback");

  if (!patientsEl || !doctorsEl || !predictionsEl || !feedbackEl) {
    return;
  }

  try {
    const data = await adminFetchJson("/notifications");
    patientsEl.textContent = data.total_users ?? 0;
    doctorsEl.textContent = data.total_doctors ?? 0;
    predictionsEl.textContent = data.total_predictions ?? 0;
    feedbackEl.textContent = data.total_feedback ?? 0;
  } catch (error) {
    patientsEl.textContent = "-";
    doctorsEl.textContent = "-";
    predictionsEl.textContent = "-";
    feedbackEl.textContent = "-";
  }
}

async function loadDoctorsTable() {
  const tbody = document.getElementById("admin-doctors-body");
  const countEl = document.getElementById("admin-doctors-count");

  if (!tbody) {
    return;
  }

  try {
    const doctors = await adminFetchJson("/view-doctors");
    if (countEl) {
      countEl.textContent = doctors.length;
    }

    if (!doctors.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-sm text-slate-500">No doctors found.</td></tr>';
      return;
    }

    tbody.innerHTML = doctors.map((doctor) => `
      <tr class="border-t border-slate-200">
        <td class="px-6 py-4 text-sm font-semibold text-slate-900">${escapeHtml(doctor.name)}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(doctor.specialization)}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(doctor.location)}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(doctor.email)}</td>
        <td class="px-6 py-4 text-sm">
          <div class="flex gap-2">
            <button type="button" class="rounded-lg bg-slate-100 px-3 py-2 font-semibold text-slate-700 hover:bg-blue-50 hover:text-blue-700" data-edit-doctor='${JSON.stringify(doctor).replace(/'/g, "&#39;")}'>Edit</button>
            <button type="button" class="rounded-lg bg-rose-50 px-3 py-2 font-semibold text-rose-700 hover:bg-rose-100" data-delete-doctor-id="${doctor.id}" data-delete-doctor-name="${escapeHtml(doctor.name)}">Delete</button>
          </div>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-edit-doctor]").forEach((button) => {
      button.addEventListener("click", () => {
        const doctor = JSON.parse(button.getAttribute("data-edit-doctor").replace(/&#39;/g, "'"));
        startDoctorEdit(doctor);
      });
    });

    tbody.querySelectorAll("[data-delete-doctor-id]").forEach((button) => {
      button.addEventListener("click", () => {
        deleteDoctor(Number(button.getAttribute("data-delete-doctor-id")), button.getAttribute("data-delete-doctor-name"));
      });
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-sm text-rose-600">Unable to load doctors.</td></tr>';
  }
}

async function loadPatientsTable() {
  const tbody = document.getElementById("admin-patients-body");
  const countEl = document.getElementById("admin-patients-count");

  if (!tbody) {
    return;
  }

  try {
    const patients = await adminFetchJson("/view-patients");
    if (countEl) {
      countEl.textContent = patients.length;
    }

    if (!patients.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-sm text-slate-500">No patients found.</td></tr>';
      return;
    }

    tbody.innerHTML = patients.map((patient) => `
      <tr class="border-t border-slate-200">
        <td class="px-6 py-4 text-sm font-semibold text-slate-900">${escapeHtml(patient.name)}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(patient.email)}</td>
        <td class="px-6 py-4 text-sm">
          <button type="button" class="rounded-lg bg-rose-50 px-3 py-2 font-semibold text-rose-700 hover:bg-rose-100" data-delete-patient-id="${patient.id}" data-delete-patient-name="${escapeHtml(patient.name)}">Delete</button>
        </td>
      </tr>
    `).join("");

    tbody.querySelectorAll("[data-delete-patient-id]").forEach((button) => {
      button.addEventListener("click", () => {
        deletePatient(Number(button.getAttribute("data-delete-patient-id")), button.getAttribute("data-delete-patient-name"));
      });
    });
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-sm text-rose-600">Unable to load patients.</td></tr>';
  }
}

async function loadFeedbackTable() {
  const tbody = document.getElementById("admin-feedback-body");
  const countEl = document.getElementById("admin-feedback-count");

  if (!tbody) {
    return;
  }

  try {
    const feedback = await adminFetchJson("/view-feedback");
    if (countEl) {
      countEl.textContent = feedback.length;
    }

    if (!feedback.length) {
      tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-sm text-slate-500">No feedback found.</td></tr>';
      return;
    }

    tbody.innerHTML = feedback.map((item) => `
      <tr class="border-t border-slate-200">
        <td class="px-6 py-4 text-sm text-slate-500">${escapeHtml(item[0])}</td>
        <td class="px-6 py-4 text-sm font-semibold text-slate-900">${escapeHtml(item[1])}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeHtml(item[2])}</td>
      </tr>
    `).join("");
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-sm text-rose-600">Unable to load feedback.</td></tr>';
  }
}

async function saveDoctor(event) {
  event.preventDefault();

  const name = document.getElementById("doctor-name")?.value.trim() || "";
  const specialization = document.getElementById("doctor-specialization")?.value.trim() || "";
  const location = document.getElementById("doctor-location")?.value.trim() || "";
  const email = document.getElementById("doctor-email")?.value.trim() || "";
  const password = document.getElementById("doctor-password")?.value.trim() || "";

  if (!name || !specialization || !location || !email || !password) {
    alert("All doctor fields are required.");
    return;
  }

  if (name.length < 2 || name.length > 60) {
    alert("Doctor name must be between 2 and 60 characters.");
    return;
  }

  if (!isAdminEmail(email)) {
    alert("Enter a valid doctor email.");
    return;
  }

  if (password.length < 8 || password.length > 64) {
    alert("Doctor password must be between 8 and 64 characters.");
    return;
  }

  const payload = { name, specialization, location, email, password };
  const endpoint = editingDoctorId ? "/update-doctor" : "/add-doctor";
  if (editingDoctorId) {
    payload.id = editingDoctorId;
  }

  try {
    const data = await adminFetchJson(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (data.message) {
      alert(data.message);
      resetDoctorForm();
      loadDoctorsTable();
      loadAdminDashboard();
      loadAdminAnalytics();
      return;
    }

    alert(data.error || "Unable to save doctor.");
  } catch (error) {
    alert("Unable to connect to the server.");
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (!ensureAdminSession()) {
    return;
  }

  loadAdminDashboard();
  loadAdminAnalytics();
  loadDoctorsTable();
  loadPatientsTable();
  loadFeedbackTable();

  const addDoctorForm = document.getElementById("add-doctor-form");
  if (addDoctorForm) {
    addDoctorForm.addEventListener("submit", saveDoctor);
  }

  const cancelButton = document.getElementById("doctor-form-cancel");
  if (cancelButton) {
    cancelButton.addEventListener("click", resetDoctorForm);
  }
});
