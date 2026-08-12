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

    const companyTd = document.createElement("td");
    const cBtn = document.createElement("button");
    cBtn.className = "company-btn";
    cBtn.textContent = norm(row.company_name) || "(unknown)";
    cBtn.title = "Click to set allotment status (yes/no/clear)";
    cBtn.addEventListener("click", () => {
      const answer = window.prompt(
        `Set allotment for ${row.company_name}. Type: yes / no / clear / source`,
        "yes"
      );
      const cmd = norm(answer).toLowerCase();
      if (!cmd) return;
      if (cmd === "source") {
        const u = norm(row.source_url);
        if (u) window.open(u, "_blank", "noopener,noreferrer");
        return;
      }
      if (!["yes", "no", "clear"].includes(cmd)) {
        showToast("Use yes, no, clear, or source", true);
        return;
      }
      updateAllotment(row.company_name, cmd);
    });
    companyTd.appendChild(cBtn);

    const statusTd = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `status ${statusClass(row.ipo_status)}`;
    badge.textContent = norm(row.ipo_status) || "Unknown";
    statusTd.appendChild(badge);

    const gotTd = document.createElement("td");
    const gotWrap = document.createElement("div");
    gotWrap.className = "action-cell";
    const got = norm(row.got_ipo).toLowerCase();

    if (got === "yes" || got === "no") {
      const fixed = document.createElement("span");
      fixed.className = `got-fixed ${got}`;
      fixed.textContent = got === "yes" ? "Yes" : "No";
      gotWrap.appendChild(fixed);
    } else {
      const yesBtn = document.createElement("button");
      yesBtn.className = "btn-yes";
      yesBtn.textContent = "Got";
      yesBtn.addEventListener("click", () => updateAllotment(row.company_name, "yes"));

      const noBtn = document.createElement("button");
      noBtn.className = "btn-no";
      noBtn.textContent = "No";
      noBtn.addEventListener("click", () => updateAllotment(row.company_name, "no"));

      gotWrap.appendChild(yesBtn);
      gotWrap.appendChild(noBtn);
    }
    gotTd.appendChild(gotWrap);

    const openTd = document.createElement("td");
    openTd.textContent = norm(row.open_date);
    const closeTd = document.createElement("td");
    closeTd.textContent = norm(row.close_date);
    const allotTd = document.createElement("td");
    allotTd.textContent = norm(row.allotment_date);
    const listTd = document.createElement("td");
    listTd.textContent = norm(row.listing_date);
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

async function updateAllotment(companyName, gotIpo) {
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
      got_ipo: gotIpo,
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
      showToast(`Queued update: ${companyName} -> ${gotIpo}`);
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
