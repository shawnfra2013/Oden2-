"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const relay=require("../lib/relay");

test("journal record uses CAS to append receipt without losing prior message",async()=>{
  let data=[{
    version:1,kind:"message",id:"a".repeat(32),at:"2026-11-19T07:00:00Z",
    sender:"iphone",to:"odin",text:"/ping"
  }];
  let version=1;
  const backend={
    async readState(){return {etag:'"'+version+'"',events:[...data]};},
    async put(path,raw,options){
      assert.equal(path,"odin-relay/v1/private-messages.json");
      assert.equal(options.access,"private");
      assert.equal(options.allowOverwrite,true);
      assert.equal(options.ifMatch,'"'+version+'"');
      const next=JSON.parse(raw);
      assert.ok(next.events.some(item=>item.kind==="message"&&item.text==="/ping"));
      assert.ok(next.events.some(item=>item.kind==="receipt"&&item.state==="delivered"));
      data=next.events;version++;
    }
  };
  const receipt=await relay.recordEvent({kind:"receipt",sender:"odin",for:"a".repeat(32),
    state:"delivered"},backend);
  assert.equal(receipt.kind,"receipt");
  assert.equal(data.length,2);
  assert.equal(data[1].state,"delivered");
});

test("journal retries ETag conflict rather than dropping concurrent writer",async()=>{
  let data=[{kind:"message",id:"a".repeat(32),version:1,
    at:"2026-11-19T07:00:00Z",text:"old",sender:"iphone",to:"odin"}];
  let version=2,writes=0;
  const backend={
    async readState(){return {etag:'"'+version+'"',events:[...data]};},
    async put(_path,raw,{ifMatch}){
      writes++;
      if(writes===1){
        // Another writer's event is preserved on retry.
        data=[...data,{kind:"message",id:"b".repeat(32),version:1,
          at:"2026-11-19T07:00:01Z",text:"concurrent",sender:"iphone",to:"odin"}];
        version++;
        const e=new Error("Precondition failed");
        e.name="BlobPreconditionFailedError";
        throw e;
      }
      assert.equal(ifMatch,'"'+version+'"');
      data=JSON.parse(raw).events;
    }
  };
  await relay.recordEvent({kind:"receipt",sender:"odin",for:"a".repeat(32),
    state:"read"},backend);
  assert.equal(writes,2);
  assert.equal(data.length,3);
  assert.ok(data.find(x=>x.text==="concurrent"));
  assert.ok(data.find(x=>x.state==="read"));
});

test("storage failure classification does not expose exception messages",()=>{
  const storageError=new Error("token-sensitive-example: not allowed");
  storageError.status=403;
  assert.equal(relay.safeStorageCode(storageError),"storage_auth");
  assert.equal(relay.safeStorageCode(Object.assign(new Error("ETag mismatch"),{
    name:"BlobPreconditionFailedError"})),"etag_conflict");
  assert.equal(relay.safeStorageCode(new Error("unrecognized detail")),"storage_error");
});
