async function fetchJSON(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

async function loadHealth() {
  const h = await fetchJSON("/health");
  document.getElementById("health-status").textContent =
    `Mode: ${h.execution_mode} | AI: ${h.enable_ai_filter} | News: ${h.enable_news_filter}`;
}

async function loadSummary() {
  const s = await fetchJSON("/api/analytics/summary");
  const container = document.getElementById("summary-cards");
  container.innerHTML = "";
  const items = [
    ["Win Rate", `${(s.win_rate * 100).toFixed(1)}%`],
    ["Total PnL", `$${s.total_pnl}`],
    ["Trades", s.total_trades],
    ["Open", s.open_positions],
    ["Max DD", `$${s.max_drawdown}`],
    ["Approved", s.decisions_approved],
    ["Rejected", s.decisions_rejected],
  ];
  for (const [label, value] of items) {
    const card = el("div", null, "card");
    card.appendChild(el("div", label, "label"));
    card.appendChild(el("div", value, "value"));
    container.appendChild(card);
  }
}

async function loadAlerts() {
  const rows = await fetchJSON("/api/alerts");
  const tbody = document.querySelector("#alerts-table tbody");
  tbody.innerHTML = "";
  rows.slice(0, 15).forEach((a) => {
    const tr = document.createElement("tr");
    const n = a.normalized || {};
    tr.innerHTML = `<td>${a.received_at?.slice(11, 19) || ""}</td><td>${a.ticker}</td><td>${n.bias || "-"}</td><td>${n.rsi ?? "-"}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadDecisions() {
  const rows = await fetchJSON("/api/decisions");
  const tbody = document.querySelector("#decisions-table tbody");
  tbody.innerHTML = "";
  rows.slice(0, 15).forEach((d) => {
    const tr = document.createElement("tr");
    const cls = d.decision === "APPROVE" ? "approve" : d.decision === "REJECT" ? "reject" : "";
    tr.innerHTML = `<td>${d.created_at?.slice(11, 19) || ""}</td><td class="${cls}">${d.decision}</td><td>${d.direction}</td><td>${(d.confidence * 100).toFixed(0)}%</td><td>${d.news_sentiment}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadPositions() {
  const rows = await fetchJSON("/api/positions");
  const tbody = document.querySelector("#positions-table tbody");
  tbody.innerHTML = "";
  rows.slice(0, 15).forEach((p) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${p.symbol}</td><td>${p.option_type}</td><td>${p.entry_price}</td><td>${p.pnl ?? "-"}</td><td>${p.status}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadAnalytics() {
  const rej = await fetchJSON("/api/analytics/rejections");
  const ul = document.getElementById("rejections-list");
  ul.innerHTML = "";
  Object.entries(rej).forEach(([k, v]) => {
    ul.appendChild(el("li", `${k}: ${v}`));
  });
  document.getElementById("tod-chart").textContent = JSON.stringify(
    await fetchJSON("/api/analytics/time-of-day"),
    null,
    2
  );
  document.getElementById("sentiment-heatmap").textContent = JSON.stringify(
    await fetchJSON("/api/analytics/sentiment-heatmap"),
    null,
    2
  );
  document.getElementById("regime-stats").textContent = JSON.stringify(
    await fetchJSON("/api/analytics/regime"),
    null,
    2
  );
}

async function refresh() {
  try {
    await loadHealth();
    await loadSummary();
    await loadAlerts();
    await loadDecisions();
    await loadPositions();
    await loadAnalytics();
  } catch (e) {
    console.error(e);
  }
}

refresh();
setInterval(refresh, 15000);
