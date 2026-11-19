"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const relay=require("../lib/relay");

const OLD="a".repeat(32);
function makeStore(){
  const legacy=[{version:1,id:OLD,at:"2026-11-19T07:00:00Z",
    kind:"message",sender:"iphone",to:"odin",text:"/ping"}];
  const files=new Map();
  const backend={
    readState:async()=>({events:legacy.map(x=>({...x}))}),
    async put(path,raw,options){
      assert.ok(path.startsWith("odin-relay/v2/events/"));
      assert.notEqual(path,"odin-relay/v1/private-messages.json");
      assert.equal(options.access,"private");
      assert.equal(options.addRandomSuffix,false);
      assert.equal(Object.hasOwn(options,"allowOverwrite"),false);
      if(files.has(path))throw new Error("Blob already exists");
      files.set(path,JSON.parse(raw));
    },
    async list({prefix}){
      assert.equal(prefix,"odin-relay/v2/events/");
      return {blobs:[...files.keys()].map(pathname=>({pathname,uploadedAt:files.get(pathname).at})),
        hasMore:false,cursor:null};
    },
    async get(path){
      const value=files.get(path);
      if(!value)return null;
      return {statusCode:200,stream:new Response(JSON.stringify(value)).body};
    }
  };
  return {backend,files,legacy};
}

test("immutable relay preserves existing pending message and appends device reply",async()=>{
  const {backend,files,legacy}=makeStore();
  const receipt=await relay.recordEvent({kind:"receipt",sender:"odin",
    for:OLD,state:"delivered"},backend);
  const read=await relay.recordEvent({kind:"receipt",sender:"odin",
    for:OLD,state:"read"},backend);
  const reply=await relay.recordEvent({kind:"message",sender:"odin",
    to:"iphone",reply_to:OLD,text:"ODIN_RELAY_PONG"},backend);
  assert.notEqual(receipt.id,read.id);
  assert.notEqual(reply.id,read.id);
  assert.equal(files.size,3);
  const merged=await relay.loadEvents(backend);
  assert.equal(legacy.length,1);
  assert.equal(merged.length,4);
  const visible=relay.view(merged,"iphone");
  assert.equal(visible.find(m=>m.id===OLD).status,"replied");
  assert.equal(visible.find(m=>m.id===reply.id).text,"ODIN_RELAY_PONG");
});

test("concurrent event writes use different paths and cannot overwrite one another",async()=>{
  const {backend,files}=makeStore();
  await Promise.all([
    relay.recordEvent({kind:"receipt",sender:"odin",for:OLD,state:"delivered"},backend),
    relay.recordEvent({kind:"receipt",sender:"odin",for:OLD,state:"read"},backend)
  ]);
  assert.equal(files.size,2);
  const all=await relay.loadEvents(backend);
  assert.equal(all.filter(x=>x.kind==="receipt").length,2);
  assert.equal(relay.view(all,"iphone")[0].status,"read");
});

test("private event storage failures surface rather than claiming success",async()=>{
  const bad={put:async()=>{throw new Error("Storage denied");}};
  await assert.rejects(
    ()=>relay.recordEvent({kind:"receipt",sender:"odin",for:OLD,state:"read"},bad),
    /Storage denied/
  );
});

test("storage error classification does not return sensitive exception details",()=>{
  const err=new Error("token-example-private-secret");
  err.status=403;
  assert.equal(relay.safeStorageCode(err),"storage_auth");
  assert.equal(relay.safeStorageCode(new TypeError("internal secret")),"storage_api_error");
  assert.equal(relay.safeStorageCode(new Error("unknown sensitive value")),"storage_error");
});

test("lost confirmation and concurrent retries keep one owner message and original timestamp",async()=>{
  const {backend,files}=makeStore();
  const id="b".repeat(32);
  const first=await relay.recordOwnerMessage(id,"/ping",backend);
  const retried=await Promise.all([
    relay.recordOwnerMessage(id,"/ping",backend),
    relay.recordOwnerMessage(id,"/ping",backend)
  ]);
  assert.deepEqual(retried,[first,first]);
  assert.equal(files.size,1);
  assert.equal(await relay.recordOwnerMessage(id,"another message",backend),null);
  const viewed=relay.view(await relay.loadEvents(backend),"odin");
  assert.equal(viewed.filter(message=>message.id===id).length,1);
});

test("parallel replies for the same request create one immutable event",async()=>{
  const {backend,files}=makeStore();
  const first=await Promise.all([
    relay.recordDeviceReply(OLD,"same reply",backend),
    relay.recordDeviceReply(OLD,"same reply",backend)
  ]);
  assert.equal(first.filter(x=>x.created).length,1);
  assert.deepEqual(first[0].entry,first[1].entry);
  assert.equal(files.size,1);
  const different=await relay.recordDeviceReply(OLD,"different reply",backend);
  assert.equal(different.created,false);
  assert.equal(different.entry.text,"same reply");
  const seen=relay.view(await relay.loadEvents(backend),"iphone");
  assert.equal(seen.filter(x=>x.reply_to===OLD).length,1);
});
