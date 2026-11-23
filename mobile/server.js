"use strict";

const {createServer} = require("node:http");
const {readFile} = require("node:fs/promises");
const {join} = require("node:path");

const assets = new Map([
  ["/", ["index.html", "text/html; charset=utf-8"]],
  ...["styles.css", "icon.svg", "manifest.webmanifest", "app.js", "app-update.js",
    "chat-route.js", "encrypted-chat.js", "local-tools.js", "ui-settings.js",
    "ui-settings.json", "vault.js"].map(name => ["/" + name, [name, {
      css:"text/css", svg:"image/svg+xml", webmanifest:"application/manifest+json",
      js:"text/javascript", json:"application/json"
    }[name.split(".").pop()]]])
]);
const routes = new Map(["browser-device", "capabilities", "chat", "command",
  "encrypted-chat", "session", "status"].map(name => ["/api/" + name, require("./api/" + name)]));

function json(res, status, value) {
  res.writeHead(status, {"Content-Type":"application/json; charset=utf-8", "Cache-Control":"no-store"});
  res.end(JSON.stringify(value));
}

async function handle(req, res) {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  res.setHeader("X-Frame-Options", "DENY");
  const path = req.url.split("?", 1)[0];
  const route = routes.get(path);
  if (route) {
    if (req.method === "POST") {
      const length = Number(req.headers["content-length"]);
      if (!Number.isSafeInteger(length) || length < 2 || length > 24576)
        return json(res, 400, {error:"Invalid request size"});
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      try { req.body = JSON.parse(Buffer.concat(chunks)); }
      catch { return json(res, 400, {error:"Invalid JSON"}); }
    }
    res.status = status => { res.statusCode = status; return res; };
    res.json = value => json(res, res.statusCode, value);
    return route(req, res);
  }

  if (path === "/api/relay" || path === "/api/wake")
    return json(res, 410, {error:"Retired endpoint. Use the private GitHub mailbox."});
  if (!assets.has(path)) return json(res, 404, {error:"Not found"});
  if (!["GET", "HEAD"].includes(req.method)) return json(res, 405, {error:"GET or HEAD required"});
  const [name, type] = assets.get(path);
  const body = await readFile(join(__dirname, name));
  res.writeHead(200, {"Content-Type":type, "Content-Length":body.length, "Cache-Control":"no-cache"});
  res.end(req.method === "HEAD" ? undefined : body);
}

function createOdinServer() {
  return createServer({requestTimeout:15000, headersTimeout:10000}, (req, res) => {
    handle(req, res).catch(() => {
      if (res.headersSent) res.destroy();
      else json(res, 500, {error:"Odin Control could not complete this request"});
    });
  });
}

if (require.main === module) {
  const port = Number(process.env.ODIN_MOBILE_PORT || "8780");
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw Error("Invalid ODIN_MOBILE_PORT");
  createOdinServer().listen(port, "127.0.0.1", () => console.log("Odin Control listening on 127.0.0.1:" + port));
}
module.exports = {createOdinServer};
