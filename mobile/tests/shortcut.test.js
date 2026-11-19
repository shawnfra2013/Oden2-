"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");

test("safe device tasks fill existing composer; no raw command controls",()=>{
  const html=fs.readFileSync(path.resolve(__dirname,"../index.html"),"utf8");
  const script=fs.readFileSync(path.resolve(__dirname,"../app.js"),"utf8");
  for(const command of ["/ping","/status","/task git-status","/task queue-status"]){
    assert.ok(html.includes('data-relay-quick="'+command+'"'));
  }
  assert.ok(script.includes("button.dataset.relayQuick"));
  assert.ok(script.includes('row.append(create("div","relay-entry-status",stateLabel))'));
  assert.doesNotMatch(html,/data-relay-quick="(?:sh |rm |exec )/);
});
