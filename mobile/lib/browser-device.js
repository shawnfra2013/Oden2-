"use strict";
const {createHash, randomBytes} = require("node:crypto");
const NAME = "__Host-odin-device";
function secretFrom(req) {
  const cookies = String(req.headers.cookie || "").split(";").map(x => x.trim());
  const values = cookies.filter(x => x.startsWith(NAME + "="));
  if (values.length !== 1) return null;
  const value = values[0].slice(NAME.length + 1);
  return /^[a-f0-9]{64}$/.test(value) ? value : null;
}
function fingerprint(secret) {
  return createHash("sha256").update("odin-control-v1:" + secret).digest("hex").slice(0,32);
}
function approved(req) {
  const secret = secretFrom(req);
  return Boolean(secret && fingerprint(secret) === process.env.ODIN_TRUSTED_BROWSER_ID);
}
function cookie(res,value,age) {
  res.setHeader("Set-Cookie", NAME+"="+value+"; Path=/; Max-Age="+age+"; Secure; HttpOnly; SameSite=Strict");
}
function enroll(req,res) {
  const secret = secretFrom(req) || randomBytes(32).toString("hex");
  cookie(res,secret,31536000);
  return fingerprint(secret);
}
module.exports = {approved,enroll,forget:res=>cookie(res,"",0)};
