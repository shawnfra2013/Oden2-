"use strict";
const {protect} = require("../lib/access");
const base = "https://api.github.com/repos/shawnfra2013/Odin-private-bridge/contents/bridge/";
const idPattern = /^[0-9a-f]{32}$/;
const sealedPattern = /^[A-Za-z0-9+/]+={0,2}$/;
module.exports = async function handler(req, res) {
  if (!protect(req, res)) return;
  const {id, sealed} = req.body;
  const keys = Object.keys(req.body).sort().join(",");
  if (typeof id !== "string" || !idPattern.test(id) || !["id", "id,sealed"].includes(keys))
    return res.status(400).json({error:"Invalid message"});
  const token = process.env.ODIN_PRIVATE_MAILBOX_TOKEN;
  if (!token) return res.status(503).json({error:"Private mailbox unavailable"});
  const headers = {Authorization:"Bearer "+token, Accept:"application/vnd.github+json"};
  const get = (folder, branch) => fetch(base+folder+"/"+id+".json?ref="+branch, {
    headers, signal:AbortSignal.timeout(8000)
  });
  try {
    if (keys === "id,sealed") {
      if (typeof sealed !== "string" || sealed.length < 40 || sealed.length > 16040 || !sealedPattern.test(sealed))
        return res.status(400).json({error:"Invalid ciphertext"});
      const now = Date.now();
      const stamp = t => new Date(t).toISOString().replace(/\.\d{3}Z$/, "Z");
      const content = {version:1, action:"encrypted_chat", id, sealed, created_at:stamp(now), expires_at:stamp(now+900000)};
      const saved = await fetch(base+"requests/"+id+".json", {method:"PUT", headers,
        body:JSON.stringify({branch:"odin-bridge-inbox",message:"Encrypted chat "+id,
          content:Buffer.from(JSON.stringify(content)).toString("base64")}),signal:AbortSignal.timeout(10000)});
      if (!saved.ok) {
        const prior = await get("requests","odin-bridge-inbox");
        if (!prior.ok) throw Error();
        const item = JSON.parse(Buffer.from((await prior.json()).content,"base64"));
        if (item.id !== id || item.action !== "encrypted_chat" || item.sealed !== sealed) throw Error();
      }
      return res.status(202).json({queued:true});
    }
    const response = await get("responses","odin-bridge-outbox");
    if (response.status === 404) return res.status(200).json({pending:true});
    if (!response.ok) throw Error();
    const receipt = JSON.parse(Buffer.from((await response.json()).content,"base64"));
    if (receipt.id !== id || receipt.action !== "encrypted_chat") throw Error();
    if (["expired", "rejected_or_failed", "unverified"].includes(receipt.status)) {
      // Return only a fixed failure category; never expose the device result or ciphertext.
      return res.status(200).json({pending:false,failed:true,state:receipt.status});
    }
    if (receipt.status !== "complete" ||
        typeof receipt.result?.sealed !== "string" || receipt.result.sealed.length > 43000) throw Error();
    return res.status(200).json({sealed:receipt.result.sealed});
  } catch {
    return res.status(502).json({error:"Encrypted message delivery unconfirmed"});
  }
};
