function doctorFetchJson(path, options = {}) {
  return fetch(path, options).then((res) => res.json());
}

function ensureDoctorSession() {
  if (typeof window.requireRoleSession === "function") {
    return window.requireRoleSession("doctor");
  }

  return true;
}

function escapeDoctorHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function loadDoctorDashboard() {
  const patientCount = document.getElementById("doctor-total-patients");
  const predictionCount = document.getElementById("doctor-total-predictions");
  const feedbackCount = document.getElementById("doctor-total-feedback");
  const recentPatients = document.getElementById("doctor-recent-patients");

  if (!patientCount && !predictionCount && !feedbackCount && !recentPatients) {
    return;
  }

  try {
    const [notifications, patients] = await Promise.all([
      doctorFetchJson("/notifications"),
      doctorFetchJson("/view-patients")
    ]);

    if (patientCount) patientCount.textContent = notifications.total_users ?? 0;
    if (predictionCount) predictionCount.textContent = notifications.total_predictions ?? 0;
    if (feedbackCount) feedbackCount.textContent = notifications.total_feedback ?? 0;

    if (recentPatients) {
      if (!patients.length) {
        recentPatients.innerHTML = '<tr><td colspan="2" class="px-6 py-8 text-center text-sm text-slate-500">No patients available.</td></tr>';
      } else {
        recentPatients.innerHTML = patients.slice(0, 5).map((patient) => `
          <tr class="border-t border-slate-200">
            <td class="px-6 py-4 text-sm font-semibold text-slate-900">${escapeDoctorHtml(patient.name)}</td>
            <td class="px-6 py-4 text-sm text-slate-600">${escapeDoctorHtml(patient.email)}</td>
          </tr>
        `).join("");
      }
    }
  } catch (error) {
    if (patientCount) patientCount.textContent = "-";
    if (predictionCount) predictionCount.textContent = "-";
    if (feedbackCount) feedbackCount.textContent = "-";
    if (recentPatients) {
      recentPatients.innerHTML = '<tr><td colspan="2" class="px-6 py-8 text-center text-sm text-rose-600">Unable to load patient data.</td></tr>';
    }
  }
}

async function loadDoctorPatientRecords() {
  const tbody = document.getElementById("doctor-patient-records-body");
  const countEl = document.getElementById("doctor-patient-records-count");

  if (!tbody) {
    return;
  }

  try {
    const patients = await doctorFetchJson("/view-patients");
    if (countEl) {
      countEl.textContent = patients.length;
    }

    if (!patients.length) {
      tbody.innerHTML = '<tr><td colspan="2" class="px-6 py-8 text-center text-sm text-slate-500">No patients found.</td></tr>';
      return;
    }

    tbody.innerHTML = patients.map((patient) => `
      <tr class="border-t border-slate-200">
        <td class="px-6 py-4 text-sm font-semibold text-slate-900">${escapeDoctorHtml(patient.name)}</td>
        <td class="px-6 py-4 text-sm text-slate-600">${escapeDoctorHtml(patient.email)}</td>
      </tr>
    `).join("");
  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="2" class="px-6 py-8 text-center text-sm text-rose-600">Unable to load patient records.</td></tr>';
  }
}

window.addEventListener("DOMContentLoaded", () => {
  if (!ensureDoctorSession()) {
    return;
  }

  loadDoctorDashboard();
  loadDoctorPatientRecords();
});
