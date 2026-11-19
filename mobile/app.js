"use strict";

const state = { data: null, filter: "all", loading: false, error: null };
const $ = id => document.getElementById(id);
const SHA = /^[0-9a-f]{40}$/;
const ACTION_LABELS = {
  ping: "Bridge heartbeat",
  repo_status: "Repository inspection",
  services: "Service health",
  stage5_health: "AI server health",
  checks: "Run regression checks",
  verify_release: "Exact-revision verification",
  preflight_release: "Update preflight"
};
const TRUNCATE = 8;

function create(tag, className, textValue) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (textValue !== undefined) element.textContent = String(textValue);
  return element;
}
function replaceChildren(id, items) {
  const element = $(id);
  element.replaceChildren(...items);
}
function shortSha(value) {
  return typeof value === "string" && SHA.test(value)
    ? value.slice(0, TRUNCATE) : "Unknown";
}
function time(value) {
  const t = Date.parse(value);
  if (!Number.isFinite(t)) return "Unknown";
  const diff = Math.round((Date.now() - t) / 1000);
  if (diff >= 0 && diff < 60) return "just now";
  if (diff >= 60 && diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff >= 3600 && diff < 86400) return Math.floor(diff / 3600) + "h ago";
  return new Intl.DateTimeFormat(undefined, {month:"short",day:"numeric",hour:"numeric",minute:"2-digit"}).format(t);
}
function freshness(last) {
  const age = Date.now() - Date.parse(last);
  return Number.isFinite(age) && age >= 0 && age <= 15 * 60 * 1000;
}
function latest(action) {
  return state.data?.receipts?.find(item =>
    item.action === action && item.status === "complete") || null;
}
function reportedSha() {
  for (const item of state.data?.receipts || []) {
    if (item.status !== "complete") continue;
    const result = item.result || {};
    const sha = result.head_after || result.head || result.local_sha
      || result.head_before;
    if (SHA.test(sha || "")) return sha;
  }
  return null;
}
function currentCI() {
  const checks = state.data?.checks || [];
  return checks.find(item => item.head_sha === state.data?.main_sha)
    || checks[0] || null;
}
function readableAction(action) {
  return ACTION_LABELS[action] || "Odin request";
}
function statusText(entry) {
  const status = entry.stage || entry.status;
  if (status === "complete") return ["Complete", "good"];
  if (status === "waiting_for_odin") return ["Waiting for Odin", "wait"];
  if (status === "expired" || status === "expired_without_response") return ["Expired", "bad"];
  if (status === "rejected_or_failed") return ["Rejected / failed", "bad"];
  return ["Unknown", ""];
}

function renderHero() {
  const data = state.data;
  const receipt = data?.receipts?.[0];
  const pill = $("heroIndicator");
  pill.className = "live-pill neutral";
  if (state.error && !data) {
    $("heroTitle").textContent = "Telemetry unavailable";
    $("heroDetail").textContent = "Cannot reach GitHub status right now. No changes were made.";
    pill.querySelector(".status-dot").nextSibling.textContent = " Offline data";
    $("lastSeen").textContent = "Unknown";
    return;
  }
  if (!receipt) {
    $("heroTitle").textContent = "Awaiting device report";
    $("heroDetail").textContent = "No verified Odin receipt in the recent public mailbox.";
    pill.querySelector(".status-dot").nextSibling.textContent = " Unknown";
    $("lastSeen").textContent = "No recent receipt";
    return;
  }
  const isFresh = freshness(receipt.checked_at);
  const device = reportedSha();
  const mismatched = Boolean(device && device !== data.main_sha);
  const pending = data.requests.filter(item => item.stage === "waiting_for_odin");
  pill.className = "live-pill " + (isFresh ? "good" : "warn");
  pill.querySelector(".status-dot").nextSibling.textContent =
    isFresh ? " Recent response" : " Stale report";
  $("lastSeen").textContent = time(receipt.checked_at);
  if (!isFresh) {
    $("heroTitle").textContent = "Last seen " + time(receipt.checked_at);
    $("heroDetail").textContent = "Odin replied previously, but a fresh heartbeat hasn't been observed.";
  } else if (pending.length) {
    $("heroTitle").textContent = "Waiting for Odin";
    $("heroDetail").textContent = pending.length + " outstanding bridge request(s). Next poll may deliver a response.";
  } else if (mismatched) {
    $("heroTitle").textContent = "Odin is responding";
    $("heroDetail").textContent = "Device is on an older reported Git revision. No update will run without approval.";
  } else {
    $("heroTitle").textContent = "Bridge is responding";
    $("heroDetail").textContent = "Device receipts are arriving through GitHub. Conversational chat is not yet paired.";
  }
}

