"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const access=require("../lib/access");
const relay=require("../lib/relay");
const handler=require("../api/relay");
const IPHONE_TOKEN="test-private-owner-token-00000000000001";
const DEVICE_TOKEN="test-private-device-token-0000000000001";
const ORIGIN="https://odin-control.vercel.app";
const ID="0123456789abcdef0123456789abcdef";

function reply(){
  return {headers:{},statusCode:null,data:null,
    setHeader(k,v){this.headers[k]=v;},
    status(value){this.statusCode=value;return this;},
    json(value){this.data=value;return value;}};
}
function request(method,token,body,origin){
  const raw=JSON.stringify(body||{});
  return {method,headers:{
      authorization:"Bearer "+token,
      ...(origin?{origin}:{}),
      "content-type":"application/json",
      "content-length":String(Buffer.byteLength(raw))
    },body:body||{}};
}
function environ(callback){
  const keys=["ODIN_CONTROL_ACCESS_TOKEN","ODIN_DEVICE_RELAY_TOKEN","BLOB_READ_WRITE_TOKEN"];
  const old=keys.map(k=>process.env[k]);
  process.env.ODIN_CONTROL_ACCESS_TOKEN=IPHONE_TOKEN;
  process.env.ODIN_DEVICE_RELAY_TOKEN=DEVICE_TOKEN;
  process.env.BLOB_READ_WRITE_TOKEN="fake-test-storage-token-not-network-access";
  const restore=()=>keys.forEach((k,i)=>{
    if(old[i]===undefined)delete process.env[k];else process.env[k]=old[i];
  });
  return Promise.resolve().then(callback).finally(restore);
}
function stubRelay(callback){
  const original={loadEvents:relay.loadEvents,recordEvent:relay.recordEvent};
  const events=[];
  relay.loadEvents=async()=>events;
  relay.recordEvent=async event=>{
    const value={...event,version:1,id:ID,at:"2026-11-19T06:00:00Z"};
    events.push(value);return value;
  };
  return Promise.resolve().then(()=>callback(events)).finally(()=>{
    relay.loadEvents=original.loadEvents;
    relay.recordEvent=original.recordEvent;
  });
}
test("relay origin validator is exported and used",()=>{
  assert.equal(typeof access.validOrigin,"function");
  assert.equal(access.validOrigin({headers:{origin:ORIGIN}}),true);
  assert.equal(access.validOrigin({headers:{origin:"https://other.example"}}),false);
});
test("authenticated iPhone GET can omit Origin header; message route does not throw",async()=>{
  await environ(()=>stubRelay(async()=>{
    const res=reply();
    await handler(request("GET",IPHONE_TOKEN,{}),res);
    assert.equal(res.statusCode,200);
    assert.equal(res.data.source,"private-odin-relay");
    assert.deepEqual(res.data.messages,[]);
  }));
});
test("authenticated iPhone submits message; Odin can read it and acknowledge",async()=>{
  await environ(()=>stubRelay(async()=>{
    let res=reply();
    await handler(request("POST",IPHONE_TOKEN,
      {type:"message",text:"/ping"},ORIGIN),res);
    assert.equal(res.statusCode,202);
    assert.equal(res.data.status,"queued");
    res=reply();
    await handler(request("GET",DEVICE_TOKEN,{}),res);
    assert.equal(res.statusCode,200);
    assert.equal(res.data.messages[0].text,"/ping");
    res=reply();
    await handler(request("POST",DEVICE_TOKEN,
      {type:"receipt",for:ID,state:"delivered"}),res);
    assert.equal(res.statusCode,201);
    assert.equal(res.data.status,"delivered");
    res=reply();
    await handler(request("POST",DEVICE_TOKEN,
      {type:"reply",for:ID,text:"ODIN_RELAY_PONG"}),res);
    assert.equal(res.statusCode,201);
    res=reply();
    await handler(request("GET",IPHONE_TOKEN,{},ORIGIN),res);
    assert.equal(res.statusCode,200);
    assert.ok(res.data.messages.some(m=>m.text==="ODIN_RELAY_PONG"));
  }));
});
test("unauthorized relay message and external Origin are rejected",async()=>{
  await environ(()=>stubRelay(async()=>{
    let res=reply();
    await handler(request("POST",IPHONE_TOKEN,
      {type:"message",text:"No"}, "https://evil.example"),res);
    assert.equal(res.statusCode,403);
    res=reply();
    await handler(request("POST","invalid", {type:"message",text:"No"},ORIGIN),res);
    assert.equal(res.statusCode,403);
  }));
});


