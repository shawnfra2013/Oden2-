"use strict";
const {put,get,list}=require("@vercel/blob");
const {randomBytes,timingSafeEqual,createHash}=require("node:crypto");
const PREFIX="odin-relay/v1/events/";
const ID=/^[0-9a-f]{32}$/;
const MAX_EVENTS=150;
function isText(value){return typeof value==="string" && value.trim().length>0 && value.length<=2000 && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value);}
function safeCompare(a,b){
  if(typeof a!=="string"||typeof b!=="string"||a.length<32||b.length<32)return false;
  const hash=s=>createHash("sha256").update(s).digest();
  return timingSafeEqual(hash(a),hash(b));
}
function deviceAuthorized(req) {
  const token=process.env.ODIN_DEVICE_RELAY_TOKEN;
  const auth=req.headers.authorization;
  return typeof token==="string" && token.length>=32
    && typeof auth==="string" && auth.startsWith("Bearer ")
    && safeCompare(auth.slice(7),token);
}
async function recordEvent(event){
  const id=randomBytes(16).toString("hex");
  const at=new Date().toISOString();
  const entry={version:1,id,at,...event};
  const path=PREFIX+at.replace(/[-:.]/g,"")+"-"+id+".json";
  await put(path,JSON.stringify(entry),{
    access:"private",addRandomSuffix:false,contentType:"application/json",
    cacheControlMaxAge:60,ttlDays:30
  });
  return entry;
}
async function readEvent(path){
  const blob=await get(path,{access:"private",useCache:false});
  if(!blob||blob.statusCode!==200)return null;
  const data=await new Response(blob.stream).text();
  if(data.length>8000)return null;
  try{return JSON.parse(data);}catch{return null;}
}
async function loadEvents(){
  const files=[];let cursor=null;
  for(let page=0;page<3;page++){
    const result=await list({prefix:PREFIX,limit:100,...(cursor?{cursor}:{})});
    files.push(...result.blobs.filter(x=>x.pathname.startsWith(PREFIX)));
    if(!result.hasMore||!result.cursor)break;
    cursor=result.cursor;
  }
  // Bounded to avoid unbounded serverless fan-out.
  const ordered=files.sort((a,b)=>b.pathname.localeCompare(a.pathname)).slice(0,MAX_EVENTS);
  const events=(await Promise.all(ordered.map(b=>readEvent(b.pathname)))).filter(Boolean);
  return events.filter(e=>e.version===1 && ID.test(e.id)
      && Number.isFinite(Date.parse(e.at)) && ["message","receipt"].includes(e.kind))
    .sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
}
function view(events,viewer) {
  const messages=events.filter(e=>e.kind==="message"&&ID.test(e.id)&&
    ["iphone","odin"].includes(e.sender)&&["iphone","odin"].includes(e.to)&&
    isText(e.text));
  const receipts=events.filter(e=>e.kind==="receipt"&&ID.test(e.for)
    && ["delivered","read","failed"].includes(e.state));
  return messages.filter(m=>viewer==="iphone"||m.to==="odin"||m.sender==="odin").map(m=>{
    const related=receipts.filter(r=>r.for===m.id && r.sender===m.to);
    const reply=messages.find(x=>x.sender===m.to && x.reply_to===m.id);
    const states=["delivered","read","failed"];
    let status=reply?"replied":related.findLast(r=>states.includes(r.state))?.state||"queued";
    return {id:m.id,at:m.at,sender:m.sender,to:m.to,
      text:m.text,reply_to:m.reply_to||null,status,
      last_activity:reply?.at||related[related.length-1]?.at||m.at};
  });
}
function validMessage(body) {
  return body && typeof body==="object" && !Array.isArray(body)
    && Object.keys(body).sort().join(",")==="text,type"
    && body.type==="message" && isText(body.text);
}
function validReceipt(body){
  return body && typeof body==="object" && !Array.isArray(body)
    && Object.keys(body).sort().join(",")==="for,state,type"
    && body.type==="receipt" && ID.test(body.for)
    && ["delivered","read","failed"].includes(body.state);
}
function validReply(body){
  return body && typeof body==="object" && !Array.isArray(body)
    && Object.keys(body).sort().join(",")==="for,text,type"
    && body.type==="reply" && ID.test(body.for) && isText(body.text);
}
module.exports={ID,isText,deviceAuthorized,safeCompare,recordEvent,loadEvents,
  view,validMessage,validReceipt,validReply};
