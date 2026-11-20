"use strict";
const {createHash, timingSafeEqual} = require("node:crypto");

const ORIGIN = "https://odin-control.vercel.app";
function configureResponse(res) {
  res.setHeader("Cache-Control", "no-store, private");
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("Vary", "Authorization, Origin, Cookie");
}
function authorized(req) {
  if (!req.headers.authorization && require("./browser-device").approved(req)) return true;
  const secret = process.env.ODIN_CONTROL_ACCESS_TOKEN;
  if (typeof secret !== "string" || secret.length < 32 || secret.length > 256) return false;
  const header = req.headers.authorization;
  if (typeof header !== "string" || !/^Bearer [A-Za-z0-9._~-]{32,256}$/.test(header)) return false;
  const provided = header.slice(7);
  const sha = value => createHash("sha256").update(value).digest();
  return timingSafeEqual(sha(secret), sha(provided));
}
function validOrigin(req) {
  return req.headers.origin === ORIGIN;
}
function validBody(req, size=24576) {
  const len = Number(req.headers["content-length"]);
  if (!Number.isSafeInteger(len) || len < 2 || len > size) return false;
  const type = String(req.headers["content-type"] || "").split(";")[0].trim().toLowerCase();
  return type === "application/json" && req.body && typeof req.body === "object"
    && !Array.isArray(req.body);
}
function protect(req,res) {
  configureResponse(res);
  if (req.method !== "POST") {
    res.setHeader("Allow","POST");
    res.status(405).json({error:"POST required"});
    return false;
  }
  if (!validOrigin(req) || !authorized(req)) {
    res.status(403).json({error:"Private access not configured or not authorized"});
    return false;
  }
  if (!validBody(req)) {
    res.status(400).json({error:"Invalid request"});
    return false;
  }
  return true;
}
module.exports={ORIGIN,configureResponse,authorized,validOrigin,validBody,protect};