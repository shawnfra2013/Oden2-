"use strict";
const {put,get,list}=require("@vercel/blob");
const {randomBytes,timingSafeEqual,createHash}=require("node:crypto");
const PATH="odin-relay/v1/private-messages.json";
const EVENT_PREFIX="odin-relay/v2/events/";
const ID=/^[0-9a-f]{32}$/;
const FAILURE_CODES=new Set([
  "ai_disabled","credential_missing","model_missing","invalid_provider",
  "provider_unavailable","provider_timeout","model_response_invalid",
  "task_failed","status_unavailable"
]);
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
  await writeEvent(path,entry,backend);
  return entry;
}
async function writeEvent(path,entry,backend){
  await backend.put(path,JSON.stringify(entry),{
    access:"private",addRandomSuffix:false,contentType:"application/json",
    cacheControlMaxAge:60
  });
}
async function recordOwnerMessage(id,text,backend={put,get}){
  if(typeof id!=="string"||!ID.test(id)||!isText(text))throw new TypeError("Invalid owner message");
  const entry={version:1,id,at:new Date().toISOString(),kind:"message",sender:"iphone",to:"odin",text:text.trim()};
  const {entry:saved}=await writeOnce(EVENT_PREFIX+"request-"+id+".json",entry,backend);
  if(saved.id!==id||saved.kind!=="message"||saved.sender!=="iphone"||saved.to!=="odin")
    throw Error("Stored owner message does not match its pathname");
  return saved.text===entry.text?saved:null;
}
async function recordDeviceReply(requestId,text,backend={put,get}){
  if(typeof requestId!=="string"||!ID.test(requestId)||!isText(text))throw new TypeError("Invalid device reply");
  const entry={version:1,id:randomBytes(16).toString("hex"),at:new Date().toISOString(),
    kind:"message",sender:"odin",to:"iphone",reply_to:requestId,text:text.trim()};
  const saved=await writeOnce(EVENT_PREFIX+"reply-"+requestId+".json",entry,backend);
  if(saved.entry.reply_to!==requestId||saved.entry.kind!=="message"||
      saved.entry.sender!=="odin"||saved.entry.to!=="iphone")
    throw Error("Stored device reply does not match its pathname");
  return saved;
}
async function writeOnce(path,entry,backend){
  try{
    await writeEvent(path,entry,backend);
    return {entry,created:true};
  }catch(error){
    if(!["already_exists","etag_conflict"].includes(safeStorageCode(error)))throw error;
    return {entry:await readPrivateEvent(path,backend),created:false};
  }
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
  const legacy=await backend.readState();
  const events=[...(legacy.events||[])];
  let cursor;
  const cursors=new Set();
  do{
    const page=await backend.list({prefix:EVENT_PREFIX,limit:100,...(cursor?{cursor}:{})});
    if(!Array.isArray(page?.blobs))throw Error("Private relay listing unavailable");
    const paths=page.blobs.map(blob=>blob.pathname).filter(path=>path?.startsWith(EVENT_PREFIX));
    for(let offset=0;offset<paths.length;offset+=8){
      events.push(...await Promise.all(paths.slice(offset,offset+8).map(path=>readPrivateEvent(path,backend))));
    }
    cursor=page.hasMore?page.cursor:null;
    if(page.hasMore && (!cursor||cursors.has(cursor)))throw Error("Invalid private relay cursor");
    if(cursor)cursors.add(cursor);
  }while(cursor);
  const seen=new Set();
  return events.filter(e=>e&&e.version===1&&ID.test(e.id)&&
    Number.isFinite(Date.parse(e.at))&&["message","receipt"].includes(e.kind))
    .sort((a,b)=>Date.parse(a.at)-Date.parse(b.at))
    .filter(e=>seen.has(e.id)?false:(seen.add(e.id),true));
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
      failure_reason:status==="failed"&&FAILURE_CODES.has(last?.reason)
        ? last.reason:null,
      last_activity:reply?.at||related[related.length-1]?.at||m.at};
  });
}
function validMessage(body) {
  return body && typeof body==="object" && !Array.isArray(body)
    && (Object.keys(body).sort().join(",")==="text,type" ||
      (Object.keys(body).sort().join(",")==="id,text,type" && typeof body.id==="string" && ID.test(body.id)))
    && body.type==="message" && isText(body.text);
}
function validReceipt(body){
  if(!body || typeof body!=="object" || Array.isArray(body))return false;
  const keys=Object.keys(body).sort().join(",");
  if(keys!=="for,state,type"&&keys!=="for,reason,state,type")return false;
  if(body.type!=="receipt"||!ID.test(body.for)
    ||!["delivered","read","failed"].includes(body.state))return false;
  if(keys==="for,reason,state,type")
    return body.state==="failed" && FAILURE_CODES.has(body.reason);
  return true;
}
function validReply(body){
  return body && typeof body==="object" && !Array.isArray(body)
    && Object.keys(body).sort().join(",")==="for,text,type"
    && body.type==="reply" && ID.test(body.for) && isText(body.text);
}
module.exports={ID,isText,deviceAuthorized,safeCompare,recordEvent,recordOwnerMessage,recordDeviceReply,loadEvents,
  view,validMessage,validReceipt,validReply,safeStorageCode,FAILURE_CODES,
  _test:{readState,readPrivateEvent,EVENT_PREFIX}};
