// LOGIN
function loginUser() {

  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  fetch("http://127.0.0.1:5000/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ email, password })
  })
  .then(res => res.json())
  .then(data => {
    if (data.message) {
      localStorage.setItem("user", email);
      localStorage.setItem("role", "patient");
      window.location.href = "predict.html";
    } else {
      alert(data.error);
    }
  });
}

// REGISTER
function registerUser() {

  const name = document.getElementById("name").value;
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  fetch("http://127.0.0.1:5000/register", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ name, email, password })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    window.location.href = "login.html";
  });
}

// PREDICT
function predict() {

  const data = {
    age: parseInt(document.getElementById("age").value),
    sex: parseInt(document.getElementById("sex").value),
    chest_pain_type: parseInt(document.getElementById("cp").value),
    resting_bp_s: parseInt(document.getElementById("trestbps").value),
    cholesterol: parseInt(document.getElementById("chol").value),
    fasting_blood_sugar: parseInt(document.getElementById("fbs").value),
    resting_ecg: parseInt(document.getElementById("restecg").value),
    max_heart_rate: parseInt(document.getElementById("thalach").value),
    exercise_angina: parseInt(document.getElementById("exang").value),
    oldpeak: parseFloat(document.getElementById("oldpeak").value),
    st_slope: parseInt(document.getElementById("slope").value),

    email: localStorage.getItem("user")
  };

  fetch("http://127.0.0.1:5000/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(data)
  })
  .then(res => res.json())
  .then(result => {
    document.getElementById("result").innerText =
      "Result: " + result.prediction;
  });
}

// HISTORY
function loadHistory() {

  fetch("http://127.0.0.1:5000/history", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      email: localStorage.getItem("user")
    })
  })
  .then(res => res.json())
  .then(data => {

    const container = document.getElementById("historyList");
    container.innerHTML = "";

    data.forEach(log => {
      container.innerHTML += `
        <div class="bg-white p-4 rounded-lg shadow">
          <p><strong>Date:</strong> ${log.date}</p>
          <p><strong>Result:</strong> ${log.result}</p>
        </div>
      `;
    });

  });
}

// LOGOUT
function logout(){
  localStorage.clear();
  window.location.href = "login.html";
}