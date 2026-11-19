"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {readFileSync}=require("node:fs");
const {randomUUID}=require("node:crypto");
const vm=require("node:vm");

test("a lost send confirmation reuses the original ID, then a new send gets a new ID",async()=>{
  const source=readFileSync(require.resolve("../app.js"),"utf8");
  const start=source.indexOf("async function queuePrivateRelayMessage(");
  const end=source.indexOf("function confirmRestart(",start);
  const node={value:"/ping"};
  const posted=[];
  const context=vm.createContext({
    $:()=>node,
    crypto:{randomUUID},
    pendingRelaySends:new Map(),
    privateState:{connected:true,relay:true,token:"fake"},
    relayLocal:{sending:false},
    restartLocal:{},
    renderRelay(){},refreshRelay(){},isRestartCommand:()=>false,
    async authenticatedPost(path,body){
      assert.equal(path,"/api/relay");
      posted.push(body);
      if(posted.length===1)throw new TypeError("Connection lost after storage");
      return {status:"queued",id:body.id};
    }
  });
  vm.runInContext(source.slice(start,end),context);
  await context.queuePrivateRelayMessage("/ping");
  assert.equal(node.value,"/ping");
  await context.queuePrivateRelayMessage("/ping");
  assert.equal(node.value,"");
  await context.queuePrivateRelayMessage("/ping");
  assert.match(posted[0].id,/^[0-9a-f]{32}$/);
  assert.equal(posted[0].id,posted[1].id);
  assert.notEqual(posted[1].id,posted[2].id);
});
