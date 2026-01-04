console.log("staff.js loaded");

// ---------- AUTH GUARD ----------
const token = localStorage.getItem("token");
const role = localStorage.getItem("role");
const username = localStorage.getItem("username");

if (!token || role !== "staff") {
    alert("Unauthorized access");
    window.location.href = "index.html";
}

// ---------- LOGOUT ----------
function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}
window.logout = logout;

// ---------- LOAD DASHBOARD ----------
async function loadStaffDashboard() {
    try {
        const res = await fetch("http://127.0.0.1:8000/staff/my-sbu", {
            headers: {
                "Authorization": `Bearer ${token}`
            }
        });

        if (!res.ok) {
            throw new Error("Failed to load staff SBU");
        }

        const data = await res.json();
        console.log("Staff SBU data:", data);

        const sbu = data.sbu;
        const salesToday = data.sales_today || 0;

        const fixed = data.fixed_costs || {};
        const variable = data.variable_costs || {};

        const netProfit = data.net_profit || 0;
        const performance = data.performance_percent || 0;
        const status = data.performance_status;

        const personnel = fixed.personnel_cost || 0;
        const rent = fixed.rent || 0;
        const electricity = fixed.electricity || 0;

        const totalExpenses = data.total_expenses || 0;

        // ---------- UPDATE UI ----------
        document.getElementById("staffName").innerText = username;
        document.getElementById("sbuName").innerText = sbu.name;

        document.getElementById("dailyBudget").innerText =
            sbu.daily_budget.toLocaleString();

        document.getElementById("salesToday").innerText =
            salesToday.toLocaleString();

        // ---------- PERFORMANCE ----------
        const performanceEl = document.getElementById("performance");
        performanceEl.innerText = performance + "%";
        performanceEl.classList.remove("good", "warn", "bad");

        if (status === "excellent") {
            performanceEl.classList.add("good");
        } else if (status === "warning") {
            performanceEl.classList.add("warn");
        } else {
            performanceEl.classList.add("bad");
        }

        // ---------- FIXED COSTS ----------
        document.getElementById("personnel").innerText =
            personnel.toLocaleString();

        document.getElementById("rent").innerText =
            rent.toLocaleString();

        document.getElementById("electricity").innerText =
            electricity.toLocaleString();

        // ---------- VARIABLE COSTS ----------
        document.getElementById("consumables").innerText =
            (variable.consumables || 0).toLocaleString();

        document.getElementById("generalExpenses").innerText =
            (variable.general_expenses || 0).toLocaleString();

        document.getElementById("miscellaneous").innerText =
            (variable.miscellaneous || 0).toLocaleString();

        document.getElementById("totalExpenses").innerText =
            totalExpenses.toLocaleString();

        document.getElementById("netProfit").innerText =
            netProfit.toLocaleString();

    } catch (err) {
        console.error(err);
        alert("Error loading staff dashboard");
    }
}

// ---------- SAVE EXPENSE ----------
function initExpenseSave() {
    const saveExpenseBtn = document.getElementById("saveExpenseBtn");
    if (!saveExpenseBtn) return;

    saveExpenseBtn.addEventListener("click", async () => {
        const categoryEl = document.getElementById("expenseCategory");
        const amountEl = document.getElementById("expenseAmount");
        const dateEl = document.getElementById("expenseDate");
        const notesEl = document.getElementById("expenseNotes");

        if (!categoryEl || !amountEl || !dateEl) {
            alert("Expense inputs missing in HTML");
            return;
        }

        const category = categoryEl.value;
        const amount = Number(amountEl.value);
        const date = dateEl.value;
        const notes = notesEl?.value || "";

        if (!amount || amount <= 0) {
            alert("Enter a valid expense amount");
            return;
        }

        if (!date) {
            alert("Select expense date");
            return;
        }

        const res = await fetch("http://127.0.0.1:8000/staff/expenses", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${token}`
            },
            body: JSON.stringify({ category, amount, date, notes })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(err.detail || "Failed to save expense");
            return;
        }

        alert("Expense saved / updated for today");

        amountEl.value = "";
        if (notesEl) notesEl.value = "";

        await loadStaffDashboard();
    });
}

// ---------- INIT ----------
document.addEventListener("DOMContentLoaded", () => {
    loadStaffDashboard();
    initExpenseSave();
});
