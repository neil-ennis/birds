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
  const card = document.createElement("article");
  card.className = "report-card";
  const media = document.createElement("div");
  media.className = "card-media";
  const bird = report.leadingBird;
  if (bird?.photo) {
    const image = document.createElement("img");
    image.src = `./${bird.photo.image}`;
    image.alt = bird.common;
    image.loading = "lazy";
    image.decoding = "async";
    if (bird.photo.position) image.style.objectPosition = bird.photo.position;
    media.append(image);
  } else {
    media.classList.add("card-media-empty");
    const icon = document.createElement("span");
    icon.className = "card-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 15c3-1 5-4 7-7 1 4 4 6 9 7-4 1-6 3-8 6-1-3-4-5-8-6Z"/><path d="M13 8c2-3 4-4 6-4"/></svg>';
    media.append(icon);
  }
  const cardNumber = document.createElement("span");
  cardNumber.className = "card-number";
  cardNumber.textContent = String(number).padStart(2, "0");
  media.append(cardNumber);

  if (bird) {
    const info = document.createElement("div");
    info.className = "bird-info";
    const button = document.createElement("button");
    button.className = "bird-info-button";
    button.type = "button";
    button.textContent = "i";
    button.setAttribute("aria-label", `Bird and photo details for ${report.title}`);
    button.setAttribute("aria-haspopup", "dialog");
    button.setAttribute("aria-expanded", "false");
    const panel = document.createElement("div");
    panel.className = "bird-info-panel";
    panel.id = `bird-info-${number}`;
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Bird and photo details");
    panel.hidden = true;
    button.setAttribute("aria-controls", panel.id);
    const label = document.createElement("strong");
    label.textContent = bird.common;
    const detail = document.createElement("span");
    detail.textContent = `${Math.round(bird.confidence * 100)}% confidence · ${bird.detections} ${bird.detections === 1 ? "detection" : "detections"} · top of this report's Confidence list`;
    panel.append(label, detail);
    if (bird.photo) {
      const credit = document.createElement("span");
      credit.textContent = "Photo by ";
      const source = document.createElement("a");
      source.href = bird.photo.sourceUrl;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = bird.photo.author;
      const license = document.createElement("a");
      license.href = bird.photo.licenseUrl;
      license.target = "_blank";
      license.rel = "noopener noreferrer";
      license.textContent = bird.photo.license;
      credit.append(source, " / Wikimedia Commons · ", license, " · cropped for display");
      panel.append(credit);
    } else {
      const missing = document.createElement("span");
      missing.textContent = "Photo not yet available";
      panel.append(missing);
    }
    info.append(button, panel);
    info.addEventListener("pointerenter", event => {
      if (event.pointerType === "mouse") setBirdPanel(info, true);
    });
    info.addEventListener("pointerleave", () => {
      if (info.dataset.pinned !== "true" && !info.contains(document.activeElement)) setBirdPanel(info, false);
    });
    info.addEventListener("focusin", () => setBirdPanel(info, true));
    info.addEventListener("focusout", event => {
      if (!info.contains(event.relatedTarget) && info.dataset.pinned !== "true") setBirdPanel(info, false);
    });
    button.addEventListener("click", () => {
      const pin = info.dataset.pinned !== "true";
      closeBirdPanels(info);
      setBirdPanel(info, pin, pin);
    });
    media.append(info);
  }

  const content = document.createElement("div");
  content.className = "card-content";
  const date = document.createElement("p");
  date.className = "card-date";
  date.textContent = report.dateLabel || "Undated session";
  const title = document.createElement("h3");
  title.textContent = report.title;
  const session = document.createElement("p");
  session.className = "card-session";
  session.textContent = report.session;
  const bottom = document.createElement("a");
  bottom.className = "card-bottom";
  bottom.href = `./?report=${encodeURIComponent(report.id)}`;
  bottom.setAttribute("aria-label", `Open ${report.title}, ${report.session}, ${report.dateLabel}`);
  bottom.innerHTML = '<span>View report</span><span class="arrow" aria-hidden="true">→</span>';
  content.append(date, title, session, bottom);
  card.append(media, content);
  return card;
}

function setBirdPanel(info, open, pinned = info.dataset.pinned === "true") {
  info.querySelector(".bird-info-panel").hidden = !open;
  info.querySelector(".bird-info-button").setAttribute("aria-expanded", String(open));
  info.dataset.pinned = String(open && pinned);
}

function closeBirdPanels(except = null) {
  grid.querySelectorAll(".bird-info").forEach(info => {
    if (info !== except) setBirdPanel(info, false, false);
  });
}

document.addEventListener("click", event => {
  if (!event.target.closest(".bird-info")) closeBirdPanels();
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape") closeBirdPanels();
});

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
    let sizeObserver;
    frame.addEventListener("load", () => {
      sizeObserver?.disconnect();
      const body = frame.contentDocument?.body;
      if (!body) return;

      const resizeFrame = () => {
        frame.style.height = `${Math.ceil(body.scrollHeight) + 2}px`;
      };
      sizeObserver = new ResizeObserver(resizeFrame);
      sizeObserver.observe(body);
      resizeFrame();
    });
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
