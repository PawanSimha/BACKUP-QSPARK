/* QSPARK — customer portal, wallet checkout, digital pass, admin center */

const $ = (id) => document.getElementById(id);

const state = {
  token: sessionStorage.getItem("qspark_token"),
  user: null,
  floor: 1,
  slots: [],
  allBookings: [],
  selected: null,
  exitBooking: null,
  charts: {},
  lastPass: null,
};

/* ------------------------------------------------------------------ helpers */
const money = (value) => `₹${Number(value || 0).toFixed(2)}`;

function fmt(iso) {
  if (!iso) return "—";
  const d = new Date(String(iso).replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}

function esc(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

function notify(message, type = "success") {
  const el = document.createElement("div");
  el.className = `alert alert-${type} shadow-sm py-2 px-3 mb-2`;
  el.textContent = message;
  $("toastArea").appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const response = await fetch(path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || data.detail || `Request failed (${response.status})`);
  }
  return data;
}

function showOnly(viewId) {
  for (const id of ["loginView", "portalView", "adminView"]) {
    $(id).classList.toggle("d-none", id !== viewId);
  }
}

/* ------------------------------------------------------------------- session */
function setUser(user) {
  state.user = user;
  $("userName").textContent = user.full_name;
  $("roleBadge").textContent = user.role;
  $("roleBadge").className = `badge ms-1 ${user.role === "ADMIN" ? "text-bg-warning" : "text-bg-info"}`;
  $("userChip").classList.remove("d-none");
  $("btnBookings").classList.remove("d-none");
  $("btnLogout").classList.remove("d-none");
  $("btnAdmin").classList.toggle("d-none", user.role !== "ADMIN");
  updateWallet();
}

function updateWallet() {
  if (!state.user) return;
  $("walletChip").textContent = `💳 Wallet: ${money(state.user.wallet_balance)}`;
  $("walletChip").classList.remove("d-none");
  calcFare();
}

async function refreshUser() {
  if (!state.token) return;
  state.user = await api("/api/auth/me");
  setUser(state.user);
}

function showLogin() {
  showOnly("loginView");
  $("userChip").classList.add("d-none");
  $("walletChip").classList.add("d-none");
  $("btnBookings").classList.add("d-none");
  $("btnAdmin").classList.add("d-none");
  $("btnLogout").classList.add("d-none");
}

function logout() {
  state.token = null;
  state.user = null;
  sessionStorage.removeItem("qspark_token");
  showLogin();
}

async function login(loginId, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ login_id: loginId, password }),
  });
  state.token = data.token;
  sessionStorage.setItem("qspark_token", data.token);
  setUser(data.user);
  await showPortal();
}

/* --------------------------------------------------------------- customer UI */
async function showPortal() {
  showOnly("portalView");
  $("btnBookings").classList.remove("d-none");
  await loadSlots();
}

async function loadSlots() {
  const data = await api(`/api/slots?floor_id=${state.floor}`);
  state.slots = data.items;
  renderSlots();
}

function bayButton(slot) {
  const icon = slot.vehicle_type === "BIKE" ? "fa-motorcycle" : "fa-car";
  const selected = state.selected && state.selected.slot_id === slot.slot_id ? " selected" : "";
  return `<button type="button" class="bay ${slot.status.toLowerCase()}${selected}" data-slot="${slot.slot_id}">
      <i class="fa-solid ${icon}"></i><span>${esc(slot.slot_number)}</span>
    </button>`;
}

function renderSlots() {
  const bikes = state.slots.filter((s) => s.vehicle_type === "BIKE");
  const cars = state.slots.filter((s) => s.vehicle_type === "CAR");
  $("bikeSection").innerHTML = bikes.map(bayButton).join("");
  $("carSection").innerHTML = cars.map(bayButton).join("");
  $("bikeCount").textContent = `${bikes.filter((s) => s.status === "AVAILABLE").length} / ${bikes.length} available`;
  $("carCount").textContent = `${cars.filter((s) => s.status === "AVAILABLE").length} / ${cars.length} available`;

  document.querySelectorAll("#bikeSection .bay.available, #carSection .bay.available").forEach((btn) => {
    btn.addEventListener("click", () => {
      const slot = state.slots.find((s) => s.slot_id === Number(btn.dataset.slot));
      selectSlot(slot);
    });
  });
}

