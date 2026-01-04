console.log("admin.js loaded");

// ================= AUTH GUARD =================
const token = localStorage.getItem("token");
const role = localStorage.getItem("role");
const username = localStorage.getItem("username");

if (!token || role !== "admin") {
    alert("Unauthorized access");
    window.location.href = "index.html";
    throw new Error("Unauthorized");
}

// ================= HEADER =================
const adminUserEl = document.getElementById("adminUser");
if (adminUserEl) {
    adminUserEl.innerText = "Logged in as: " + username;
}

// ================= LOAD SBUs =================
async function loadSBUs() {
    const res = await fetch(`${API_BASE}/admin/sbus`, {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
        alert("Failed to load SBUs");
        return;
    }

    const sbus = await res.json();

    // Existing output
    document.getElementById("output").innerHTML =
        sbus.map(s => `<p>${s.name} – ₦${s.daily_budget.toLocaleString()}</p>`).join("");

    // ✅ ADD THIS (report dropdown)
    const reportSBU = document.getElementById("reportSBU");
    if (reportSBU) {
        reportSBU.innerHTML = sbus
            .map(s => `<option value="${s.id}">${s.name}</option>`)
            .join("");
    }
}


// ================= CREATE STAFF MODAL =================
function openCreateStaff() {
    document.getElementById("modal").innerHTML = `
        <h3>Create Staff</h3>

        <input id="full_name" placeholder="Full name" />
        <input id="staff_username" placeholder="Username" />
        <input id="staff_password" placeholder="Password" />

        <select id="sbuSelect"></select>

        <button id="saveStaffBtn">Save</button>
    `;

    loadSBUOptions();

    document
        .getElementById("saveStaffBtn")
        .addEventListener("click", createStaff);
}

// ================= LOAD SBU OPTIONS =================
async function loadSBUOptions() {
    const res = await fetch(`${API_BASE}/admin/sbus`, {
        headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
        alert("Failed to load SBU list");
        return;
    }

    const sbus = await res.json();
    const sbuSelect = document.getElementById("sbuSelect");

    sbuSelect.innerHTML = sbus
        .map(s => `<option value="${s.id}">${s.name}</option>`)
        .join("");
}

// ================= CREATE STAFF =================
async function createStaff() {
    const payload = {
        full_name: document.getElementById("full_name").value.trim(),
        username: document.getElementById("staff_username").value.trim(),
        password: document.getElementById("staff_password").value,
        department_id: document.getElementById("sbuSelect").value
    };

    if (!payload.full_name || !payload.username || !payload.password) {
        alert("Fill all fields");
        return;
    }

    const res = await fetch(`${API_BASE}/admin/create-staff`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
    });

    if (!res.ok) {
        const err = await res.text();
        console.error(err);
        alert("Failed to create staff");
        return;
    }

    alert("Staff created successfully");
}

// ================= LOAD REPORT =================
document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("loadReportBtn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
        const sbuId = document.getElementById("reportSBU").value;
        const period = document.getElementById("reportPeriod").value;
        const date = document.getElementById("reportDate").value;

        if (!sbuId || !date) {
            alert("Select SBU and date");
            return;
        }

        const res = await fetch(
            `${API_BASE}/admin/sbu-report?sbu_id=${sbuId}&period=${period}&report_date=${date}`,
            {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            }
        );

        if (!res.ok) {
            alert("Failed to load report");
            return;
        }

        const data = await res.json();

        document.getElementById("reportResult").innerHTML = `
            <h4>${data.sbu.name}</h4>
            <p>Total Sales: ₦${data.total_sales.toLocaleString()}</p>
            <p>Total Expenses: ₦${data.expenses.total.toLocaleString()}</p>
            <p>Net Profit: ₦${data.net_profit.toLocaleString()}</p>
            <p>Performance: ${data.performance_percent}%</p>
        `;
    });
});



// ================= INIT =================
document.addEventListener("DOMContentLoaded", loadSBUs);


// ================= LOGOUT =================
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}

// expose globally for onclick
window.logout = logout;

