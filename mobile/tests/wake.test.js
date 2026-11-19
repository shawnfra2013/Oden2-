"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const {Readable} = require("node:stream");
const {createHmac} = require("node:crypto");
const handler = require("../api/wake");
const wake = require("../lib/wake");

test("only signed inbox pushes wake diagnostics; invalid signatures have no effect", async t => {
  t.mock.method(wake, "notify", async () => true);
  const secret = "w".repeat(32);
  process.env.ODIN_WAKE_WEBHOOK_SECRET = secret;
  t.after(() => delete process.env.ODIN_WAKE_WEBHOOK_SECRET);
  const raw = JSON.stringify({repository:{full_name:"shawnfra2013/Oden2-"},ref:"refs/heads/odin-bridge-inbox"});
  for (const [key, code] of [["wrong",403],[secret,202]]) {
    const req = Readable.from([Buffer.from(raw)]);
    Object.assign(req,{method:"POST",headers:{"x-github-event":"push","x-hub-signature-256":
      "sha256="+createHmac("sha256",key).update(raw).digest("hex")}});
    const res = {setHeader(){},status(value){this.code=value;return this;},end(){}};
    await handler(req,res);
    assert.equal(res.code,code);
  }
  assert.equal(wake.notify.mock.callCount(),1);
  assert.deepEqual(wake.notify.mock.calls[0].arguments,["bridge"]);
});

test("sync wakes only after successful main push checks", () => {
  const data = {repository:{full_name:"shawnfra2013/Oden2-"},action:"completed",
    workflow_run:{name:"Odin Checks",head_branch:"main",event:"push",conclusion:"success"}};
  assert.equal(handler._test.eventLane("workflow_run",data),"sync");
  data.workflow_run.conclusion="failure";
  assert.equal(handler._test.eventLane("workflow_run",data),null);
});
