"use strict";

const articlesElement = document.querySelector("#article-list");
const emptyElement = document.querySelector("#empty-state");
const errorElement = document.querySelector("#error-state");
const searchElement = document.querySelector("#search");
const serviceElement = document.querySelector("#service-filter");
const categoryElement = document.querySelector("#category-filter");
const sourceElement = document.querySelector("#source-filter");
const sortElement = document.querySelector("#sort-order");
const resultCountElement = document.querySelector("#result-count");
let articles = [];

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function validLink(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

function formatDate(value) {
  if (!value) return "Date unavailable";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "Date unavailable";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeZone: "UTC" }).format(parsed);
}

function categoryClass(category) {
  return `badge-${String(category || "general-announcement").toLowerCase().replaceAll(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`;
}

function createCard(article) {
  const card = element("article", "article-card");
  const meta = element("div", "card-meta");
  meta.append(element("span", `badge ${categoryClass(article.category)}`, article.category || "General Announcement"));
  meta.append(element("span", "service-tag", article.service || "AWS service"));
  meta.append(element("span", "card-source", article.source || "AWS"));
  meta.append(element("span", "card-date", formatDate(article.published)));
  card.append(meta);

  const title = element("h3", "article-title");
  const link = element("a", "", article.title || "Untitled announcement");
  if (validLink(article.url)) {
    link.href = article.url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
  } else {
    link.removeAttribute("href");
  }
  title.append(link);
  card.append(title);
  if (article.summary) card.append(element("p", "article-summary", article.summary));
  return card;
}

function sortArticles(items) {
  const sorted = [...items];
  const mode = sortElement.value;
  sorted.sort((left, right) => {
    if (mode === "title") return (left.title || "").localeCompare(right.title || "");
    const dateDifference = Date.parse(right.published || "") - Date.parse(left.published || "");
    if (mode === "oldest") return -dateDifference;
    return dateDifference;
  });
  return sorted;
}

function renderHighlights(containerId, category) {
  const container = document.querySelector(containerId);
  container.replaceChildren();
  const matches = sortArticles(articles.filter((article) => article.category === category)).slice(0, 4);
  if (!matches.length) {
    container.append(element("p", "highlight-empty", "No matching updates yet."));
    return;
  }
  for (const article of matches) {
    const link = element("a", "highlight-link");
    link.append(element("strong", "", article.title || "Untitled announcement"));
    link.append(element("span", "", `${article.source || "AWS"} · ${formatDate(article.published)}`));
    if (validLink(article.url)) {
      link.href = article.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    }
    container.append(link);
  }
}

function render() {
  const query = searchElement.value.trim().toLocaleLowerCase();
  const category = categoryElement.value;
  const source = sourceElement.value;
  const service = serviceElement.value;
  const matches = sortArticles(articles.filter((article) => {
    const searchable = `${article.title || ""} ${article.summary || ""} ${article.source || ""} ${article.category || ""}`.toLocaleLowerCase();
    return (!query || searchable.includes(query))
      && (!category || article.category === category)
      && (!source || article.source === source)
      && (!service || article.service === service);
  }));

  articlesElement.replaceChildren(...matches.map(createCard));
  emptyElement.hidden = matches.length > 0;
  resultCountElement.textContent = `${matches.length} ${matches.length === 1 ? "result" : "results"}`;
}

function updateOverview() {
  const now = Date.now();
  const weekAgo = now - 7 * 24 * 60 * 60 * 1000;
  const lastWeek = articles.filter((article) => {
    const timestamp = Date.parse(article.published || "");
    return Number.isFinite(timestamp) && timestamp >= weekAgo && timestamp <= now;
  }).length;
  document.querySelector("#stat-total").textContent = articles.length.toLocaleString();
  document.querySelector("#stat-week").textContent = lastWeek.toLocaleString();
  document.querySelector("#stat-security").textContent = articles.filter((article) => article.category === "Security").length.toLocaleString();
}

async function loadArticles() {
  const candidates = ["./data/articles.json", "../data/articles.json"];
  let response;
  for (const path of candidates) {
    try {
      response = await fetch(path, { cache: "no-store" });
      if (response.ok) break;
    } catch {
      response = undefined;
    }
  }
  if (!response || !response.ok) throw new Error("Could not load the announcement dataset.");
  const payload = await response.json();
  if (!Array.isArray(payload)) throw new Error("The announcement dataset has an invalid format.");
  articles = payload;

  const services = [...new Set(articles.map((article) => article.service).filter(Boolean))].sort();
  for (const service of services) serviceElement.add(new Option(service, service));
  const sources = [...new Set(articles.map((article) => article.source).filter(Boolean))].sort();
  for (const source of sources) sourceElement.add(new Option(source, source));

  const latest = articles.map((article) => Date.parse(article.published || "")).filter(Number.isFinite).sort((a, b) => b - a)[0];
  document.querySelector("#last-updated").textContent = latest
    ? `Latest announcement published ${formatDate(new Date(latest).toISOString())} · ${articles.length.toLocaleString()} tracked`
    : `${articles.length.toLocaleString()} tracked announcements`;

  updateOverview();
  render();
  renderHighlights("#security-list", "Security");
  renderHighlights("#release-list", "Release");
  renderHighlights("#upgrade-list", "Upgrade");
}

for (const control of [searchElement, serviceElement, categoryElement, sourceElement, sortElement]) {
  control.addEventListener("input", render);
  control.addEventListener("change", render);
}

loadArticles().catch((error) => {
  document.querySelector("#last-updated").textContent = "Announcement data is unavailable.";
  errorElement.textContent = error.message;
  errorElement.hidden = false;
  emptyElement.hidden = true;
  resultCountElement.textContent = "";
});