function renderMetrics() {
  const recent = state.data?.receipts?.[0];
  $("bridgeState").textContent = recent ? (freshness(recent.checked_at) ? "Responding" : "Stale") : "Unknown";
  const ci = currentCI();
  $("ciState").textContent =
    ci?.conclusion === "success" && ci.head_sha === state.data?.main_sha ? "Passed"
    : ci?.status === "in_progress" ? "Running"
    : ci?.conclusion === "failure" ? "Failed" : "Unknown";
  const services = latest("services")?.result || {};
  $("workerState").textContent =
    services["odin-task-worker"] === true ? "Running" :
    services["odin-task-worker"] === false ? "Stopped" : "Unknown";
  const health = latest("stage5_health")?.result || {};
  $("stage5State").textContent =
    health.reachable === true ? "Reachable" :
    health.reachable === false ? "Unreachable" : "Unknown";
  $("snapshotTime").textContent = state.data
    ? "Updated " + time(state.data.server_time) : "Waiting for update";
}

function step(index, title, info, status, label) {
  const item = create("div", "step");
  item.append(create("span", "step-marker " + (status || ""), index));
  const body = create("div", "step-body");
  const heading = create("div", "step-title", title);
  heading.append(create("span", "", label));
  body.append(heading, create("div", "step-detail", info));
  item.append(body);
  return item;
}
function renderSteps() {
  const d = state.data;
  if (!d) return;
  const ci = currentCI(), req = d.requests[0], receipt = d.receipts[0];
  const device = reportedSha();
  const verify = latest("verify_release");
  const verified = verify?.result?.verified === true
    && verify?.result?.head_after === d.main_sha;
  const steps = [
    step("01", "GitHub code", "Main " + shortSha(d.main_sha) +
      (ci?.head_sha === d.main_sha
        ? "; latest CI " + (ci.conclusion || ci.status)
        : "; CI for this revision not confirmed"),
      ci?.head_sha === d.main_sha && ci.conclusion === "success" ? "good" : "wait",
      ci?.conclusion === "success" && ci.head_sha === d.main_sha ? "Checked" : "Review"),
    step("02", "Request submitted",
      req ? readableAction(req.action) + " · " + time(req.created_at)
        : "No recent bridge request was found",
      req ? "good" : "wait", req ? "Received by GitHub" : "Idle"),
    step("03", "Odin response",
      receipt ? readableAction(receipt.action) + " · " + time(receipt.checked_at)
        : "No device receipt has been observed",
      receipt ? "good" : "wait", receipt ? "Receipt" : "Awaiting"),
    step("04", "Revision & test evidence",
      verified ? "Odin tested the exact current GitHub main revision"
        : device && device !== d.main_sha
        ? "Odin reported " + shortSha(device) + " while GitHub is " + shortSha(d.main_sha)
        : "No current exact-commit test confirmation",
      verified ? "good" : "wait", verified ? "Verified" : "Waiting"),
    step("05", "ChatGPT conversation relay",
      "Private chat transport is not paired. No private messages are exposed.",
      "wait", "Not linked")
  ];
  replaceChildren("steps", steps);
}

function sourceEvents() {
  const d = state.data;
  if (!d) return [];
  const events = [];
  for (const req of d.requests) {
    const [label, tone] = statusText(req);
    events.push({
      id: "request-" + req.id, type:"request", time:req.created_at,
      title:"Request · " + readableAction(req.action),
      sub: label + " · " + req.id.slice(-8),
      state: label, tone
    });
  }
  for (const receipt of d.receipts) {
    const [label, tone] = statusText(receipt);
    const result = receipt.result || {};
    let detail = label + " · receipt " + receipt.id.slice(-8);
    if (receipt.action === "verify_release") {
      detail = "Exact commit " + (result.verified === true ? "verified" : "not verified")
        + " · " + shortSha(result.head_after || result.head_before);
    } else if (receipt.action === "checks") {
      detail = "Stage 4: " + (result.stage4_passed === true ? "pass" : "unconfirmed")
        + " / Stage 5: " + (result.stage5_passed === true ? "pass" : "unconfirmed")
        + " / lint: " + (result.ruff_passed === true ? "pass" : "unconfirmed");
    } else if (receipt.action === "repo_status") {
      detail = "Device revision " + shortSha(result.head)
        + " · tracked " + (result.tracked_clean === true ? "clean" : "not clean");
    } else if (receipt.action === "stage5_health") {
      detail = result.reachable === true
        ? "AI server reachable" : "AI server not reachable in last check";
    }
    events.push({
      id:"odin-" + receipt.id,type:"odin",time:receipt.checked_at,
      title:"Odin · " + readableAction(receipt.action),
      sub:detail, state:label, tone
    });
  }
  for (const run of d.checks) {
    events.push({
      id:"github-" + run.id,type:"github",time:run.created_at,
      title:"GitHub · automated CI",
      sub:shortSha(run.head_sha) + " · " + (run.conclusion || run.status),
      state:run.conclusion === "success" ? "Passed"
        : run.conclusion === "failure" ? "Failed" : run.status,
      tone:run.conclusion === "success" ? "good"
        : run.conclusion === "failure" ? "bad" : "wait",
      url:run.url
    });
  }
  return events.filter(x => Number.isFinite(Date.parse(x.time)))
    .sort((a, b) => Date.parse(b.time) - Date.parse(a.time));
}
function eventNode(item) {
  const wrapper = create("div", "activity-row");
  wrapper.append(create("div", "activity-glyph " + item.type,
    item.type === "github" ? "⌘" : item.type === "odin" ? "◎" : "↗"));
  const main = create("div", "activity-main");
  const title = item.url ? create("a", "activity-title", item.title)
    : create("div", "activity-title", item.title);
  if (item.url) {
    title.href = item.url;
    title.target = "_blank";
    title.rel = "noopener noreferrer";
  }
  main.append(title, create("div", "activity-sub", item.sub));
  const meta = create("div", "activity-meta");
  meta.append(create("div", "", time(item.time)),
    create("div", "state-tag " + (item.tone || ""), item.state));
  wrapper.append(main, meta);
  return wrapper;
}
function renderActivity() {
  const events = sourceEvents();
  replaceChildren("overviewActivity", events.length
    ? events.slice(0,4).map(eventNode)
    : [create("div","empty-state","No recent public bridge events")]);
  const selected = state.filter === "all" ? events
    : events.filter(item => item.type === state.filter);
  replaceChildren("activityFeed", selected.length
    ? selected.slice(0,30).map(eventNode)
    : [create("div","empty-state","No events found for this filter")]);
}

