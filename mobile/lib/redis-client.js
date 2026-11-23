"use strict";

async function withClient(action) {
  const url = process.env.ODIN_CHAT_REDIS_URL;
  if (!url || !url.startsWith("rediss://")) throw Error("Chat budget storage unavailable");
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

module.exports = {withClient};