function selectSlot(slot) {
  if (!slot || slot.status !== "AVAILABLE") return;
  state.selected = slot;
  renderSlots();
  $("selectedSummary").innerHTML =
    `<i class="fa-solid fa-square-parking text-primary me-1"></i><strong>${esc(slot.slot_number)}</strong>` +
    ` · ${esc(slot.vehicle_type)} · ${money(slot.hourly_rate)}/hr` +
    ` <span class="badge text-bg-light ms-1">${esc(slot.floor_code)}</span>`;
  calcFare();
}

function calcFare() {
  const hours = Number($("durationRange")?.value || 1);
  $("durationLabel").textContent = `${hours.toFixed(1)} hr`;
  const slot = state.selected;
  const rate = slot ? Number(slot.hourly_rate) : 0;
  const fare = Math.round(hours * rate * 100) / 100;
  const balance = Number(state.user?.wallet_balance || 0);
  const remaining = Math.round((balance - fare) * 100) / 100;

  $("rateLabel").textContent = slot ? `${money(rate)}/hr` : "—";
  $("formulaLabel").textContent = `${hours.toFixed(1)} hr × ${money(rate)} = ${money(fare)}`;
  $("fareAmount").textContent = money(fare);
  $("balanceText").textContent = money(balance);
  $("remainingText").textContent = money(remaining);

  const insufficient = !slot || fare > balance;
  $("btnPay").disabled = insufficient;
  $("payBlocked").classList.toggle("d-none", !(slot && insufficient));
}

function openPayment() {
  const hours = Number($("durationRange").value);
  const fare = Math.round(hours * Number(state.selected.hourly_rate) * 100) / 100;
  const balance = Number(state.user.wallet_balance);
  $("payPrevious").textContent = money(balance);
  $("payFare").textContent = money(fare);
  $("payRemaining").textContent = money(balance - fare);
  $("payWarning").classList.toggle("d-none", balance >= fare);
  $("btnConfirmPay").disabled = balance < fare;
  bootstrap.Modal.getOrCreateInstance($("paymentModal")).show();
}

async function confirmPayment() {
  const hours = Number($("durationRange").value);
  const slot = state.selected;
  const plate = $("plateInput").value.trim() || "KA-01-MJ-2026";
  const button = $("btnConfirmPay");
  button.disabled = true;
  try {
    const booking = await api("/api/bookings", {
      method: "POST",
      body: JSON.stringify({
        user_id: state.user.user_id,
        slot_id: slot.slot_id,
        vehicle_number: plate,
        duration_hours: hours,
      }),
    });

    const start = new Date();
    const end = new Date(start.getTime() + hours * 3600 * 1000);
    state.user.wallet_balance = booking.new_wallet_balance;
    updateWallet();

    state.lastPass = {
      code: booking.booking_code,
      bay: booking.slot_number,
      floor: slot.floor_code,
      plate,
      window: `${fmt(start.toISOString())} - ${fmt(end.toISOString())}`,
      paid: booking.base_amount,
      balance: booking.new_wallet_balance,
    };

    bootstrap.Modal.getOrCreateInstance($("paymentModal")).hide();
    showPass(state.lastPass);
    await loadSlots();
    state.selected = null;
    calcFare();
    notify(`Booked ${booking.slot_number} for ${money(booking.base_amount)}`);
  } catch (error) {
    notify(error.message, "danger");
  } finally {
    button.disabled = false;
  }
}

function showPass(pass) {
  $("passCode").textContent = pass.code;
  $("passBay").textContent = `${pass.bay} · ${pass.floor}`;
  $("passPlate").textContent = pass.plate;
  $("passWindow").textContent = pass.window;
  $("passPaid").textContent = money(pass.paid);
  $("passBalance").textContent = money(pass.balance);
  drawQr(pass.code);
  bootstrap.Modal.getOrCreateInstance($("passModal")).show();
}

function drawQr(text) {
  const canvas = $("qrCanvas");
  const size = 25;
  const cell = 6;
  const offset = 5;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  let seed = 0;
  for (const ch of String(text)) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
  const random = () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };

  ctx.fillStyle = "#0f172a";
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      if (random() > 0.52) ctx.fillRect(offset + x * cell, offset + y * cell, cell, cell);
    }
  }

  const finder = (fx, fy) => {
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(offset + fx * cell, offset + fy * cell, 7 * cell, 7 * cell);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(offset + (fx + 1) * cell, offset + (fy + 1) * cell, 5 * cell, 5 * cell);
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(offset + (fx + 2) * cell, offset + (fy + 2) * cell, 3 * cell, 3 * cell);
  };
  finder(0, 0);
  finder(size - 7, 0);
  finder(0, size - 7);
}

