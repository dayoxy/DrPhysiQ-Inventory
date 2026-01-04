function show(id) {
    document.getElementById(id).classList.remove("hidden");
}

function hide(id) {
    document.getElementById(id).classList.add("hidden");
}

function logout() {
    localStorage.clear();
    window.location.href = "index.html";
}
