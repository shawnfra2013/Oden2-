"use strict";

const lanes = new Set(["relay", "bridge", "sync"]);

async function withClient(action) {
  const url = process.env.ODIN_WAKE_REDIS_URL;
  if (!url || !url.startsWith("rediss://")) throw Error("Wake transport unavailable");
  const {createClient} = require("redis");
  const client = createClient({url, socket: {connectTimeout: 2500, reconnectStrategy: false}});
  client.on("error", () => {});
  try {
    await client.connect();
    return await action(client);
  } finally {
    if (client.isOpen) await client.disconnect();
  }
}

function key(lane) {
  if (!lanes.has(lane)) throw Error("Invalid wake lane");
  return "odin:wake:v1:" + lane;
}

async function signal(lane) {
  const name = key(lane);
  // Coalesce hints while the device is offline. The queues own the actual work.
  await withClient(client => client.multi().lPush(name, "1").lTrim(name, 0, 0)
    .expire(name, 600).exec());
}

async function notify(lane) {
  try { await signal(lane); return true; } catch { return false; }
}

async function wait(lane) {
  const name = key(lane);
  return Boolean(await withClient(client => client.blPop(name, 20)));
}

module.exports = {lanes, notify, wait, withClient};
