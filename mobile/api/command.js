"use strict";
const {randomBytes} = require("node:crypto");
const {protect} = require("../lib/access");
const REPO = "shawnfra2013/Oden2-";
const API = "https://api.github.com/repos/"+REPO;
const ACTIONS = new Set(["ping","repo_status","services","stage5_health","checks","verify_release","preflight_release","odin_health"]);
const SHA=/^[0-9a-f]{40}$/;
const iso=date=>date.toISOString().replace(/\.\d{3}Z$/,"Z");
function parseAction(body){
  if (!body || typeof body!=="object" || Array.isArray(body)
    || Object.keys(body).sort().join(",")!=="action"
    || !ACTIONS.has(body.action)) return null;
  return body.action;
}
function buildRequest(action, expectedSha=null, now=new Date()){
  const id=randomBytes(16).toString("hex");
  const body={version:1,id,action,
    created_at:iso(now),expires_at:iso(new Date(now.getTime()+15*60*1000))};
  if (action==="verify_release" || action==="preflight_release"){
    if (!SHA.test(expectedSha||""))throw Error("Invalid source revision");
    body.expected_sha=expectedSha;
  }
  return body;
}
module.exports = async function handler(req,res) {
  if (!protect(req,res))return;
  const token=process.env.ODIN_GITHUB_TOKEN;
  if(!token)return res.status(503).json({error:"GitHub diagnostics not configured in Vercel"});
  const action=parseAction(req.body);
  if(!action)return res.status(400).json({error:"Unsupported action"});
  const headers={
    "Authorization":"Bearer "+token,
    "Accept":"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28",
    "Content-Type":"application/json",
    "User-Agent":"Odin-Control-Verified-Diagnostics"
  };
  try {
    let sha=null;
    if(action==="verify_release" || action==="preflight_release"){
      const check=await fetch(API+"/branches/main",{
        headers,signal:AbortSignal.timeout(8000)
      });
      if(!check.ok)throw Error("Cannot verify revision");
      sha=(await check.json())?.commit?.sha;
      if(!SHA.test(sha||""))throw Error("Untrusted revision");
    }
    const request=buildRequest(action,sha);
    const path="bridge/requests/"+request.id+".json";
    const payload={
      branch:"odin-bridge-inbox",
      message:"Odin mobile diagnostic "+action+" "+request.id,
      content:Buffer.from(JSON.stringify(request,null,2)+"\n").toString("base64")
    };
    const submitted=await fetch(API+"/contents/"+path,{
      method:"PUT",headers,body:JSON.stringify(payload),
      signal:AbortSignal.timeout(12000)
    });
    if(submitted.status!==201)throw Error("GitHub submission failed");
    return res.status(202).json({
      accepted:true,id:request.id,action:request.action,
      created_at:request.created_at,expires_at:request.expires_at,
      expected_sha:request.expected_sha||null,
      status:"waiting_for_odin",device_completed:false
    });
  } catch {
    return res.status(502).json({error:"Request could not be submitted; no device operation confirmed"});
  }
};
module.exports._test={buildRequest,parseAction};