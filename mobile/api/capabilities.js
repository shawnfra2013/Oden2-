"use strict";
const {configureResponse} = require("../lib/access");
module.exports = function handler(req,res) {
  configureResponse(res);
  if (req.method !== "GET") {
    res.setHeader("Allow","GET");
    return res.status(405).json({error:"GET required"});
  }
  const access = typeof process.env.ODIN_CONTROL_ACCESS_TOKEN === "string"
    && process.env.ODIN_CONTROL_ACCESS_TOKEN.length >= 32;
  const model = process.env.ODIN_OPENAI_MODEL || "";
  const ai = Boolean(process.env.OPENAI_API_KEY && /^[A-Za-z0-9._-]{1,100}$/.test(model));
  const github = Boolean(process.env.ODIN_GITHUB_TOKEN);
  return res.status(200).json({
    source:"odin-control-server",
    access_configured:access,
    cloud_chat_configured:access && ai,
    device_diagnostics_configured:access && github,
    private_odin_conversation_connected:false,
    arbitrary_shell_enabled:false,
    exact_chatgpt_thread_connected:false
  });
};