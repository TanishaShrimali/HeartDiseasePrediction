const ROLE_DASHBOARDS = {
  patient: "patient_dashboard.html",
  doctor: "doctor_dashboard.html",
  admin: "admin_dashboard.html"
};

function getStoredRole() {
  return localStorage.getItem("role") || "";
}

function getStoredUser() {
  return localStorage.getItem("user") || "";
}

function getDashboardForRole(role) {
  return ROLE_DASHBOARDS[role] || "login.html";
}

function hasActiveSession() {
  const role = getStoredRole();
  const user = getStoredUser();
  return Boolean(role && user && ROLE_DASHBOARDS[role]);
}

function clearSession() {
  localStorage.removeItem("user");
  localStorage.removeItem("role");
}

function logoutUser(event) {
  if (event) {
    event.preventDefault();
  }

  clearSession();
  window.location.href = "index.html";
}

function requireRoleSession(expectedRole) {
  const role = getStoredRole();
  const user = getStoredUser();

  if (!role || !user) {
    window.location.href = "login.html";
    return false;
  }

  if (role !== expectedRole) {
    window.location.href = getDashboardForRole(role);
    return false;
  }

  return true;
}

window.logoutUser = logoutUser;
window.requireRoleSession = requireRoleSession;
window.getStoredRole = getStoredRole;
window.getStoredUser = getStoredUser;

function showHomeForSession() {
  const role = getStoredRole();
  const dashboard = getDashboardForRole(role);
  const guestNodes = document.querySelectorAll("[data-auth='guest']");
  const userNodes = document.querySelectorAll("[data-auth='user']");
  const roleNodes = document.querySelectorAll("[data-session-role]");
  const dashboardNodes = document.querySelectorAll("[data-session-dashboard]");

  guestNodes.forEach((node) => node.classList.add("hidden"));
  userNodes.forEach((node) => node.classList.remove("hidden"));
  roleNodes.forEach((node) => {
    node.textContent = role ? role.charAt(0).toUpperCase() + role.slice(1) : "User";
  });
  dashboardNodes.forEach((node) => {
    node.setAttribute("href", dashboard);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const requiredRole = body?.dataset?.requiredRole || "";
  const isHomePage = body?.dataset?.homePage === "true";
  const isAuthEntry = body?.dataset?.authEntry === "true";

  if (isHomePage && hasActiveSession()) {
    showHomeForSession();
  }

  if (isAuthEntry && hasActiveSession()) {
    window.location.href = "index.html";
    return;
  }

  if (requiredRole && !requireRoleSession(requiredRole)) {
    return;
  }

  document.querySelectorAll("[data-logout='true']").forEach((button) => {
    button.addEventListener("click", logoutUser);
  });
});
