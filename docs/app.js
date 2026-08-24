const DATA_URL = "./mainboard_ipos_web.json";
const DISPATCH_WORKFLOW = "set-ipo-allotment.yml";

const els = {
  body: document.getElementById("tableBody"),
  search: document.getElementById("searchInput"),
  status: document.getElementById("statusFilter"),
  refresh: document.getElementById("refreshBtn"),
  token: document.getElementById("ghToken"),
  owner: document.getElementById("ghOwner"),
  repo: document.getElementById("ghRepo"),
  branch: document.getElementById("ghBranch"),
  toast: document.getElementById("toast"),
};

let allRows = [];

function showToast(msg, isError = false) {
  els.toast.textContent = msg;
  els.toast.style.background = isError ? "#7f1d1d" : "#111827";
  els.toast.classList.add("show");
  window.setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function norm(v) {
  return String(v || "").trim();
}

function formatSubsc(v) {
  const text = norm(v);
  if (!text) return "";
  if (/x$/i.test(text)) return text;
  return `${text}x`;
}

function formatDateNoYear(v) {
  const text = norm(v);
  if (!text) return "";
  return text.replace(/,\s*\d{4}$/, "").replace(/\s+\d{4}$/, "");
}

function applyGotSelectClass(selectEl, rawValue) {
  const val = norm(rawValue).toLowerCase();
  selectEl.classList.remove("got-select--yes", "got-select--no", "got-select--na", "got-select--empty");
  if (val === "yes") {
    selectEl.classList.add("got-select--yes");
  } else if (val === "no") {
    selectEl.classList.add("got-select--no");
  } else if (val === "na" || val === "n/a") {
    selectEl.classList.add("got-select--na");
  } else {
    selectEl.classList.add("got-select--empty");
  }
}

function statusClass(status) {
  const s = norm(status).toLowerCase();
  if (s === "open") return "open";
  if (s === "upcoming") return "upcoming";
  if (s === "listed") return "listed";
  return "closed";
}

function render() {
  const q = norm(els.search.value).toLowerCase();
  const filterStatus = els.status.value;

  const rows = allRows.filter((row) => {
    const company = norm(row.company_name).toLowerCase();
    const status = norm(row.ipo_status);
    const matchesText = !q || company.includes(q);
    const matchesStatus = filterStatus === "all" || status === filterStatus;
    return matchesText && matchesStatus;
  });

  els.body.innerHTML = "";

  for (const row of rows) {
    const tr = document.createElement("tr");
    const gotRaw = norm(row.got_ipo).toLowerCase();
    if (gotRaw === "yes") {
      tr.classList.add("got-yes");
    } else if (gotRaw === "no") {
      tr.classList.add("got-no");
    } else if (gotRaw === "n/a") {
      tr.classList.add("got-na");
    }

    const companyTd = document.createElement("td");
    companyTd.className = "company-cell";
    companyTd.title = norm(row.company_name);

    const companySpan = document.createElement("span");
    companySpan.className = "company-name-text";
    companySpan.textContent = norm(row.company_name) || "(unknown)";

    companyTd.appendChild(companySpan);

    const statusTd = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status ${statusClass(row.ipo_status)}`;
    badge.textContent = norm(row.ipo_status) || "Unknown";
    statusTd.appendChild(badge);

    const appliedTd = document.createElement("td");
    const appliedWrap = document.createElement("div");
    appliedWrap.className = "action-cell";
    const appliedRaw = norm(row.applied).toLowerCase();

    const appliedSelect = document.createElement("select");
    appliedSelect.className = "got-select";

    const appPlaceholder = document.createElement("option");
    appPlaceholder.value = "";
    appPlaceholder.textContent = "Select";
    appliedSelect.appendChild(appPlaceholder);

    const appOptYes = document.createElement("option");
    appOptYes.value = "yes";
    appOptYes.textContent = "Yes";
    appliedSelect.appendChild(appOptYes);

    const appOptNo = document.createElement("option");
    appOptNo.value = "no";
    appOptNo.textContent = "No";
    appliedSelect.appendChild(appOptNo);

    const appOptNa = document.createElement("option");
    appOptNa.value = "na";
    appOptNa.textContent = "N/A";
    appliedSelect.appendChild(appOptNa);

    if (appliedRaw === "yes" || appliedRaw === "no" || appliedRaw === "n/a") {
      appliedSelect.value = appliedRaw === "n/a" ? "na" : appliedRaw;
      appliedSelect.disabled = true;
      appliedSelect.classList.add("locked");
      applyGotSelectClass(appliedSelect, appliedSelect.value);
    } else {
      appliedSelect.value = "";
      applyGotSelectClass(appliedSelect, appliedSelect.value);
      appliedSelect.addEventListener("change", () => {
        const selected = norm(appliedSelect.value).toLowerCase();
        if (!selected) return;
        applyGotSelectClass(appliedSelect, selected);
        updateStatus(row.company_name, { applied: selected });
      });
    }

    appliedWrap.appendChild(appliedSelect);
    appliedTd.appendChild(appliedWrap);

    const gotTd = document.createElement("td");
    const gotWrap = document.createElement("div");
    gotWrap.className = "action-cell";
    const got = gotRaw;

    const gotSelect = document.createElement("select");
    gotSelect.className = "got-select";

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select";
    gotSelect.appendChild(placeholder);

    const optYes = document.createElement("option");
    optYes.value = "yes";
    optYes.textContent = "Yes";
    gotSelect.appendChild(optYes);

    const optNo = document.createElement("option");
    optNo.value = "no";
    optNo.textContent = "No";
    gotSelect.appendChild(optNo);

    const optNa = document.createElement("option");
    optNa.value = "na";
    optNa.textContent = "N/A";
    gotSelect.appendChild(optNa);

    if (got === "yes" || got === "no" || got === "n/a") {
      gotSelect.value = got === "n/a" ? "na" : got;
      gotSelect.disabled = true;
      gotSelect.classList.add("locked");
      applyGotSelectClass(gotSelect, gotSelect.value);
    } else {
      gotSelect.value = "";
      applyGotSelectClass(gotSelect, gotSelect.value);
      gotSelect.addEventListener("change", () => {
        const selected = norm(gotSelect.value).toLowerCase();
        if (!selected) return;
        applyGotSelectClass(gotSelect, selected);
        updateStatus(row.company_name, { got_ipo: selected });
      });
    }

    gotWrap.appendChild(gotSelect);
    gotTd.appendChild(gotWrap);

    const openTd = document.createElement("td");
    openTd.textContent = formatDateNoYear(row.open_date);
    const closeTd = document.createElement("td");
    closeTd.textContent = formatDateNoYear(row.close_date);
    const allotTd = document.createElement("td");
    allotTd.textContent = formatDateNoYear(row.allotment_date);
    const listTd = document.createElement("td");
    listTd.textContent = formatDateNoYear(row.listing_date);
    const lotTd = document.createElement("td");
    lotTd.textContent = norm(row.lot_size);
    const bandTd = document.createElement("td");
    bandTd.textContent = norm(row.price_band);
    const invTd = document.createElement("td");
    invTd.textContent = norm(row.invested);
    const listPriceTd = document.createElement("td");
    listPriceTd.textContent = norm(row.listing_price);
    const outputTd = document.createElement("td");
    outputTd.textContent = norm(row.output);
    const gainTd = document.createElement("td");
    gainTd.textContent = norm(row.listing_gain);
    const subscTd = document.createElement("td");
    subscTd.textContent = formatSubsc(row.total_subsc);

    tr.append(
      companyTd,
      statusTd,
      appliedTd,
      gotTd,
      openTd,
      closeTd,
      allotTd,
      listTd,
      lotTd,
      bandTd,
      invTd,
      listPriceTd,
      outputTd,
      gainTd,
      subscTd
    );
    els.body.appendChild(tr);
  }
}

async function fetchRows() {
  const res = await fetch(`${DATA_URL}?ts=${Date.now()}`);
  if (!res.ok) throw new Error(`Failed to fetch data: HTTP ${res.status}`);
  const payload = await res.json();
  allRows = Array.isArray(payload.rows) ? payload.rows : [];
  render();
}

async function updateStatus(companyName, opts = {}) {
  const token = norm(els.token.value);
  const owner = norm(els.owner.value);
  const repo = norm(els.repo.value);
  const branch = norm(els.branch.value) || "main";

  if (!token) {
    showToast("Enter GitHub token first", true);
    return;
  }
  if (!owner || !repo) {
    showToast("Owner/repo missing", true);
    return;
  }

  const endpoint = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${DISPATCH_WORKFLOW}/dispatches`;
  const body = {
    ref: branch,
    inputs: {
      company_name: companyName,
      got_ipo: opts.got_ipo || "none",
      applied: opts.applied || "none",
    },
  };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (res.status === 204) {
      const detail = opts.applied ? `applied -> ${opts.applied}` : `got_ipo -> ${opts.got_ipo}`;
      showToast(`Queued update: ${companyName} (${detail})`);
      return;
    }

    const text = await res.text();
    showToast(`Dispatch failed (${res.status}). ${text.slice(0, 120)}`, true);
  } catch (err) {
    showToast(`Dispatch error: ${err.message}`, true);
  }
}

els.search.addEventListener("input", render);
els.status.addEventListener("change", render);
els.refresh.addEventListener("click", () => {
  fetchRows().catch((e) => showToast(e.message, true));
});

fetchRows().catch((e) => showToast(e.message, true));
