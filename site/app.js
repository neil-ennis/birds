"use strict";

const catalogueView = document.getElementById("catalogue-view");
const viewerView = document.getElementById("viewer-view");
const errorView = document.getElementById("error-view");
const searchInput = document.getElementById("report-search");
const sortInput = document.getElementById("report-sort");
const grid = document.getElementById("report-grid");
const emptyState = document.getElementById("empty-state");
const status = document.getElementById("catalogue-status");

function showOnly(view) {
  catalogueView.hidden = view !== catalogueView;
  viewerView.hidden = view !== viewerView;
  errorView.hidden = view !== errorView;
}

function showError(title, description) {
  document.getElementById("error-title").textContent = title;
  document.getElementById("error-description").textContent = description;
  document.title = `${title} · Birdsong Archive`;
  showOnly(errorView);
}

function makeCard(report, number) {
  const card = document.createElement("a");
  card.className = "report-card";
  card.href = `./?report=${encodeURIComponent(report.id)}`;
  card.setAttribute("aria-label", `Open ${report.title}, ${report.session}, ${report.dateLabel}`);

  const top = document.createElement("div");
  top.className = "card-top";
  const icon = document.createElement("span");
  icon.className = "card-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 15c3-1 5-4 7-7 1 4 4 6 9 7-4 1-6 3-8 6-1-3-4-5-8-6Z"/><path d="M13 8c2-3 4-4 6-4"/></svg>';
  const cardNumber = document.createElement("span");
  cardNumber.className = "card-number";
  cardNumber.textContent = String(number).padStart(2, "0");
  top.append(icon, cardNumber);

  const date = document.createElement("p");
  date.className = "card-date";
  date.textContent = report.dateLabel || "Undated session";
  const title = document.createElement("h3");
  title.textContent = report.title;
  const session = document.createElement("p");
  session.className = "card-session";
  session.textContent = report.session;
  const bottom = document.createElement("span");
  bottom.className = "card-bottom";
  bottom.innerHTML = '<span>View report</span><span class="arrow" aria-hidden="true">→</span>';
  card.append(top, date, title, session, bottom);
  return card;
}

function renderCatalogue(reports) {
  const query = searchInput.value.trim().toLocaleLowerCase();
  const visible = reports.filter(report =>
    `${report.title} ${report.session} ${report.id} ${report.dateLabel}`.toLocaleLowerCase().includes(query)
  );
  const direction = sortInput.value === "oldest" ? 1 : -1;
  visible.sort((a, b) => sortInput.value === "name"
    ? a.title.localeCompare(b.title) || a.id.localeCompare(b.id)
    : direction * (a.sortDate.localeCompare(b.sortDate) || a.id.localeCompare(b.id))
  );

  const cards = document.createDocumentFragment();
  visible.forEach((report, index) => cards.append(makeCard(report, index + 1)));
  grid.replaceChildren(cards);
  emptyState.hidden = visible.length !== 0;
  status.textContent = `${visible.length} ${visible.length === 1 ? "recording" : "recordings"}${query ? " found" : ""}`;
}

async function init() {
  const requestedId = new URLSearchParams(window.location.search).get("report");
  let reports;
  try {
    const response = await fetch("./reports.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    reports = await response.json();
    if (!Array.isArray(reports)) throw new Error("Invalid report list");
  } catch (error) {
    console.error("Unable to load reports:", error);
    showError("The recordings could not be loaded.", "Please refresh the page or try again later.");
    return;
  }

  if (requestedId !== null) {
    const report = reports.find(item => item.id === requestedId);
    if (!report) {
      showError("This report could not be found.", "The link may be out of date.");
      return;
    }
    document.getElementById("viewer-title").textContent = report.title;
    document.getElementById("viewer-kicker").textContent = report.session;
    document.getElementById("viewer-details").textContent = [report.dateLabel, report.timeLabel].filter(Boolean).join(" · ");
    const frame = document.getElementById("report-frame");
    frame.title = `${report.title} ${report.session} report`;
    frame.src = report.url;
    document.getElementById("direct-link").href = report.url;
    document.title = `${report.title} · ${report.session} · Birdsong Archive`;
    showOnly(viewerView);
    return;
  }

  document.getElementById("report-count").textContent = reports.length;
  document.getElementById("report-count-label").textContent = reports.length === 1 ? "Report" : "Reports";
  const latest = [...reports].sort((a, b) => b.sortDate.localeCompare(a.sortDate))[0];
  document.getElementById("latest-date").textContent = latest ? latest.dateLabel : "—";
  searchInput.addEventListener("input", () => renderCatalogue(reports));
  sortInput.addEventListener("change", () => renderCatalogue(reports));
  renderCatalogue(reports);
  showOnly(catalogueView);
}

init();