function printPass() {
  const pass = state.lastPass;
  if (!pass) return;
  $("printArea").innerHTML = `
    <div style="font-family:system-ui;max-width:420px;margin:2rem auto;border:2px dashed #0f172a;border-radius:12px;padding:24px">
      <h2 style="margin:0 0 4px">QSPARK</h2>
      <div style="color:#64748b;margin-bottom:16px">Digital Parking Pass</div>
      <div style="font-size:22px;font-weight:800;margin-bottom:12px">${esc(pass.code)}</div>
      <p><strong>Bay:</strong> ${esc(pass.bay)} (${esc(pass.floor)})</p>
      <p><strong>Vehicle:</strong> ${esc(pass.plate)}</p>
      <p><strong>Validity:</strong> ${esc(pass.window)}</p>
      <p><strong>Paid:</strong> ${money(pass.paid)} · <strong>Wallet:</strong> ${money(pass.balance)}</p>
      <div style="margin-top:16px;padding:12px;background:#0f172a;color:#fff;text-align:center;border-radius:8px">Show this pass at the boom barrier</div>
    </div>`;
  window.print();
}

/* ------------------------------------------------------------------ bookings */
async function loadBookings() {
  const data = await api(`/api/bookings?user_id=${state.user.user_id}`);
  state.allBookings = data.items;
  renderBookings();
}

function renderBookings() {
  const rows = state.allBookings.map((booking) => {
    const badge = {
      CONFIRMED: "text-bg-warning",
      COMPLETED: "text-bg-success",
      CANCELLED: "text-bg-secondary",
      CHECKED_IN: "text-bg-primary",
      OVERSTAY: "text-bg-danger",
    }[booking.status] || "text-bg-light";

    const actions = [];
    if (booking.status === "CONFIRMED") {
      actions.push(`<button class="btn btn-sm btn-outline-danger" data-cancel="${booking.booking_id}">Cancel</button>`);
    }
    if (["CONFIRMED", "CHECKED_IN", "OVERSTAY"].includes(booking.status)) {
      actions.push(`<button class="btn btn-sm btn-outline-warning" data-exit="${booking.booking_id}">Simulate Exit</button>`);
    }

    return `<tr>
      <td class="fw-semibold">${esc(booking.booking_code)}</td>
      <td>${esc(booking.slot_number)} <span class="text-muted small">${esc(booking.floor_code)}</span></td>
      <td>${esc(booking.vehicle_number)}<div class="small text-muted">${esc(booking.vehicle_type)}</div></td>
      <td class="small">${fmt(booking.scheduled_start)}<br>${fmt(booking.scheduled_end)}</td>
      <td>${money(booking.total_amount)}</td>
      <td><span class="badge ${badge}">${esc(booking.status)}</span></td>
      <td class="text-nowrap">${actions.join(" ")}</td>
    </tr>`;
  });
  $("bookingsBody").innerHTML = rows.join("") || `<tr><td colspan="7" class="text-center text-muted py-4">No bookings yet.</td></tr>`;
}

async function cancelBooking(bookingId) {
  if (!window.confirm("Cancel this booking and refund the full fare?")) return;
  try {
    const result = await api(`/api/bookings/${bookingId}/cancel`, { method: "PUT" });
    notify(`Refunded ${money(result.refunded_amount)} · wallet ${money(result.restored_wallet_balance)}`);
    await refreshUser();
    await loadSlots();
    await loadBookings();
  } catch (error) {
    notify(error.message, "danger");
  }
}

function openExit(bookingId) {
  const booking = state.allBookings.find((b) => b.booking_id === bookingId);
  if (!booking) return;
  state.exitBooking = booking;
  $("exitBookingLabel").textContent = `${booking.booking_code} · ${booking.slot_number} · ${booking.vehicle_type}`;
  $("exitDelay").value = "0";
  bootstrap.Modal.getOrCreateInstance($("exitModal")).show();
}

