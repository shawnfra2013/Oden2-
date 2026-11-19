"use strict";

const {createHmac, timingSafeEqual} = require("node:crypto");
const {deviceAuthorized} = require("../lib/relay");
const {configureResponse} = require("../lib/access");
const wake = require("../lib/wake");

function eventLane(event, data) {
  if (data?.repository?.full_name !== "shawnfra2013/Oden2-") return null;
  if (event === "push" && !data.deleted && data.ref === "refs/heads/odin-bridge-inbox")
    return "bridge";
  const run = data.workflow_run;
  if (event === "workflow_run" && data.action === "completed" && run?.name === "Odin Checks" &&
      run.event === "push" && run.head_branch === "main" && run.conclusion === "success")
    return "sync";
  return null;
}

module.exports = async function handler(req, res) {
  configureResponse(res);
  if (req.method === "GET") {
    if (!deviceAuthorized(req)) return res.status(403).end();
    if (!wake.lanes.has(req.query.lane)) return res.status(400).end();
    try { return res.status(200).json({wake: await wake.wait(req.query.lane)}); }
    catch { return res.status(503).end(); }
  }
  if (req.method !== "POST") return res.status(405).end();
  const secret = process.env.ODIN_WAKE_WEBHOOK_SECRET;
  const sig = req.headers["x-hub-signature-256"];
  if (!secret || secret.length < 32 || !/^sha256=[a-f0-9]{64}$/.test(sig || ""))
    return res.status(403).end();
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > 1024 * 1024) return res.status(413).end();
    chunks.push(Buffer.from(chunk));
  }
  const raw = Buffer.concat(chunks);
  const digest = createHmac("sha256", secret).update(raw).digest();
  if (!timingSafeEqual(digest, Buffer.from(sig.slice(7), "hex"))) return res.status(403).end();
  let data;
  try { data = JSON.parse(raw); } catch { return res.status(400).end(); }
  const lane = eventLane(req.headers["x-github-event"], data);
  if (!lane) return res.status(204).end();
  return res.status(await wake.notify(lane) ? 202 : 503).end();
};
module.exports.config = {api: {bodyParser: false}};
module.exports._test = {eventLane};
