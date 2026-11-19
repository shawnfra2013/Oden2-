"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const html=fs.readFileSync(path.resolve(__dirname,"../index.html"),"utf8");
const app=fs.readFileSync(path.resolve(__dirname,"../app.js"),"utf8");
const relay=require("../lib/relay");

test("System has authenticated restart-all button with clear warning",()=>{
  assert.match(html,/id="restartAllButton"[^>]*disabled/);
  assert.match(html,/id="restartAllStatus"[^>]*role="status"/);
  assert.match(html,/interrupt running tasks and messages/i);
});
test("chat and System share the same authenticated private relay",()=>{
  assert.match(html,/data-relay-quick="\/restart-services"/);
  assert.match(app,/queuePrivateRelayMessage\("\/restart-services"\)/);
  assert.match(app,/queuePrivateRelayMessage\(text\)/);
  assert.match(app,/authenticatedPost\("\/api\/relay",\{type:"message",text\}/);
  assert.match(app,/if\(isRestartCommand\(text\)&&!confirmRestart\(restartTarget\(text\)\)\)return/);
  assert.match(app,/if\(!confirmRestart\(\)\)return/);
  assert.match(app,/privateState\.paired/);
});
test("restart does not broaden the remote API beyond plain private messages",()=>{
  assert.equal(relay.validMessage({type:"message",text:"/restart-services"}),true);
  assert.equal(relay.validMessage({
    type:"message",text:"/restart-services",argv:["sv","restart","sshd"]
  }),false);
  assert.match(app,/ODIN_SERVICES_RESTART_RESULT|response\.text/);
});