async function processExit() {
  const booking = state.exitBooking;
  if (!booking) return;
  const delay = Number($("exitDelay").value);
  const end = new Date(String(booking.scheduled_end).replace(" ", "T"));
  // Exit at scheduled_end + chosen delay, even for seeded bookings whose window has passed.
  const remainingHours = (end.getTime() - Date.now()) / 3600000;
  const simulated = Math.round((remainingHours + delay) * 100) / 100;

  try {
    const result = await api(`/api/bookings/${booking.booking_id}/checkout`, {
      method: "PUT",
      body: JSON.stringify({ simulated_late_hours: simulated }),
    });
    bootstrap.Modal.getOrCreateInstance($("exitModal")).hide();
    notify(
      result.penalty_charged > 0
        ? `Exit settled · ${result.overstay_hours.toFixed(2)} h overstay · penalty ${money(result.penalty_charged)}`
        : "Exit settled on time · no penalty",
      result.penalty_charged > 0 ? "warning" : "success"
    );
    await refreshUser();
    await loadSlots();
    await loadBookings();
  } catch (error) {
    notify(error.message, "danger");
  }
}

/* --------------------------------------------------------------------- admin */
async function showAdmin() {
  if (!state.user || state.user.role !== "ADMIN") return;
  showOnly("adminView");
  if (!$("trackAdminName").value) $("trackAdminName").value = state.user.username;
  try {
    const [kpi, slots, bookings, audit] = await Promise.all([
      api("/api/analytics/kpi"),
      api("/api/slots"),
      api("/api/bookings"),
      api("/api/analytics/audit"),
    ]);
    state.slots = slots.items;
    state.allBookings = bookings.items;
    renderKpi(kpi);
    renderHeatmap(kpi.floor_heatmaps);
    renderCharts(kpi, bookings.items);
    renderOverrideTable(slots.items, $("overrideSearch").value);
    renderAudit(audit.items);
  } catch (error) {
    notify(error.message, "danger");
  }
}

function renderKpi(kpi) {
  $("kpiTotal").textContent = kpi.total_slots;
  $("kpiOccupancy").textContent = `${kpi.occupancy_rate_percent.toFixed(2)}%`;
  $("kpiActive").textContent = kpi.reserved_slots + kpi.occupied_slots;
  $("kpiRevenue").textContent = money(kpi.total_revenue_collected);
}

function renderHeatmap(floors) {
  $("heatmap").innerHTML = floors
    .map((floor) => {
      const pct = floor.occupancy_percent;
      const color = pct < 35 ? "bg-success" : pct <= 70 ? "bg-warning" : "bg-danger";
      return `<div class="mb-3">
        <div class="d-flex justify-content-between small fw-semibold">
          <span>${esc(floor.floor_code)}</span><span>${floor.occupied}/${floor.total} · ${pct.toFixed(2)}%</span>
        </div>
        <div class="progress heat-bar mt-1">
          <div class="progress-bar ${color}" role="progressbar" style="width:${Math.min(100, pct)}%"></div>
        </div>
      </div>`;
    })
    .join("");
}

function renderCharts(kpi, bookings) {
  if (state.charts.status) state.charts.status.destroy();
  if (state.charts.revenue) state.charts.revenue.destroy();

  state.charts.status = new Chart($("statusChart"), {
    type: "doughnut",
    data: {
      labels: ["Available", "Reserved", "Occupied", "Maintenance"],
      datasets: [{
        data: [kpi.available_slots, kpi.reserved_slots, kpi.occupied_slots, kpi.maintenance_slots],
        backgroundColor: ["#10b981", "#f59e0b", "#ef4444", "#64748b"],
      }],
    },
    options: { plugins: { legend: { position: "bottom" } }, maintainAspectRatio: false },
  });

  const byType = { BIKE: 0, CAR: 0 };
  bookings.forEach((booking) => {
    if (booking.status !== "CANCELLED" && byType[booking.vehicle_type] !== undefined) {
      byType[booking.vehicle_type] += Number(booking.total_amount || 0);
    }
  });

  state.charts.revenue = new Chart($("revenueChart"), {
    type: "bar",
    data: {
      labels: ["Bike", "Car"],
      datasets: [{ label: "Revenue", data: [byType.BIKE, byType.CAR], backgroundColor: ["#2563eb", "#0f172a"] }],
    },
    options: {
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
      maintainAspectRatio: false,
    },
  });
}

function renderOverrideTable(slots, filter = "") {
  const needle = String(filter || "").toLowerCase();
  const options = ["AVAILABLE", "OCCUPIED", "MAINTENANCE"]
    .map((status) => `<option value="${status}">${status}</option>`)
    .join("");

  $("overrideBody").innerHTML = slots
    .filter((slot) => !needle || slot.slot_number.toLowerCase().includes(needle))
    .map(
      (slot) => `<tr data-slot="${slot.slot_id}">
        <td class="fw-semibold">${esc(slot.slot_number)}</td>
        <td>${esc(slot.vehicle_type)}</td>
        <td>${esc(slot.status)}</td>
        <td>
          <select class="form-select form-select-sm override-select" data-slot="${slot.slot_id}">
            <option value="">Set…</option>${options}
          </select>
        </td>
      </tr>`
    )
    .join("");
}

