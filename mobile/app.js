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
    renderSecureState();
    if (privateState.connected && document.visibilityState === "visible") refreshRelay();
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


// Private bearer auth still uses an in-memory session. On explicit opt-in,
// only an AES-GCM encrypted copy may persist in local browser storage.
// The unlock password is never transmitted or stored, and is not a server key.
const privateState = {
  token:null, connected:false, cloud:false, diagnostics:false,
  history:[], cloudEvents:[], pending:null, capabilities:null, sending:false
};

function addChatLine(role,text) {
  const container=create("div","private-chat-line "+role);
  const label=create("div","private-chat-label",role==="user" ? "YOU → CLOUD AI"
    : role==="error" ? "CLOUD AI ERROR" : "CLOUD AI (API)");
  const bubble=create("div","private-chat-bubble",text);
  container.append(label,bubble);
  $("chatLog").append(container);
  $("chatLog").scrollTop=$("chatLog").scrollHeight;
  privateState.cloudEvents.push({
    id:"cloud-"+privateState.cloudEvents.length,
    sender:role==="user"?"you-cloud":role==="error"?"cloud-error":"cloud-ai",
    text,at:new Date().toISOString(),
    status:role==="user"?"Sent to cloud provider":
      role==="error"?"Cloud AI failed":"Cloud AI replied"
  });
  renderRelay();
}
function clearPrivateChat() {
  privateState.history=[];
  privateState.cloudEvents=[];
  renderRelay();
  $("chatLog").replaceChildren(create("div","empty-state",
    "New local tab conversation. Nothing was sent to Odin."));
  $("chatSendStatus").textContent="Conversation cleared";
}
async function authenticatedPost(path, body, token) {
  const response=await fetch(path,{
    method:"POST",cache:"no-store",
    headers:{"Accept":"application/json","Content-Type":"application/json",
      "Authorization":"Bearer "+token},
    body:JSON.stringify(body),
    signal:AbortSignal.timeout(path==="/api/chat"?50000:20000)
  });
  const data=await response.json().catch(()=>({error:"Unexpected response"}));
  if(!response.ok)throw Error(data.error || "Request rejected");
  return data;
}
async function checkCapabilities() {
  try {
    const response=await fetch("/api/capabilities",{cache:"no-store"});
    if(!response.ok)throw Error("Capabilities unavailable");
    privateState.capabilities=await response.json();
  } catch {
    privateState.capabilities=null;
  }
  renderSecureState();
}

function renderSecureState() {
  const p=privateState;
  const ready=p.connected;
  $("accessButton").textContent=ready?"Reconnect":"Connect";
  $("disconnectButton").disabled=!ready;
  $("cloudMessage").disabled=!(ready&&p.cloud);
  $("cloudSend").disabled=!(ready&&p.cloud)||p.sending;
  for (const button of document.querySelectorAll("[data-odin-action]")) {
    button.disabled=!(ready&&p.diagnostics)||p.sending;
  }
  if(!ready){
    const capabilities=p.capabilities;
    $("accessState").textContent=capabilities?.access_configured
      ? (savedVaultPresent() && !preferTokenForm
        ? "Enter your saved unlock password; the token stays encrypted on this device."
        : "Private server configured. Enter your access token to connect.")
      : "Private server token is not set. See setup instructions in GitHub.";
  } else {
    $("accessState").textContent="Authenticated for this tab. Cloud AI: "
      +(p.cloud?"ready":"needs server key")
      +" · Odin diagnostics: "+(p.diagnostics?"ready":"needs GitHub token");
  }
  $("cloudChatBanner").textContent=ready&&p.cloud
    ? "Cloud AI available · Separate from this ChatGPT app thread"
    : "Cloud AI chat not connected";
  if(p.pending){
    const id=p.pending.id;
    const req=state.data?.requests?.find(item=>item.id===id);
    const response=state.data?.receipts?.find(item=>item.id===id);
    let status="Awaiting Odin: "+p.pending.action+" · "+id.slice(-8);
    if(response)status="Odin receipt: "+response.status+" · "
      +readableAction(response.action)+" · "+time(response.checked_at);
    else if(req?.stage==="expired_without_response")
      status="Expired without Odin response · "+id.slice(-8);
    $("actionStatus").textContent=status;
  } else {
    $("actionStatus").textContent=ready&&p.diagnostics
      ? "Select a diagnostic. It will appear in the activity timeline."
      : "Remote diagnostics are locked until secure access and the GitHub token are configured.";
  }
}

