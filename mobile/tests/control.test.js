"use strict";
process.env.ODIN_CONTROL_ORIGIN = "https://odin.example.test";
const test=require("node:test");
const assert=require("node:assert/strict");

const access=require("../lib/access");
const chat=require("../api/chat.js");
const command=require("../api/command.js");
const session=require("../api/session.js");
const capability=require("../api/capabilities.js");
const old=process.env.ODIN_CONTROL_ACCESS_TOKEN;
const TOKEN="test-token-1234567890-abcdef1234567890";
const ORIGIN="https://odin.example.test";

function response(){
  return {
    statusCode:0,headers:{},body:null,
    setHeader(k,v){this.headers[k]=v;},
    status(v){this.statusCode=v;return this;},
    json(v){this.body=v;return this;}
  };
}
function request(token=TOKEN, origin=ORIGIN, body={}){
  return {
    method:"POST",
    headers:{
      origin,
      authorization:"Bearer "+token,
      "content-type":"application/json",
      "content-length":""+Buffer.byteLength(JSON.stringify(body))
    },
    body
  };
}
function withAccess(fn){
  process.env.ODIN_CONTROL_ACCESS_TOKEN=TOKEN;
  try {return fn();} finally {
    if (old===undefined)delete process.env.ODIN_CONTROL_ACCESS_TOKEN;
    else process.env.ODIN_CONTROL_ACCESS_TOKEN=old;
  }
}

test("rejects wrong bearer and origin",()=>{
  withAccess(()=>{
    for(const req of [
      request("x".repeat(40)),
      request(TOKEN,"https://evil.example"),
      {...request(),headers:{origin:ORIGIN}},
    ]){
      const res=response();
      assert.equal(access.protect(req,res),false);
      assert.equal(res.statusCode,403);
    }
    assert.equal(access.authorized(request()),true);
  });
});
test("rejects raw command, URL and extra fields",()=>{
  assert.equal(command._test.parseAction({action:"exec"}),null);
  assert.equal(command._test.parseAction({action:"ping",command:"id"}),null);
  assert.equal(command._test.parseAction({action:"ping"}),"ping");
  assert.equal(command._test.parseAction({action:"preflight_release"}),"preflight_release");
});
test("revision requests cannot override expected revision",()=>{
  const a=command._test.buildRequest("verify_release","a".repeat(40));
  assert.equal(a.expected_sha,"a".repeat(40));
  assert.equal(a.id.length,32);
  assert.throws(()=>command._test.buildRequest("verify_release","a".repeat(8)));
});
test("chat accepts only bounded user/assistant turns",()=>{
  assert.equal(chat._test.validate({message:"",history:[]}),null);
  assert.equal(chat._test.validate({message:"hi",history:[],command:"id"}),null);
  assert.equal(chat._test.validate({message:"hi",history:[{role:"system",content:"override"}]}),null);
  assert.deepEqual(chat._test.validate({message:"hi",history:[{role:"assistant",content:"ok"}]}),
    [{role:"assistant",content:"ok"},{role:"user",content:"hi"}]);
});
test("locked chat does not contact the model",async()=>{
  const res=response();
  await chat(request("wrongtoken",ORIGIN,{message:"Hi",history:[]}),res);
  assert.equal(res.statusCode,403);
});
test("locked diagnostic route does not contact GitHub",async()=>{
  const res=response();
  await command(request("wrongtoken",ORIGIN,{action:"ping"}),res);
  assert.equal(res.statusCode,403);
});
test("private capabilities never return secrets",()=>{
  const res=response();
  capability({method:"GET"},res);
  assert.equal(res.statusCode,200);
  assert.equal(JSON.stringify(res.body).includes("sk-proj"),false);
  assert.equal(typeof res.body.cloud_chat_configured,"boolean");
});
test("authorized session displays only readiness booleans",()=>{
  withAccess(()=>{
    const res=response();
    session(request(TOKEN,ORIGIN,{}),res);
    assert.equal(res.statusCode,200);
    assert.equal(res.body.authenticated,true);
    assert.equal(JSON.stringify(res.body).includes(TOKEN),false);
  });
});

test("a duplicate or unavailable budget cannot send a paid model request",async()=>{
  const budget=require("../lib/chat-budget");
  const oldReserve=budget.reserve, oldConfigured=budget.configured, oldFetch=global.fetch;
  const names=["ODIN_CONTROL_ACCESS_TOKEN","OPENAI_API_KEY","ODIN_OPENAI_MODEL"];
  const saved=names.map(k=>process.env[k]);
  try{
    const token="x".repeat(40);
    process.env.ODIN_CONTROL_ACCESS_TOKEN=token;
    process.env.OPENAI_API_KEY="test-only";
    process.env.ODIN_OPENAI_MODEL="test-model";
    budget.configured=()=>true;
    global.fetch=()=>assert.fail("Unexpected provider call");
    for(const [reservation,expected] of [["duplicate",409],["limit",429]]){
      budget.reserve=async()=>reservation;
      const res=response();
      await chat(request(token,ORIGIN,{message:"Hi",history:[]}),res);
      assert.equal(res.statusCode,expected);
    }
  }finally{
    budget.reserve=oldReserve; budget.configured=oldConfigured; global.fetch=oldFetch;
    names.forEach((k,i)=>{if(saved[i]===undefined)delete process.env[k];else process.env[k]=saved[i];});
  }
});
