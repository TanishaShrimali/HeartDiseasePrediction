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
