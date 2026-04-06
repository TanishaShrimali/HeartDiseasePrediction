function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidName(name) {
  return /^[A-Za-z ]+$/.test(name);
}

function isValidPassword(password) {
  return password.length >= 8 && password.length <= 64;
}

function getBcryptClient() {
  return window.dcodeIO?.bcrypt || window.bcrypt || null;
}

async function hashPasswordForTransport(password) {
  const bcryptClient = getBcryptClient();
  if (!bcryptClient) {
    return password;
  }

  const salt = await bcryptClient.genSalt(10);
  return bcryptClient.hash(password, salt);
}

function loginUser(event) {
  if (event) {
    event.preventDefault();
  }

  const identifier = document.getElementById("email")?.value.trim() || "";
  const password = document.getElementById("password")?.value.trim() || "";
  const role = document.getElementById("role")?.value || "";

  if (!identifier || !password || !role) {
    alert("All fields are required!");
    return;
  }

  if (role === "admin" && identifier.length < 3) {
    alert("Enter a valid admin username!");
    return;
  }

  if (role !== "admin" && !isValidEmail(identifier)) {
    alert("Enter a valid email!");
    return;
  }

  if (!isValidPassword(password)) {
    alert("Password must be between 8 and 64 characters.");
    return;
  }

  const roleConfig = {
    patient: {
      endpoint: "http://127.0.0.1:5000/login",
      body: { email: identifier, password },
      redirect: "patient_dashboard.html"
    },
    doctor: {
      endpoint: "http://127.0.0.1:5000/doctor-login",
      body: { email: identifier, password },
      redirect: "doctor_dashboard.html"
    },
    admin: {
      endpoint: "http://127.0.0.1:5000/admin-login",
      body: { username: identifier, email: identifier, password },
      redirect: "admin_dashboard.html"
    }
  };

  const selectedRole = roleConfig[role];

  fetch(selectedRole.endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(selectedRole.body)
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.message) {
        localStorage.setItem("user", identifier);
        localStorage.setItem("role", role);
        window.location.href = selectedRole.redirect;
        return;
      }

      alert(data.error || "Login failed");
    })
    .catch(() => {
      alert("Unable to connect to the server.");
    });
}

async function registerUser(event) {
  if (event) {
    event.preventDefault();
  }

  const name = document.getElementById("name")?.value.trim() || "";
  const email = document.getElementById("email")?.value.trim() || "";
  const password = document.getElementById("password")?.value.trim() || "";

  if (!name || !email || !password) {
    alert("All fields are required!");
    return;
  }

  if (!isValidName(name)) {
    alert("Name should contain only letters!");
    return;
  }

  if (name.length < 2 || name.length > 60) {
    alert("Name must be between 2 and 60 characters.");
    return;
  }

  if (!isValidEmail(email)) {
    alert("Invalid email format!");
    return;
  }

  if (!isValidPassword(password)) {
    alert("Password must be between 8 and 64 characters.");
    return;
  }

  const hashedPassword = await hashPasswordForTransport(password);

  fetch("http://127.0.0.1:5000/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, password: hashedPassword })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.message) {
        alert(data.message);
        window.location.href = "login.html";
        return;
      }

      alert(data.error || "Registration failed");
    })
    .catch(() => {
      alert("Unable to connect to the server.");
    });
}

async function resetPassword(event) {
  if (event) {
    event.preventDefault();
  }

  const role = document.getElementById("reset-role")?.value || "";
  const email = document.getElementById("reset-email")?.value.trim() || "";
  const password = document.getElementById("reset-password")?.value.trim() || "";
  const confirmPassword = document.getElementById("reset-confirm-password")?.value.trim() || "";

  if (!role || !email || !password || !confirmPassword) {
    alert("All fields are required!");
    return;
  }

  if (role !== "patient" && role !== "doctor") {
    alert("Only patient and doctor accounts can be reset here.");
    return;
  }

  if (!isValidEmail(email)) {
    alert("Enter a valid email!");
    return;
  }

  if (!isValidPassword(password)) {
    alert("Password must be between 8 and 64 characters.");
    return;
  }

  if (password !== confirmPassword) {
    alert("Passwords do not match.");
    return;
  }

  const hashedPassword = await hashPasswordForTransport(password);

  fetch("http://127.0.0.1:5000/forgot-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role, email, password: hashedPassword })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.message) {
        alert(data.message);
        window.location.href = "login.html";
        return;
      }

      alert(data.error || "Password reset failed");
    })
    .catch(() => {
      alert("Unable to connect to the server.");
    });
}
