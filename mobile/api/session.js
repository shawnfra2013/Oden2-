"use strict";
const {protect}=require("../lib/access");
const {cloudChatConfigured} = require("../lib/openai-config");
module.exports=function handler(req,res){
  if(!protect(req,res))return;
  if(Object.keys(req.body).length) return res.status(400).json({error:"Unexpected fields"});
  return res.status(200).json({
    authenticated:true,
    cloud_chat_configured:cloudChatConfigured(),
    device_diagnostics_configured:Boolean(process.env.ODIN_GITHUB_TOKEN),
    private_odin_conversation_connected:false,
    private_relay_configured:Boolean(process.env.BLOB_READ_WRITE_TOKEN || process.env.VERCEL_OIDC_TOKEN),
    odin_pairing_configured:Boolean(process.env.ODIN_DEVICE_RELAY_TOKEN),
    exact_chatgpt_thread_connected:false,
    arbitrary_shell_enabled:false
  });
};
