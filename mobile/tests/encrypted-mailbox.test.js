"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const handler = require("../api/encrypted-chat");
test("private mailbox rejects unauthorized and plaintext input; retry reuses the ciphertext", async t => {
  const token = "test-only-"+"a".repeat(40);
  const env = process.env;
  const original = {ODIN_CONTROL_ACCESS_TOKEN:env.ODIN_CONTROL_ACCESS_TOKEN, ODIN_PRIVATE_MAILBOX_TOKEN:env.ODIN_PRIVATE_MAILBOX_TOKEN};
  Object.assign(env, {ODIN_CONTROL_ACCESS_TOKEN:token,ODIN_PRIVATE_MAILBOX_TOKEN:"fixture"});
  t.after(()=>{for(const [k,v] of Object.entries(original)) { if(v===undefined) delete env[k]; else env[k]=v; }});
  let stored,receipt;
  t.mock.method(global,"fetch",async(url,opts)=>{
    if(opts.method==="PUT"){
      if(stored) return {ok:false,status:422};
      stored=JSON.parse(opts.body).content;return {ok:true,status:201};
    }
    const content=url.includes("/responses/")?receipt:stored;
    return {ok:Boolean(content),status:content?200:404,json:async()=>({content})};
  });
  async function post(body, authorized=true) {
    const res={setHeader(){},status(n){this.code=n;return this},json(data){this.data=data}};
    await handler({method:"POST",headers:{origin:"https://odin-control.vercel.app",authorization:"Bearer "+(authorized?token:"none"),
      "content-type":"application/json","content-length":String(Buffer.byteLength(JSON.stringify(body)))},body},res);
    return res;
  }
  const id="a".repeat(32), sealed=Buffer.alloc(64,77).toString("base64");
  assert.equal((await post({id},false)).code,403);
  assert.equal((await post({id,text:"question"})).code,400);
  assert.equal((await post({id,sealed})).code,202);
  assert.equal((await post({id,sealed})).code,202);
  assert.equal((await post({id,sealed:sealed.replace("T","S")})).code,502);
  assert.deepEqual((await post({id})).data,{pending:true});
  receipt=Buffer.from(JSON.stringify({id,action:"encrypted_chat",status:"complete",result:{sealed}})).toString("base64");
  assert.deepEqual((await post({id})).data,{sealed});
});
