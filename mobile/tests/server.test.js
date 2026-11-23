"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {get, request} = require("node:http");
const {createOdinServer} = require("../server");

test("standalone phone server mounts the app, preserves private access and retires old endpoints", async t => {
  const server = createOdinServer();
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const base = "http://127.0.0.1:" + server.address().port;
  const html = await fetch(base + "/");
  assert.equal(html.status, 200);
  assert.match(await html.text(), /Odin Control/);
  assert.equal((await fetch(base + "/app.js?v=test")).status, 200);
  assert.equal((await fetch(base + "/api/capabilities")).status, 200);
  for (const path of ["/api/relay", "/api/wake"]) {
    assert.equal((await new Promise(resolve => get(base + path, res => {
      res.resume();
      resolve(res.statusCode);
    }))), 410);
  }
  const status = await new Promise(resolve => {
    const req = request(base + "/api/session", {
      method:"POST", headers:{"Content-Type":"application/json","Content-Length":2}
    }, res => { res.resume(); resolve(res.statusCode); });
    req.end("{}");
  });
  assert.equal(status, 403);
  assert.equal((await fetch(base + "/package.json")).status, 404);
});