function resultRow(name, value) {
  const item = create("div","test-row");
  item.append(create("div","test-label",name),
    create("div","test-result",
      value === true ? "Passed" : value === false ? "Failed" : "Not reported"));
  return item;
}
function renderSystem() {
  const d=state.data;
  if (!d) return;
  const device=reportedSha();
  $("repoSha").textContent=shortSha(d.main_sha);
  $("deviceSha").textContent=shortSha(device);
  $("alignment").textContent=!device ? "Unknown"
    : device === d.main_sha ? "Same revision" : "Update needed";
  const s=latest("services")?.result || {};
  $("syncState").textContent=s["odin-git-sync"] === true ? "Last check: running"
    : s["odin-git-sync"] === false ? "Last check: down" : "Not reported";
  $("workerDetail").textContent=s["odin-task-worker"] === true ? "Last check: running"
    : s["odin-task-worker"] === false ? "Last check: down" : "Not reported";
  const v=latest("verify_release");
  const c=v?.result?.checks || latest("checks")?.result || {};
  replaceChildren("testResults", [
    resultRow("Stage 4 regressions", c.stage4_passed),
    resultRow("Stage 5 regressions", c.stage5_passed),
    resultRow("Ruff lint", c.ruff_passed),
    resultRow("Exact Git revision", v?.result?.verified)
  ]);
}
function renderChat() {
  const receipt=state.data?.receipts?.[0];
  $("chatReceipt").textContent = receipt
    ? readableAction(receipt.action) + ": " + (
      receipt.status === "complete" ? "complete" : receipt.status
    ) + " · " + time(receipt.checked_at)
    : "No recent verified device response.";
}
function renderAll() {
  renderHero(); renderMetrics(); renderSteps();
  renderActivity(); renderSystem(); renderChat();
}
async function refresh() {
  if (state.loading) return;
  state.loading=true;
  $("refreshBtn").disabled=true;
  try {
    const response=await fetch("/api/status",{
      headers:{"Accept":"application/json"},cache:"no-store",
      signal:AbortSignal.timeout(12000)
    });
    if (!response.ok) throw new Error("Status endpoint unavailable");
    const data=await response.json();
    if (!SHA.test(data.main_sha) || !Array.isArray(data.receipts)
        || !Array.isArray(data.requests) || !Array.isArray(data.checks)) {
      throw new Error("Unexpected status data");
    }
    state.data=data;state.error=null;
  } catch (error) {
    state.error=error;
    if (!state.data) {
      $("bridgeState").textContent="Unavailable";
      $("ciState").textContent="Unknown";
      $("snapshotTime").textContent="Fetch failed";
    }
  } finally {
    state.loading=false;
    $("refreshBtn").disabled=false;
    renderAll();
  }
}

function navigate(tab) {
  for (const item of document.querySelectorAll("[data-tab]")) {
    const isActive=item.dataset.tab===tab;
    item.classList.toggle("active",isActive);
    if (isActive) item.setAttribute("aria-current","page");
    else item.removeAttribute("aria-current");
  }
  for (const page of document.querySelectorAll(".page")) {
    page.classList.toggle("active",page.id==="view-"+tab);
  }
  window.scrollTo({top:0,behavior:"instant"});
}
document.addEventListener("click",event=>{
  const tab=event.target.closest("[data-tab],[data-nav]");
  if (tab) navigate(tab.dataset.tab || tab.dataset.nav);
  const filter=event.target.closest("[data-filter]");
  if (filter) {
    state.filter=filter.dataset.filter;
    for (const item of document.querySelectorAll("[data-filter]")) {
      const active=item.dataset.filter===state.filter;
      item.classList.toggle("active",active);
      item.setAttribute("aria-pressed",String(active));
    }
    renderActivity();
  }
});
$("refreshBtn").addEventListener("click",refresh);
window.addEventListener("focus",()=>{ if (state.data) renderAll(); });
document.addEventListener("visibilitychange",()=>{
  if (document.visibilityState==="visible") refresh();
});
setInterval(()=>{
  if (document.visibilityState==="visible") refresh();
},60000);
refresh();
