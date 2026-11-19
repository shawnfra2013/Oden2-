"use strict";
const {protect} = require("../lib/access");
const {openAiApiKey} = require("../lib/openai-config");
const MODEL = /^[a-zA-Z0-9._-]{1,100}$/;
function validate(data) {
  if (Object.keys(data).some(k=>!["message","history"].includes(k))
      || typeof data.message!=="string"
      || !data.message.trim()
      || data.message.length>3000
      || !Array.isArray(data.history) || data.history.length>8) return null;
  if (data.history.some(m=>!m || typeof m!=="object" || Array.isArray(m)
    || Object.keys(m).sort().join(",")!=="content,role"
    || !["user","assistant"].includes(m.role)
    || typeof m.content!=="string" || m.content.length>2000)) return null;
  return [
    ...data.history.map(m=>({role:m.role,content:m.content})),
    {role:"user",content:data.message.trim()}
  ];
}
module.exports=async function handler(req,res) {
  if (!protect(req,res)) return;
  const key=openAiApiKey();
  const model=process.env.ODIN_OPENAI_MODEL;
  if (!key || !MODEL.test(model||"")) {
    return res.status(503).json({error:"Cloud chat not configured; add a fresh API key and model in Vercel settings"});
  }
  const input=validate(req.body);
  if (!input) return res.status(400).json({error:"Invalid conversation or message"});
  const payload={
    model,input,store:false,max_output_tokens:700,
    instructions:"You are the Odin Control cloud AI assistant. You are an independent API conversation, NOT the user's exact ChatGPT app conversation and NOT an active Odin device process. Guide the user about their AYN Odin 2 AI workstation and its public GitHub repository shawnfra2013/Oden2-. Never claim that you have connected to Odin, pushed code, tested, restarted services or approved a device action unless the user supplies a separate verified receipt. Never request API keys in the chat. Device operations require a separate explicitly confirmed diagnostic action."
  };
  try {
    const response=await fetch("https://api.openai.com/v1/responses",{
      method:"POST",
      headers:{"Authorization":"Bearer "+key,"Content-Type":"application/json"},
      body:JSON.stringify(payload),signal:AbortSignal.timeout(40000)
    });
    if(!response.ok)return res.status(502).json({error:"Model provider unavailable or account not configured"});
    const raw=await response.text();
    if(raw.length>1048576)return res.status(502).json({error:"Oversized provider response"});
    const data=JSON.parse(raw);
    const answer=(data.output||[]).flatMap(item=>
      item?.type==="message" && Array.isArray(item.content) ? item.content : [])
      .filter(c=>c?.type==="output_text" && typeof c.text==="string")
      .map(c=>c.text).join("\n").trim();
    if(!answer || answer.length>16000)throw Error("Invalid output");
    return res.status(200).json({
      answer,source:"openai-api",device_verified:false,
      exact_chatgpt_thread:false
    });
  } catch {
    return res.status(502).json({error:"Cloud chat request failed; no device command was sent"});
  }
};
module.exports._test={validate};