test("storage failures return a visible sanitized stage, not fake success",async()=>{
  await environ(async()=>{
    const original=relay.loadEvents;
    const originalError=console.error;
    let logged=null;
    relay.loadEvents=async()=>{throw new Error("example-private-secret-never-log");};
    console.error=(...args)=>{logged=args.join(" ");};
    try {
      const res=reply();
      await handler(request("GET",IPHONE_TOKEN,{}),res);
      assert.equal(res.statusCode,503);
      assert.equal(res.data.stage,"load");
      assert.match(res.data.error,/Private relay unavailable/);
      assert.match(logged,/ODIN_RELAY_FAILURE/);
      assert.doesNotMatch(logged,/example-private-secret/);
      assert.doesNotMatch(JSON.stringify(res.data),/example-private-secret/);
    }finally{
      relay.loadEvents=original;
      console.error=originalError;
    }
  });
});

test("device failure reason remains an allowlisted code visible to the iPhone",async()=>{
  await environ(()=>stubRelay(async()=>{
    let res=reply();
    await handler(request("POST",IPHONE_TOKEN,
      {type:"message",text:"Explain this"},ORIGIN),res);
    assert.equal(res.statusCode,202);
    res=reply();
    await handler(request("POST",DEVICE_TOKEN,
      {type:"receipt",for:ID,state:"failed",reason:"credential_missing"}),res);
    assert.equal(res.statusCode,201);
    res=reply();
    await handler(request("GET",IPHONE_TOKEN,{},ORIGIN),res);
    const message=res.data.messages.find(x=>x.sender==="iphone");
    assert.equal(message.status,"failed");
    assert.equal(message.failure_reason,"credential_missing");
  }));
});
test("relay rejects arbitrary sensitive failure reason and reasons on success",async()=>{
  await environ(()=>stubRelay(async()=>{
    let res=reply();
    await handler(request("POST",DEVICE_TOKEN,{
      type:"receipt",for:ID,state:"failed",
      reason:"private-provider-token-should-not-leak"
    }),res);
    assert.equal(res.statusCode,400);
    res=reply();
    await handler(request("POST",DEVICE_TOKEN,{
      type:"receipt",for:ID,state:"read",reason:"credential_missing"
    }),res);
    assert.equal(res.statusCode,400);
  }));
});

test("stable owner request ID is passed to storage and a changed payload returns conflict",async()=>{
  await environ(async()=>{
    const original=relay.recordOwnerMessage;
    const entry={id:ID,at:"2026-11-19T06:00:00Z"};
    relay.recordOwnerMessage=async(id,text)=>{
      assert.equal(id,ID);
      return text==="/ping"?entry:null;
    };
    try{
      let res=reply();
      await handler(request("POST",IPHONE_TOKEN,{type:"message",text:"/ping",id:ID},ORIGIN),res);
      assert.equal(res.statusCode,202);
      assert.deepEqual(res.data,{...entry,status:"queued"});
      res=reply();
      await handler(request("POST",IPHONE_TOKEN,{type:"message",text:"changed",id:ID},ORIGIN),res);
      assert.equal(res.statusCode,409);
      res=reply();
      await handler(request("POST",DEVICE_TOKEN,{type:"message",text:"/ping",id:ID},ORIGIN),res);
      assert.equal(res.statusCode,400);
    }finally{relay.recordOwnerMessage=original;}
  });
});
