"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const relay=require("../lib/relay");
const ID="0123456789abcdef0123456789abcdef";
const OTHER="fedcba9876543210fedcba9876543210";
const msg=(id,sender,to,text,at)=>({kind:"message",version:1,id,at,sender,to,text});
test("phone messages begin queued and move through delivered, read, replied",()=>{
  const at="2026-11-19T00:00:00.000Z";
  const m=msg(ID,"iphone","odin","Please report status",at);
  assert.equal(relay.view([m],"iphone")[0].status,"queued");
  const delivered={kind:"receipt",id:"a".repeat(32),version:1,at:"2026-11-19T00:00:01.000Z",
    sender:"odin",for:ID,state:"delivered"};
  assert.equal(relay.view([m,delivered],"iphone")[0].status,"delivered");
  const read={...delivered,id:"b".repeat(32),at:"2026-11-19T00:00:02.000Z",state:"read"};
  assert.equal(relay.view([m,delivered,read],"iphone")[0].status,"read");
  const reply={...msg(OTHER,"odin","iphone","Here is my response","2026-11-19T00:00:03.000Z"),
    reply_to:ID};
  assert.equal(relay.view([m,delivered,read,reply],"iphone")[0].status,"replied");
  assert.equal(relay.view([m,delivered,read,reply],"odin").length,2);
});
test("Odin can see when owner reads replies",()=>{
  const reply={...msg(OTHER,"odin","iphone","Done","2026-11-19T00:00:00.000Z"),
    reply_to:ID};
  const seen={kind:"receipt",version:1,id:"c".repeat(32),
    sender:"iphone",for:OTHER,state:"read",at:"2026-11-19T00:00:03.000Z"};
  assert.equal(relay.view([reply,seen],"odin")[0].status,"read");
});
test("invalid forms and extra command fields are rejected",()=>{
  assert.equal(relay.validMessage({type:"message",text:"Hello"}),true);
  assert.equal(relay.validMessage({type:"message",text:"Hello",command:"rm -rf /"}),false);
  assert.equal(relay.validMessage({type:"message",text:""}),false);
  assert.equal(relay.validMessage({type:"message",text:"x".repeat(2001)}),false);
  assert.equal(relay.validReceipt({type:"receipt",for:ID,state:"read"}),true);
  assert.equal(relay.validReply({type:"reply",for:ID,text:"I am here"}),true);
  assert.equal(relay.validReply({type:"reply",for:"wrong",text:"No"}),false);
});
test("device authentication is separate from iPhone access",()=>{
  const old=process.env.ODIN_DEVICE_RELAY_TOKEN;
  process.env.ODIN_DEVICE_RELAY_TOKEN="device-1234567890-abcdef1234567890";
  try {
    assert.equal(relay.deviceAuthorized({headers:{authorization:
      "Bearer device-1234567890-abcdef1234567890"}}),true);
    assert.equal(relay.deviceAuthorized({headers:{authorization:
      "Bearer iphone-1234567890-abcdef1234567890"}}),false);
    assert.equal(relay.deviceAuthorized({headers:{}}),false);
  } finally {
    if(old===undefined)delete process.env.ODIN_DEVICE_RELAY_TOKEN;
    else process.env.ODIN_DEVICE_RELAY_TOKEN=old;
  }
});

test("failed receipts have bounded reason codes and do not disclose messages",()=>{
  assert.equal(relay.validReceipt({
    type:"receipt",for:ID,state:"failed",reason:"ai_disabled"
  }),true);
  assert.equal(relay.validReceipt({
    type:"receipt",for:ID,state:"failed",reason:"secret-password"
  }),false);
  assert.equal(relay.validReceipt({
    type:"receipt",for:ID,state:"read",reason:"ai_disabled"
  }),false);
  const initial=msg(ID,"iphone","odin","Hello Odin","2026-11-19T00:00:00.000Z");
  const failure={kind:"receipt",version:1,id:"a".repeat(32),
    at:"2026-11-19T00:00:04.000Z",sender:"odin",for:ID,state:"failed",
    reason:"ai_disabled"};
  const record=relay.view([initial,failure],"iphone")[0];
  assert.equal(record.status,"failed");
  assert.equal(record.failure_reason,"ai_disabled");
  assert.equal(record.text,"Hello Odin");
});
