"use strict";
const {put,get,list}=require("@vercel/blob");
const {randomBytes,timingSafeEqual,createHash}=require("node:crypto");
const PATH="odin-relay/v1/private-messages.json";
const EVENT_PREFIX="odin-relay/v2/events/";
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
// Keep the original journal read-only so no preexisting queued messages
// or private conversation history is discarded during the repair.
async function readState(){
  const blob=await get(PATH,{access:"private",useCache:false});
  if(!blob)return {events:[]};
  if(blob.statusCode!==200)throw Error("Legacy private journal unreadable");
  const raw=await new Response(blob.stream).text();
  if(raw.length>500000)throw Error("Legacy journal exceeds read limit");
  const data=JSON.parse(raw);
  if(!data||data.version!==1||!Array.isArray(data.events))
    throw Error("Invalid legacy journal format");
  return {events:data.events};
}
function safeStorageCode(error){
  const name=typeof error?.name==="string"?error.name:"";
  const message=typeof error?.message==="string"?error.message:"";
  const status=Number(error?.statusCode||error?.status||error?.response?.status);
  if(name==="BlobPreconditionFailedError"||status===412||
      /precondition|etag|if.match/i.test(message))return "etag_conflict";
  if(/already exists|overwrite/i.test(message)||status===409)return "already_exists";
  if(status===401||status===403||/unauthorized|invalid token|forbidden/i.test(message))
    return "storage_auth";
  if(status===404||/not found/i.test(message))return "storage_not_found";
  if(status===429||/rate.limit/i.test(message))return "storage_rate_limit";
  if(status>=500&&status<=599)return "storage_server_error";
  if(name==="TypeError")return "storage_api_error";
  return "storage_error";
}
async function recordEvent(event,backend={put}){
  // Each message, receipt and reply is written only once at a unique private
  // pathname. No ETag/overwrite operations, concurrency conflicts, or
  // replacement of another event's content.
  const id=randomBytes(16).toString("hex");
  const at=new Date().toISOString();
  const entry={version:1,id,at,...event};
  const path=EVENT_PREFIX+at.replace(/[-:.TZ]/g,"")+"-"+id+".json";
  await backend.put(path,JSON.stringify(entry),{
    access:"private",addRandomSuffix:false,contentType:"application/json",
    cacheControlMaxAge:60
  });
  return entry;
}
async function readPrivateEvent(pathname,backend){
  const blob=await backend.get(pathname,{access:"private",useCache:false});
  if(!blob||blob.statusCode!==200)throw Error("Private relay event unreadable");
  const raw=await new Response(blob.stream).text();
  if(raw.length>10000)throw Error("Private relay event too large");
  const data=JSON.parse(raw);
  if(!data||data.version!==1||!ID.test(data.id)||
    !Number.isFinite(Date.parse(data.at))||
    !["message","receipt"].includes(data.kind))
    throw Error("Invalid private relay event");
  return data;
}
async function loadEvents(backend={list,get,readState}){
  const blobs=[];
  let cursor=null;
  let hasMore=false;
  for(let page=0;page<20;page++){
    const result=await backend.list({
      prefix:EVENT_PREFIX,limit:100,...(cursor?{cursor}:{})
    });
    if(!result||!Array.isArray(result.blobs))
      throw Error("Private relay listing unavailable");
    blobs.push(...result.blobs.filter(x=>typeof x.pathname==="string"&&
      x.pathname.startsWith(EVENT_PREFIX)));
    hasMore=result.hasMore===true;
    if(!hasMore)break;
    if(!result.cursor)throw Error("Private relay listing cursor unavailable");
    cursor=result.cursor;
  }
  // Do not claim a complete history if the storage scan was incomplete.
  if(hasMore)throw Error("Private relay event listing exceeded limit");
  // New objects have sortable timestamp-based names; bound the number of
  // private reads while retaining every object in storage for future export.
  const latest=blobs.sort((a,b)=>b.pathname.localeCompare(a.pathname))
    .slice(0,MAX_EVENTS);
  const [legacy,events]=await Promise.all([
    backend.readState(),
    Promise.all(latest.map(x=>readPrivateEvent(x.pathname,backend)))
  ]);
  const merged=[...(legacy.events||[]),...events];
  const seen=new Set();
  return merged.filter(e=>e&&e.version===1&&ID.test(e.id)&&
    Number.isFinite(Date.parse(e.at))&&["message","receipt"].includes(e.kind))
    .sort((a,b)=>Date.parse(a.at)-Date.parse(b.at))
    .filter(e=>seen.has(e.id)?false:(seen.add(e.id),true))
    .slice(-MAX_EVENTS);
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
    const states={delivered:1,read:2,failed:3};
    const last=related.filter(r=>Object.hasOwn(states,r.state))
      .sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)||
        states[a.state]-states[b.state]||a.id.localeCompare(b.id)).at(-1);
    const status=reply?"replied":last?.state||"queued";
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
  view,validMessage,validReceipt,validReply,safeStorageCode,
  _test:{readState,readPrivateEvent,EVENT_PREFIX}};
