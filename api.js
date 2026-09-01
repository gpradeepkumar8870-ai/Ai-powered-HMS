/* ==========================================================================
   AI-HMS — Central API helper.
   Wraps fetch() with the base URL, auth header, and consistent error handling.
   ========================================================================== */
const API_BASE_URL = "http://localhost:5000/api";

async function apiRequest(endpoint, { method = "GET", body = null, isFormData = false } = {}) {
  const headers = {};
  const token = localStorage.getItem("aihms_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isFormData) headers["Content-Type"] = "application/json";

  const config = { method, headers };
  if (body) config.body = isFormData ? body : JSON.stringify(body);

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${endpoint}`, config);
  } catch (err) {
    throw new Error("Cannot reach the server. Please make sure the Flask backend is running on port 5000.");
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    throw new Error("Unexpected server response");
  }

  if (response.status === 401) {
    // Token expired/invalid -> force re-login
    localStorage.removeItem("aihms_token");
    localStorage.removeItem("aihms_user");
    if (!window.location.pathname.includes("login.html")) {
      window.location.href = "/login.html";
    }
  }

  if (!data.success) {
    throw new Error(data.message || "Request failed");
  }
  return data;
}

const API = {
  // Auth
  register: (payload) => apiRequest("/auth/register", { method: "POST", body: payload }),
  login: (payload) => apiRequest("/auth/login", { method: "POST", body: payload }),
  me: () => apiRequest("/auth/me"),

  // Patients
  listDoctors: (department) => apiRequest(`/patients/doctors${department ? `?department=${department}` : ""}`),
  myPrescriptions: () => apiRequest("/patients/prescriptions"),
  medicalHistory: (patientId) => apiRequest(`/patients/medical-history${patientId ? `?patient_id=${patientId}` : ""}`),
  updateProfile: (payload) => apiRequest("/patients/profile", { method: "PUT", body: payload }),

  // Doctors
  doctorDashboardStats: () => apiRequest("/doctors/dashboard-stats"),
  myPatients: () => apiRequest("/doctors/my-patients"),
  writePrescription: (payload) => apiRequest("/doctors/prescriptions", { method: "POST", body: payload }),

  // Admin
  adminStats: () => apiRequest("/admin/dashboard-stats"),
  appointmentsTrend: () => apiRequest("/admin/analytics/appointments-trend"),
  departmentLoad: () => apiRequest("/admin/analytics/department-load"),
  listAllDoctors: (status) => apiRequest(`/admin/doctors${status ? `?status=${status}` : ""}`),
  approveDoctor: (id) => apiRequest(`/admin/doctors/${id}/approve`, { method: "PATCH" }),
  blockDoctor: (id) => apiRequest(`/admin/doctors/${id}/block`, { method: "PATCH" }),
  removeDoctor: (id) => apiRequest(`/admin/doctors/${id}`, { method: "DELETE" }),
  listAllPatients: () => apiRequest("/admin/patients"),
  removePatient: (id) => apiRequest(`/admin/patients/${id}`, { method: "DELETE" }),
  listDepartments: () => apiRequest("/admin/departments"),

  // Appointments
  bookAppointment: (payload) => apiRequest("/appointments", { method: "POST", body: payload }),
  listAppointments: (status) => apiRequest(`/appointments${status ? `?status=${status}` : ""}`),
  updateAppointmentStatus: (id, status) => apiRequest(`/appointments/${id}/status`, { method: "PATCH", body: { status } }),
  cancelAppointment: (id) => apiRequest(`/appointments/${id}`, { method: "DELETE" }),

  // AI
  getSymptomList: () => apiRequest("/ai/symptoms"),
  predictDisease: (symptoms) => apiRequest("/ai/predict", { method: "POST", body: { symptoms } }),
  chatbot: (message) => apiRequest("/ai/chatbot", { method: "POST", body: { message } }),
  chatbotSuggestions: () => apiRequest("/ai/chatbot/suggestions"),
  emergencyQueue: () => apiRequest("/ai/emergency-queue"),

  // Billing
  createBill: (payload) => apiRequest("/billing", { method: "POST", body: payload }),
  listBills: (status) => apiRequest(`/billing${status ? `?status=${status}` : ""}`),
  markBillPaid: (id) => apiRequest(`/billing/${id}/pay`, { method: "PATCH" }),

  // Lab
  listReports: (patientId) => apiRequest(`/lab/reports${patientId ? `?patient_id=${patientId}` : ""}`),
};
