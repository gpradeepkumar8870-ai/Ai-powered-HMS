/* ==========================================================================
   AI-HMS — Auth guard + shared header/session helpers.
   ========================================================================== */

function saveSession(token, user) {
  localStorage.setItem("aihms_token", token);
  localStorage.setItem("aihms_user", JSON.stringify(user));
}

function getCurrentUser() {
  const raw = localStorage.getItem("aihms_user");
  return raw ? JSON.parse(raw) : null;
}

function logout() {
  localStorage.removeItem("aihms_token");
  localStorage.removeItem("aihms_user");
  window.location.href = "/login.html";
}

/**
 * Call at the top of every protected page.
 * Redirects to login if not authenticated, or to the correct
 * dashboard if the logged-in role doesn't match the page's expected role.
 */
function requireRole(expectedRole) {
  const token = localStorage.getItem("aihms_token");
  const user = getCurrentUser();
  if (!token || !user) {
    window.location.href = "/login.html";
    return null;
  }
  if (expectedRole && user.role !== expectedRole) {
    window.location.href = `/${user.role}/dashboard.html`;
    return null;
  }
  const nameEl = document.getElementById("current-user-name");
  if (nameEl) nameEl.textContent = user.name;
  return user;
}

function showToast(message, type = "success") {
  const containerId = "toast-container";
  let container = document.getElementById(containerId);
  if (!container) {
    container = document.createElement("div");
    container.id = containerId;
    container.className = "toast-container position-fixed top-0 end-0 p-3";
    container.style.zIndex = 1080;
    document.body.appendChild(container);
  }
  const toastEl = document.createElement("div");
  toastEl.className = `toast align-items-center text-white bg-${type === "success" ? "success" : "danger"} border-0`;
  toastEl.setAttribute("role", "alert");
  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toastEl);
  const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
  toastEl.addEventListener("hidden.bs.toast", () => toastEl.remove());
}

function formatDate(dateStr) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  if (isNaN(d)) return dateStr;
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function statusBadge(status) {
  return `<span class="badge badge-status-${status}">${status}</span>`;
}

function riskBadge(risk) {
  return `<span class="badge badge-risk-${risk}">${risk}</span>`;
}
