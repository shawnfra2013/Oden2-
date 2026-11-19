"use strict";

// Read-only, sanitized device telemetry from the PUBLIC Odin GitHub mailbox.
// No GitHub credentials, private chats, or arbitrary device commands.
const REPO = "shawnfra2013/Oden2-";
const HEAD = "https://api.github.com/repos/" + REPO + "/branches/main";
const OUTBOX_HISTORY = "https://api.github.com/repos/" + REPO
  + "/commits?sha=odin-bridge-outbox&path=bridge/responses&per_page=20";
const INBOX_HISTORY = "https://api.github.com/repos/" + REPO
  + "/commits?sha=odin-bridge-inbox&path=bridge/requests&per_page=20";
const CI = "https://api.github.com/repos/" + REPO
  + "/actions/runs?branch=main&per_page=5";
const INBOX_RAW = "https://raw.githubusercontent.com/" + REPO
  + "/odin-bridge-inbox/bridge/requests/";
const RAW = "https://raw.githubusercontent.com/" + REPO
  + "/odin-bridge-outbox/bridge/responses/";
const ID = /^[0-9a-f]{32}$/;
const SHA = /^[0-9a-f]{40}$/;
const ACTIONS = new Set([
  "ping", "repo_status", "services", "stage5_health", "checks",
  "verify_release", "preflight_release", "odin_health", "worker_probe"
]);
const SAFE_KEYS = new Set([
  "alive", "bridge_version", "branch", "head", "tracked_clean",
  "untracked_count", "odin-git-sync", "odin-task-worker", "reachable",
  "ready", "ai_enabled", "stage4_passed", "stage5_passed", "ruff_passed",
  "expected_sha", "head_before", "head_after", "revision_matches",
  "branch_main", "tests_ran", "verified", "local_sha", "remote_main_sha",
  "fast_forward_possible", "target_matches", "untracked_collisions",
  "worker_heartbeat_age_s", "relay_poll_age_s", "queue_pending", "queue_running",
  "safe_to_attempt_pull", "applied", "checks", "stage5_reachable", "services", "sync_reason", "last_rollout"
]);

const HEALTH_SERVICES = [
  "odin-git-sync", "odin-task-worker", "odin-github-bridge", "odin-stage5", "odin-private-relay"
];
const SERVICE_STATES = new Set(["running", "down", "unknown", "not_configured"]);
const SYNC_REASONS = new Set([
  "unknown", "already_up_to_date", "source_updated", "source_updated_restart_not_automatic",
  "branch_not_main", "unexpected_origin", "tracked_changes", "invalid_local_revision",
  "invalid_remote_revision", "diverged", "ci_not_passed", "safe_pull_refused",
  "revision_mismatch", "update_check_failed"
]);

async function get(url) {
  const response = await fetch(url, {
    headers: {
      "Accept": "application/vnd.github+json",
      "User-Agent": "Odin-Mobile-ReadOnly",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    signal: AbortSignal.timeout(7000)
  });
  if (!response.ok) throw new Error("Upstream unavailable");
  return response.json();
}

function sanitize(entry, expectedId) {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)
      || entry.id !== expectedId || !ACTIONS.has(entry.action)
      || !["complete", "expired", "rejected_or_failed"].includes(entry.status)
      || !Number.isFinite(Date.parse(entry.checked_at))) {
    return null;
  }
  const source = entry.result && typeof entry.result === "object"
    && !Array.isArray(entry.result) ? entry.result : {};
  const result = {};
  for (const [key, value] of Object.entries(source)) {
    if (!SAFE_KEYS.has(key)) continue;
    if (key === "services") {
      if (entry.action !== "odin_health" || !value || typeof value !== "object") continue;
      const services = {};
      for (const name of HEALTH_SERVICES) {
        const status = value[name];
        if (!status || !SERVICE_STATES.has(status.state)) continue;
        const safe = {state: status.state};
        if (status.state === "running") {
          for (const field of ["pid", "uptime_s"]) {
            if (Number.isSafeInteger(status[field]) && status[field] >= 0
                && status[field] < 1000000000) safe[field] = status[field];
          }
        }
        services[name] = safe;
      }
      result.services = services;
    } else if (key === "last_rollout") {
      if (entry.action === "odin_health" && value && typeof value === "object"
          && SHA.test(value.revision || "") && typeof value.revision === "string"
          && typeof value.checked_at === "string" && Number.isFinite(Date.parse(value.checked_at))
          && ["pending", "verified", "unverified"].includes(value.reload_status)) {
        result.last_rollout = {revision: value.revision, checked_at: value.checked_at,
          reload_status: value.reload_status};
      }
    } else if (key === "sync_reason") {
      if (entry.action === "odin_health" && SYNC_REASONS.has(value)) result[key] = value;
    } else if (typeof value === "boolean") result[key] = value;
    else if (typeof value === "number" && Number.isSafeInteger(value)
             && value >= 0 && value < 1000000) result[key] = value;
    else if (typeof value === "string" &&
             ((key === "branch" && value === "main") ||
              (["head", "expected_sha", "head_before", "head_after",
                "local_sha", "remote_main_sha"].includes(key) && SHA.test(value)))) {
      result[key] = value;
    } else if (key === "checks" && value && typeof value === "object") {
      const checks = {};
      for (const k of ["stage4_passed", "stage5_passed", "ruff_passed"]) {
        if (typeof value[k] === "boolean") checks[k] = value[k];
      }
      result.checks = checks;
    }
  }
  return { id: entry.id, action: entry.action, status: entry.status,
    checked_at: entry.checked_at, result };
}