let preferTokenForm=false;
function savedVaultPresent(){
  try{return OdinVault.hasSaved();}catch{return false;}
}
function renderVaultUI(){
  const saved=savedVaultPresent();
  const connected=privateState.connected;
  $("accessForm").hidden=connected || (saved && !preferTokenForm);
  $("vaultUnlockForm").hidden=connected || !saved || preferTokenForm;
  $("vaultSaveForm").hidden=!connected || (saved && !preferTokenForm);
  $("vaultManagement").hidden=!saved;
  $("vaultUseToken").hidden=connected;
  $("vaultUseToken").textContent=preferTokenForm
    ? "Use saved password" : "Use access token instead";
}
async function connectPrivateAccess(token){
  const result=await authenticatedPost("/api/session",{},token);
  if(!result.authenticated)throw Error("Authentication rejected");
  privateState.token=token;
  privateState.connected=true;
  privateState.cloud=result.cloud_chat_configured===true;
  privateState.diagnostics=result.device_diagnostics_configured===true;
  privateState.relay=result.private_relay_configured===true;
  privateState.paired=result.odin_pairing_configured===true;
  $("accessToken").value="";
  refreshRelay();
}
function lockPrivateAccess(){
  privateState.token=null;
  privateState.connected=false;
  privateState.cloud=false;
  privateState.diagnostics=false;
  privateState.relay=false;
  privateState.paired=false;
  $("accessToken").value="";
  $("vaultUnlockPassword").value="";
  $("vaultSavePassword").value="";
  relayLocal.messages=[];
  relayLocal.acknowledged.clear();
  relayLocal.error=null;
  relayLocal.notice=null;
  relayLocal.lastUpdated=null;
  clearPrivateChat();
}
$("accessForm").addEventListener("submit",async event=>{
  event.preventDefault();
  const token=$("accessToken").value.trim();
  if(token.length<32){
    $("accessState").textContent="Access token must contain at least 32 characters.";
    return;
  }
  $("accessButton").disabled=true;
  $("accessState").textContent="Verifying private access…";
  let status;
  try{
    await connectPrivateAccess(token);
    // A token entered manually can be saved under a new local password.
    preferTokenForm=true;
    status="Connected. Set an unlock password below to avoid pasting this token again.";
  }catch(error){
    lockPrivateAccess();
    status=error.message;
  }finally{
    $("accessButton").disabled=false;
    renderVaultUI();
    renderSecureState();
    $("accessState").textContent=status;
  }
});
$("vaultSaveForm").addEventListener("submit",async event=>{
  event.preventDefault();
  if(!privateState.connected||!privateState.token)return;
  const password=$("vaultSavePassword").value;
  $("vaultSaveButton").disabled=true;
  let status;
  try{
    await OdinVault.save(privateState.token,password);
    status="Encrypted access saved on this device. Next time, enter your password.";
    preferTokenForm=false;
  }catch{
    status="Could not save encrypted access. Your current session remains connected.";
  }finally{
    $("vaultSavePassword").value="";
    $("vaultSaveButton").disabled=false;
    renderVaultUI();
    $("accessState").textContent=status;
  }
});
$("vaultUnlockForm").addEventListener("submit",async event=>{
  event.preventDefault();
  const password=$("vaultUnlockPassword").value;
  $("vaultUnlockButton").disabled=true;
  $("accessState").textContent="Unlocking saved access…";
  let status;
  try{
    const token=await OdinVault.unlock(password);
    await connectPrivateAccess(token);
    preferTokenForm=false;
    status="Private session unlocked. Your password was never sent to the server.";
  }catch{
    lockPrivateAccess();
    status="Unlock failed. Check the password, or select Use access token instead.";
  }finally{
    $("vaultUnlockPassword").value="";
    $("vaultUnlockButton").disabled=false;
    renderVaultUI();
    renderSecureState();
    $("accessState").textContent=status;
  }
});
$("vaultUseToken").addEventListener("click",()=>{
  preferTokenForm=!preferTokenForm;
  renderVaultUI();
});
$("vaultForget").addEventListener("click",()=>{
  try{
    OdinVault.forget();
    preferTokenForm=false;
    renderVaultUI();
    $("accessState").textContent=privateState.connected
      ? "Encrypted saved access forgotten. Current session remains connected."
      : "Saved access forgotten. Enter your long access token to connect.";
  }catch{
    $("accessState").textContent="Could not clear saved access in this browser.";
  }
});
$("disconnectButton").addEventListener("click",()=>{
  lockPrivateAccess();
  preferTokenForm=false;
  renderSecureState();
  renderVaultUI();
});
$("cloudChatForm").addEventListener("submit",async event=>{
  event.preventDefault();
  if(!privateState.connected||!privateState.cloud||privateState.sending)return;
  const msg=$("cloudMessage").value.trim();
  if(!msg||msg.length>3000)return;
  privateState.sending=true;
  $("chatSendStatus").textContent="Waiting for the cloud AI provider…";
  $("cloudMessage").value="";
  addChatLine("user",msg);
  renderSecureState();
  try {
    const result=await authenticatedPost("/api/chat",{
      message:msg,history:privateState.history.slice(-8)
    },privateState.token);
    if(typeof result.answer!=="string"||result.source!=="openai-api")
      throw Error("Unexpected AI response");
    addChatLine("assistant",result.answer);
    privateState.history.push({role:"user",content:msg},{role:"assistant",content:result.answer});
    privateState.history=privateState.history.slice(-8);
    $("chatSendStatus").textContent="Cloud reply received · Not a device execution receipt";
  } catch(err){
    addChatLine("error","Chat unavailable: "+err.message);
    $("chatSendStatus").textContent="No validated AI response";
  } finally {
    privateState.sending=false;
    renderSecureState();
  }
});
$("clearChat").addEventListener("click",clearPrivateChat);
for(const button of document.querySelectorAll("[data-odin-action]")){
  button.addEventListener("click",async()=>{
    if(!privateState.connected||!privateState.diagnostics||privateState.sending)
      return;
    const action=button.dataset.odinAction;
    if(!Object.prototype.hasOwnProperty.call(ACTION_LABELS,action))return;
    const intensive=["checks","verify_release"].includes(action);
    if(intensive && !window.confirm(
      "Submit "+readableAction(action)+"? Odin will run its predefined tests, without modifying the repository."
    ))return;
    privateState.sending=true;
    $("actionStatus").textContent="Submitting "+readableAction(action)+" to GitHub…";
    renderSecureState();
    try {
      const result=await authenticatedPost("/api/command",{action},privateState.token);
      if(result.accepted!==true||typeof result.id!=="string")
        throw Error("Request not accepted");
      privateState.pending={id:result.id,action};
      $("actionStatus").textContent="Sent to GitHub · waiting for Odin's next poll";
      await refresh();
    }catch(err){
      $("actionStatus").textContent="Not submitted: "+err.message;
    }finally{
      privateState.sending=false;
      renderSecureState();
    }
  });
}
checkCapabilities();