async function applyOverride(select) {
  const slotId = Number(select.dataset.slot);
  const status = select.value;
  if (!status) return;
  try {
    await api(`/api/slots/${slotId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status, admin_user_id: state.user.user_id }),
    });
    notify(`Bay set to ${status}`);
    await showAdmin();
  } catch (error) {
    notify(error.message, "danger");
    select.value = "";
  }
}

function renderAudit(logs) {
  $("auditBody").innerHTML = logs
    .map(
      (log) => `<tr>
        <td class="small text-nowrap">${fmt(log.logged_at)}</td>
        <td><span class="badge text-bg-light">${esc(log.event_type)}</span></td>
        <td class="small">${esc(log.full_name || log.changed_by_user_id || "—")}</td>
        <td class="small">${esc(log.slot_number || "—")}</td>
        <td class="small">${esc(log.old_state || "—")} → ${esc(log.new_state || "—")}</td>
      </tr>`
    )
    .join("") || `<tr><td colspan="5" class="text-center text-muted py-4">No audit entries.</td></tr>`;
}

/* -------------------------------------------------------------------- events */
function bindEvents() {
  $("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await login($("loginId").value.trim(), $("loginPassword").value);
    } catch (error) {
      notify(error.message, "danger");
    }
  });

  document.querySelectorAll(".quick-login").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await login(button.dataset.login, button.dataset.password);
      } catch (error) {
        notify(error.message, "danger");
      }
    });
  });

  $("btnLogout").addEventListener("click", logout);
  $("btnPortal").addEventListener("click", () => showPortal());
  $("btnAdmin").addEventListener("click", () => showAdmin());
  $("btnBookings").addEventListener("click", async () => {
    try {
      await loadBookings();
      bootstrap.Offcanvas.getOrCreateInstance($("bookingsDrawer")).show();
    } catch (error) {
      notify(error.message, "danger");
    }
  });

  $("floorTabs").addEventListener("click", (event) => {
    const button = event.target.closest("[data-floor]");
    if (!button) return;
    state.floor = Number(button.dataset.floor);
    state.selected = null;
    document.querySelectorAll("#floorTabs .nav-link").forEach((tab) => tab.classList.toggle("active", tab === button));
    $("selectedSummary").textContent = "Select an available bay from the grid.";
    calcFare();
    loadSlots().catch((error) => notify(error.message, "danger"));
  });

  $("durationRange").addEventListener("input", calcFare);
  $("btnPay").addEventListener("click", openPayment);
  $("btnConfirmPay").addEventListener("click", confirmPayment);
  $("btnPrintPass").addEventListener("click", printPass);
  $("btnProcessExit").addEventListener("click", processExit);
  $("btnRefreshAdmin").addEventListener("click", () => showAdmin());
  $("auditTrackForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = {
      admin_name: $("trackAdminName").value.trim(),
      modified_table: $("trackTable").value,
      modified_column: $("trackColumn").value.trim(),
      why_modified: $("trackReason").value.trim(),
    };
    try {
      const result = await api("/api/admin/audit-track", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      notify(`Compliance record #${result.track_id} logged`);
      $("trackReason").value = "";
    } catch (error) {
      notify(error.message, "danger");
    }
  });
  $("overrideSearch").addEventListener("input", (event) => renderOverrideTable(state.slots, event.target.value));

  $("bookingsBody").addEventListener("click", (event) => {
    const cancel = event.target.closest("[data-cancel]");
    if (cancel) return cancelBooking(Number(cancel.dataset.cancel));
    const exit = event.target.closest("[data-exit]");
    if (exit) return openExit(Number(exit.dataset.exit));
  });

  $("overrideBody").addEventListener("change", (event) => {
    if (event.target.classList.contains("override-select")) applyOverride(event.target);
  });
}

/* ---------------------------------------------------------------------- boot */
document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  calcFare();
  if (!state.token) return showLogin();
  try {
    const user = await api("/api/auth/me");
    setUser(user);
    await showPortal();
  } catch {
    logout();
  }
});