function requestId(message) {
  const matches = typeof message === "string"
    ? message.match(/[0-9a-f]{32}/g) : null;
  return matches ? matches.find(value => ID.test(value)) || null : null;
}

function sanitizeRequest(entry, expectedId) {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)
      || entry.id !== expectedId || !ACTIONS.has(entry.action)
      || !Number.isFinite(Date.parse(entry.created_at))
      || !Number.isFinite(Date.parse(entry.expires_at))) return null;
  return {
    id: expectedId, action: entry.action,
    created_at: entry.created_at, expires_at: entry.expires_at
  };
}

async function fetchRequest(id) {
  try {
    return sanitizeRequest(await get(INBOX_RAW + id + ".json"), id);
  } catch { return null; }
}

async function fetchReceipt(id) {
  try {
    const entry = await get(RAW + id + ".json");
    return sanitize(entry, id);
  } catch {
    return null;
  }
}

async function loadStatus() {
  const [main, outbox, inbox, workflow] = await Promise.all([
    get(HEAD), get(OUTBOX_HISTORY), get(INBOX_HISTORY), get(CI)
  ]);
  if (!SHA.test(main?.commit?.sha) ||
      !Array.isArray(outbox) || !Array.isArray(inbox)) {
    throw new Error("Unexpected upstream schema");
  }
  const responseIds = [];
  const requestIds = [];
  for (const commit of outbox) {
    const id = requestId(commit?.commit?.message);
    if (id && !responseIds.includes(id)) responseIds.push(id);
    if (responseIds.length >= 12) break;
  }
  for (const commit of inbox) {
    const id = requestId(commit?.commit?.message);
    if (id && !requestIds.includes(id)) requestIds.push(id);
    if (requestIds.length >= 12) break;
  }
  const [responseData, requestData] = await Promise.all([
    Promise.all(responseIds.map(fetchReceipt)),
    Promise.all(requestIds.map(fetchRequest))
  ]);
  const receipts = responseData.filter(Boolean)
    .sort((a, b) => Date.parse(b.checked_at) - Date.parse(a.checked_at));
  const requests = requestData.filter(Boolean)
    .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
    .map(req => {
      const receipt = receipts.find(item => item.id === req.id);
      return {
        ...req,
        stage: receipt?.status || (Date.parse(req.expires_at) < Date.now()
          ? "expired_without_response" : "waiting_for_odin"),
        response_at: receipt?.checked_at || null
      };
    });
  const runs = Array.isArray(workflow?.workflow_runs)
    ? workflow.workflow_runs : [];
  const checks = runs.slice(0, 3).map(run => ({
    id: String(run.id),
    status: ["queued", "in_progress", "completed", "waiting", "pending"]
      .includes(run.status) ? run.status : "unknown",
    conclusion: ["success", "failure", "cancelled", "skipped",
      "timed_out", "action_required"].includes(run.conclusion)
      ? run.conclusion : null,
    head_sha: SHA.test(run.head_sha) ? run.head_sha : null,
    created_at: Number.isFinite(Date.parse(run.created_at))
      ? run.created_at : null,
    url: typeof run.html_url === "string" &&
      /^https:\/\/github\.com\/shawnfra2013\/Oden2-\/actions\/runs\/\d+$/.test(run.html_url)
      ? run.html_url : null
  }));
  return {
    source: "public-github-read-only",
    server_time: new Date().toISOString(),
    main_sha: main.commit.sha,
    receipts, requests, checks,
    chatgpt_thread_connected: false,
    device_command_execution_enabled: false
  };
}

module.exports = async function handler(req, res) {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Cache-Control", "public, s-maxage=45, stale-while-revalidate=60");
  if (req.method !== "GET") {
    res.setHeader("Allow", "GET");
    return res.status(405).json({ error: "Method not allowed" });
  }
  try {
    return res.status(200).json(await loadStatus());
  } catch {
    return res.status(502).json({
      error: "Public GitHub telemetry is temporarily unavailable",
      source: "public-github-read-only"
    });
  }
};

module.exports._test = { sanitize, sanitizeRequest, requestId, loadStatus };
