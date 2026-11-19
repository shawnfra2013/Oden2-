"use strict";

// Read-only, sanitized device telemetry from the PUBLIC Odin GitHub mailbox.
// No GitHub credentials, private chats, or arbitrary device commands.
const REPO = "shawnfra2013/Oden2-";
const HEAD = "https://api.github.com/repos/" + REPO + "/branches/main";
const HISTORY = "https://api.github.com/repos/" + REPO
  + "/commits?sha=odin-bridge-outbox&per_page=20";
const RAW = "https://raw.githubusercontent.com/" + REPO
  + "/odin-bridge-outbox/bridge/responses/";
const ID = /^[0-9a-f]{32}$/;
const SHA = /^[0-9a-f]{40}$/;
const ACTIONS = new Set([
  "ping", "repo_status", "services", "stage5_health", "checks",
  "verify_release", "preflight_release"
]);
const SAFE_KEYS = new Set([
  "alive", "bridge_version", "branch", "head", "tracked_clean",
  "untracked_count", "odin-git-sync", "odin-task-worker", "reachable",
  "ready", "ai_enabled", "stage4_passed", "stage5_passed", "ruff_passed",
  "expected_sha", "head_before", "head_after", "revision_matches",
  "branch_main", "tests_ran", "verified", "local_sha", "remote_main_sha",
  "fast_forward_possible", "target_matches", "untracked_collisions",
  "safe_to_attempt_pull", "applied"
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
    if (typeof value === "boolean") result[key] = value;
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

async function fetchReceipt(id) {
  try {
    const entry = await get(RAW + id + ".json");
    return sanitize(entry, id);
  } catch {
    return null;
  }
}

async function loadStatus() {
  const [main, commits] = await Promise.all([get(HEAD), get(HISTORY)]);
  if (!SHA.test(main?.commit?.sha) || !Array.isArray(commits)) {
    throw new Error("Unexpected upstream schema");
  }
  const ids = [];
  for (const commit of commits) {
    const match = /^Odin bridge response ([0-9a-f]{32})$/.exec(commit?.commit?.message || "");
    if (match && ID.test(match[1]) && !ids.includes(match[1])) ids.push(match[1]);
    if (ids.length >= 10) break;
  }
  const receipts = (await Promise.all(ids.map(fetchReceipt))).filter(Boolean)
    .sort((a, b) => Date.parse(b.checked_at) - Date.parse(a.checked_at));
  return {
    source: "public-github-read-only",
    server_time: new Date().toISOString(),
    main_sha: main.commit.sha,
    receipts
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

module.exports._test = { sanitize, loadStatus };
