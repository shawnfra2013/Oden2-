"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const app = require("../api/status.js");
const {sanitize, sanitizeRequest, requestId} = app._test;
const id = "0123456789abcdef0123456789abcdef";
const now = "2026-11-19T00:00:00Z";

test("only recognized, structurally valid responses are presented", () => {
  assert.equal(sanitize({id:"other",action:"ping",status:"complete",checked_at:now,result:{}},id), null);
  assert.equal(sanitize({id,action:"exec",status:"complete",checked_at:now,result:{}},id), null);
  assert.equal(sanitize({id,action:"ping",status:"complete",checked_at:"bogus",result:{}},id), null);
  assert.equal(sanitize({id,action:"ping",status:"complete",checked_at:now,result:{alive:true}},id).result.alive,true);
});

test("private strings and unknown values are not leaked", () => {
  const received=sanitize({id,action:"repo_status",status:"complete",checked_at:now,result:{
    alive:true, secret:"sk-proj-test", transcript:"private message",
    head:"a".repeat(40),branch:"main",untracked_count:9,
    device_path:"/data/data/com.termux",object:{private:"hello"}
  }}, id);
  assert.deepEqual(received.result,{
    alive:true,head:"a".repeat(40),branch:"main",untracked_count:9
  });
  assert.equal(JSON.stringify(received).includes("sk-proj"),false);
  assert.equal(JSON.stringify(received).includes("private message"),false);
});

test("nested checks are restricted to boolean results", () => {
  const received=sanitize({id,action:"verify_release",status:"complete",checked_at:now,result:{
    verified:true,
    checks:{stage4_passed:true,stage5_passed:false,ruff_passed:true,
      raw_logs:"secret", extra:"more secret"}
  }},id);
  assert.deepEqual(received.result.checks,{
    stage4_passed:true,stage5_passed:false,ruff_passed:true
  });
});

test("request metadata cannot carry full conversation messages", () => {
  const r=sanitizeRequest({
    id,action:"checks",created_at:now,expires_at:"2026-11-19T00:30:00Z",
    message:"please print my key",api_key:"private"
  },id);
  assert.deepEqual(r,{
    id,action:"checks",created_at:now,expires_at:"2026-11-19T00:30:00Z"
  });
});

test("commit message IDs are read safely", () => {
  assert.equal(requestId("Odin bridge response "+id),id);
  assert.equal(requestId("unrelated commit"),null);
});

test("dashboard has disabled conversation composer, no private API calls", () => {
  const root=path.resolve(__dirname,"..");
  const html=fs.readFileSync(path.join(root,"index.html"),"utf8");
  const js=fs.readFileSync(path.join(root,"app.js"),"utf8");
  assert.match(html, /Messaging unlocks after private pairing/);
  assert.match(html, /<input disabled/);
  assert.match(js, /fetch\("\/api\/status"/);
  assert.doesNotMatch(js, /OPENAI_API_KEY|sk-proj|exec\(/);
});

test("API only permits GET",async()=>{
  let status=null,body=null,allow=null;
  const req={method:"POST"};
  const res={
    setHeader(key,value){if(key==="Allow")allow=value;},
    status(value){status=value;return this;},
    json(value){body=value;return value;}
  };
  await app(req,res);
  assert.equal(status,405);
  assert.equal(allow,"GET");
  assert.equal(body.error,"Method not allowed");
});