// PRIVATE RELAY: phone <-> Odin, independent from the public GitHub mailbox.
// Status values are based on server-stored receipts, never inferred from a
// model prediction. No arbitrary device action can be transported here.
const relayLocal = {messages:[], acknowledged:new Set(), loading:false, sending:false, error:null, notice:null, lastUpdated:null};
const restartLocal = {id:null};
const RESTART_COMMANDS=new Set([
  "/restart-services", "/restart-all-services", "restart all services",
  "restart odin services", "restart odin"
]);
function isRestartCommand(text){
  return RESTART_COMMANDS.has(text.trim().toLowerCase().replace(/\s+/g," "));
}
const RELAY_FAILURE_LABELS=Object.freeze({
  ai_disabled:"AI is disabled on Odin; enable the local provider",
  credential_missing:"AI provider key is not available to the Odin relay",
  model_missing:"AI model name is not configured on Odin",
  invalid_provider:"Unsupported Odin AI provider selected",
  provider_unavailable:"Odin AI provider request failed",
  provider_timeout:"Odin AI request timed out",
  model_response_invalid:"Odin AI returned an invalid response",
  task_failed:"Verified read-only task failed on Odin",
  status_unavailable:"Odin AI status could not be checked"
});
function renderRelay(){
  const unlocked=privateState.connected && privateState.relay===true;
  $("relayMessage").disabled=!unlocked;
  $("relaySendButton").disabled=!unlocked||relayLocal.sending;
  $("restartAllButton").disabled=!unlocked||!privateState.paired||relayLocal.sending;
  let restartStatus=!unlocked?"Unlock private controls to restart Odin services.":
    !privateState.paired?"Odin device pairing is not configured.":
    "Ready to request a confirmed restart. Odin will send the final result.";
  if(unlocked&&restartLocal.id){
    const request=relayLocal.messages.find(m=>m.id===restartLocal.id);
    const response=relayLocal.messages.find(m=>m.sender==="odin"&&m.reply_to===restartLocal.id);
    if(response)restartStatus=response.text;
    else if(request?.status==="read")restartStatus=
      "Odin read the request. Restart/health checks may be in progress; awaiting final result.";
    else if(request?.status==="failed")restartStatus="Restart request failed before completion.";
    else restartStatus="Restart request queued. Waiting for Odin to receive it.";
  }
  $("restartAllStatus").textContent=restartStatus;
  const count=relayLocal.messages.filter(m=>m.sender==="odin"&&
    !["read","replied"].includes(m.status)).length;
  const badge=$("relayBadge");
  const inboxConfirmed=unlocked && !relayLocal.error && relayLocal.lastUpdated &&
    Date.now()-Date.parse(relayLocal.lastUpdated)<90000;
  badge.className="live-pill "+(inboxConfirmed?"good":"warn");
  badge.lastChild.textContent=!unlocked?"Private access locked"
    : relayLocal.error?"Inbox sync failed"
    : !inboxConfirmed?"Checking inbox"
    : (count?count+" unread":"Inbox checked");
  $("relayState").textContent=relayLocal.error || relayLocal.notice || (!privateState.connected
    ? "Connect your private session"
    : !privateState.relay?"Private storage unavailable"
    : !privateState.paired?"Odin has not been paired with its relay token"
    : relayLocal.lastUpdated ? "Last relay refresh "+time(relayLocal.lastUpdated)
    : "Checking private message inbox…");
  // Source labels prevent cloud API messages from being mistaken for
  // physical Odin replies or this exact ChatGPT application conversation.
  const events=[...relayLocal.messages,...privateState.cloudEvents]
    .sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)).slice(-35);
  replaceChildren("relayMessages",events.length
    ? events.map(m=>{
      const fromCloud=typeof m.sender==="string" &&
        (m.sender==="cloud-ai"||m.sender==="cloud-error"||m.sender==="you-cloud");
      const actor=m.sender==="odin"?"ODIN DEVICE":
        m.sender==="cloud-ai"?"CLOUD AI (API)":
        m.sender==="cloud-error"?"CLOUD AI ERROR":
        m.sender==="you-cloud"?"YOU → CLOUD AI":"YOU → ODIN";
      const row=create("div","relay-entry "+(fromCloud?"cloud":
        m.sender==="odin"?"odin":"iphone"));
      row.append(create("div","relay-entry-label",actor+" · "+time(m.at)));
      row.append(create("div","relay-entry-text",m.text));
      let stateLabel=m.status;
      if(!fromCloud && m.sender==="iphone" &&
         ["queued","delivered","read"].includes(m.status)){
        const age=Date.now()-Date.parse(m.at);
        if(m.status==="queued" && age>120000)stateLabel="Queued · Odin has not acknowledged (delayed)";
        else if(m.status==="read" && age>90000)stateLabel="Read by Odin · awaiting response";
        else if(m.status==="delivered")stateLabel="Delivered to Odin · awaiting processing";
      }
      if(m.status==="failed")stateLabel="Failed · "+
        (RELAY_FAILURE_LABELS[m.failure_reason]||
          "Review Odin relay status; no verified answer was returned");
      row.append(create("div","relay-entry-status",stateLabel));
      return row;
    }) : [create("div","empty-state","No messages or replies yet")]);
  document.title=count?"("+count+") Odin Control":"Odin — Control Center";
}
async function refreshRelay(){
  if(relayLocal.loading||!privateState.connected||!privateState.relay)return;
  relayLocal.loading=true;
  try{
    const resp=await fetch("/api/relay",{
      headers:{"Accept":"application/json",
        "Authorization":"Bearer "+privateState.token},
      cache:"no-store",signal:AbortSignal.timeout(12000)
    });
    const payload=await resp.json().catch(()=>({}));
    if(!resp.ok)throw Error(typeof payload.error==="string"
      ? payload.error.slice(0,150) : "Relay HTTP "+resp.status);
    if(!Array.isArray(payload.messages)||payload.source!=="private-odin-relay")
      throw Error("Unexpected relay response");
    relayLocal.messages=payload.messages;
    relayLocal.error=null;
    relayLocal.notice=null;
    relayLocal.lastUpdated=new Date().toISOString();
    renderRelay();
    const activeChat=$("view-chat").classList.contains("active") &&
      document.visibilityState==="visible";
    if(activeChat){
      for(const msg of payload.messages){
        if(msg.sender==="odin"&&msg.to==="iphone"&&msg.status==="queued" &&
           !relayLocal.acknowledged.has(msg.id)){
          relayLocal.acknowledged.add(msg.id);
          authenticatedPost("/api/relay",{
            type:"receipt",for:msg.id,state:"read"
          },privateState.token).catch(()=>{
            relayLocal.acknowledged.delete(msg.id);
          });
        }
      }
    }
  }catch(err){
    relayLocal.error="Message sync failed: "+err.message;
    renderRelay();
  }finally{relayLocal.loading=false;}
}
async function queuePrivateRelayMessage(text){
  if(!privateState.connected||!privateState.relay||relayLocal.sending)return;
  if(!text||text.length>2000)return;
  relayLocal.sending=true;
  relayLocal.error=null;
  relayLocal.notice="Sending securely…";
  renderRelay();
  try{
    const result=await authenticatedPost("/api/relay",{type:"message",text},privateState.token);
    if(typeof result.id!=="string")throw Error("Message not queued");
    if(isRestartCommand(text))restartLocal.id=result.id;
    $("relayMessage").value="";
    relayLocal.notice=isRestartCommand(text)
      ?"Restart request queued; Odin will reply after checking all services."
      :"Queued for Odin; waiting for a delivery receipt";
    await refreshRelay();
  }catch(err){
    relayLocal.error="Could not send: "+err.message;
    relayLocal.notice=null;
  }finally{
    relayLocal.sending=false;
    renderRelay();
  }
}
function confirmRestart(){
  return window.confirm("Restart all managed Odin services now? "+
    "This may interrupt active work and temporarily disconnect messages. "+
    "Odin will report service health after reconnecting.");
}
$("relaySendForm").addEventListener("submit",async event=>{
  event.preventDefault();
  const text=$("relayMessage").value.trim();
  if(isRestartCommand(text)&&!confirmRestart())return;
  await queuePrivateRelayMessage(text);
});
$("restartAllButton").addEventListener("click",async()=>{
  if(!privateState.connected||!privateState.relay||!privateState.paired)return;
  if(!confirmRestart())return;
  await queuePrivateRelayMessage("/restart-services");
});
for(const button of document.querySelectorAll("[data-relay-quick]")){
  button.addEventListener("click",()=>{
    if(!privateState.connected || !privateState.relay)return;
    $("relayMessage").value=button.dataset.relayQuick;
    $("relayMessage").focus();
  });
}
$("relayRefresh").addEventListener("click",refreshRelay);
setInterval(()=>{
  if(document.visibilityState==="visible")refreshRelay();
},15000);
renderVaultUI();
renderRelay();
