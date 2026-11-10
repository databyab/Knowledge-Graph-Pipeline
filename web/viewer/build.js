import {render} from "/viewer.js";

const form = document.querySelector("#build-form");
const text = document.querySelector("#source-text");
const context = document.querySelector("#context");
const entityConfig = document.querySelector("#entity-config");
const apiKey = document.querySelector("#api-key");
const counter = document.querySelector("#text-count");
const status = document.querySelector("#status");
const error = document.querySelector("#error");
const share = document.querySelector("#share");
const maxInputChars = Number(document.body.dataset.maxInputChars);

function updateCounter() {
  counter.textContent = `${text.value.length} / ${maxInputChars}`;
  text.setCustomValidity(text.value.length > maxInputChars ? "Text exceeds the maximum length." : "");
}

function parseEntityConfig(source) {
  const result = {aliases: {}};
  let section = "";
  for (const line of source.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    if (!line.startsWith(" ") && trimmed.endsWith(":")) {
      section = trimmed.slice(0, -1);
      continue;
    }
    const separator = trimmed.indexOf(":");
    if (separator < 1) continue;
    const key = trimmed.slice(0, separator).trim();
    const value = trimmed.slice(separator + 1).trim().replace(/^['"]|['"]$/g, "");
    if (section === "aliases") result.aliases[key] = value;
    else if (key === "context") result.context = value || null;
  }
  return result;
}

async function readEntityConfig() {
  if (!entityConfig.files.length) return undefined;
  return parseEntityConfig(await entityConfig.files[0].text());
}

function showError() {
  error.textContent = "The graph could not be built. Check the API key and try again.";
}

async function pollGraph(id, key) {
  const deadline = Date.now() + 5 * 60 * 1000;
  while (Date.now() < deadline) {
    const response = await fetch(`/v1/graphs/${encodeURIComponent(id)}`, {headers: {"X-API-Key": key}});
    if (!response.ok) throw new Error("status request failed");
    const result = await response.json();
    status.textContent = result.status;
    if (result.status === "completed") return result;
    if (!["queued", "running"].includes(result.status)) throw new Error("build failed");
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("build timed out");
}

async function submit(event) {
  event.preventDefault();
  error.textContent = "";
  share.textContent = "";
  status.textContent = "queued";
  const key = apiKey.value;
  try {
    const payload = {text: text.value, context: context.value || undefined, entity_config: await readEntityConfig()};
    const response = await fetch("/v1/graphs", {method: "POST", headers: {"Content-Type": "application/json", "X-API-Key": key}, body: JSON.stringify(payload)});
    if (!response.ok) throw new Error("build request failed");
    const result = await pollGraph((await response.json()).id, key);
    render(result.graph, document);
    const link = document.createElement("a");
    link.href = `/g/${encodeURIComponent(result.share_id)}`;
    link.textContent = `Share graph: ${window.location.origin}${link.pathname}`;
    share.replaceChildren(link);
    text.value = "";
    apiKey.value = "";
    updateCounter();
  } catch (_error) {
    status.textContent = "failed";
    showError();
  }
}

text.addEventListener("input", updateCounter);
form.addEventListener("submit", submit);
updateCounter();
