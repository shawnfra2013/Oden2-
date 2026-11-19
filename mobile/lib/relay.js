"use strict";
const {put,get,head}=require("@vercel/blob");
const {randomBytes,timingSafeEqual,createHash}=require("node:crypto");
const PATH="odin-relay/v1/private-messages.json";
const ID=/^[0-9a-f]{32}$/;
const MAX_EVENTS=120;
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
async function readState() {
  const blob=await get(PATH,{access:"private",useCache:false});
  if(!blob || blob.statusCode!==200)return {etag:null,events:[]};
  const raw=await new Response(blob.stream).text();
  if(raw.length>500000)throw Error("Relay state exceeds limit");
  const data=JSON.parse(raw);
  if(!data || data.version!==1 || !Array.isArray(data.events))
    throw Error("Invalid relay state");
  // No mutation is attempted without an ETag for an existing journal.
  // Private Blob reads bypass CDN cache so a previous write cannot be lost.
  const etag=blob.blob?.etag || (await head(PATH))?.etag;
  if(typeof etag!=="string" || !etag)
    throw Object.assign(new Error("Missing journal ETag"),{code:"BLOB_ETAG_MISSING"});
  return {etag,events:data.events.slice(-MAX_EVENTS)};
}
function safeStorageCode(error){
  const name=typeof error?.name==="string" ? error.name : "";
  const message=typeof error?.message==="string" ? error.message : "";
  const status=Number(error?.statusCode || error?.status || error?.response?.status);
  if(error?.code==="BLOB_ETAG_MISSING")return "etag_missing";
  if(name==="BlobPreconditionFailedError" || status===412 ||
      /precondition|etag|if.match/i.test(message))return "etag_conflict";
  if(/already exists|overwrite/i.test(message) || status===409)return "already_exists";
  if(status===401 || status===403 || /unauthorized|invalid token|forbidden/i.test(message))
    return "storage_auth";
  if(status===404 || /not found/i.test(message))return "storage_not_found";
  if(status===429 || /rate.limit/i.test(message))return "storage_rate_limit";
  if(status>=500 && status<=599)return "storage_server_error";
  return "storage_error";
}
async function recordEvent(event,backend={readState,put}){
  const id=randomBytes(16).toString("hex");
  const at=new Date().toISOString();
  const entry={version:1,id,at,...event};
  for(let attempt=0;attempt<6;attempt++){
    const {etag,events}=await backend.readState();
    const next={version:1,events:[...events,entry].slice(-MAX_EVENTS)};
    try {
      await backend.put(PATH,JSON.stringify(next),{
        access:"private",addRandomSuffix:false,contentType:"application/json",
        cacheControlMaxAge:60,
        ...(etag?{allowOverwrite:true,ifMatch:etag}:{allowOverwrite:false})
      });
      return entry;
    }catch(err){
      const kind=safeStorageCode(err);
      if(!["etag_conflict","already_exists"].includes(kind) || attempt===5){
        const failure=new Error("Private journal update failed");
        failure.code=kind;
        throw failure;
      }
      // A competing writer can commit between read and CAS. Re-read rather
      // than overwriting a receipt or dropping an already queued message.
      await new Promise(resolve=>setTimeout(resolve,150*(attempt+1)));
    }
  }
  throw Object.assign(new Error("Journal attempts exhausted"),{code:"write_failed"});
}
async function loadEvents(){
  const {events}=await readState();
  return events.filter(e=>e&&e.version===1&&ID.test(e.id)
    &&Number.isFinite(Date.parse(e.at))
    &&["message","receipt"].includes(e.kind))
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
  view,validMessage,validReceipt,validReply,
  _test:{safeStorageCode,readState}};
