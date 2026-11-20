"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const access=require("../lib/access");
const handler=require("../api/browser-device");
test("registration requires same origin and approval binds to the secret cookie",()=>{
  const req={method:"POST",headers:{origin:access.ORIGIN,"content-type":"application/json","content-length":"21"},body:{action:"register"}};
  const res={headers:{},setHeader(k,v){this.headers[k]=v},status(n){this.code=n;return this},json(v){this.body=v}};
  const old=process.env.ODIN_TRUSTED_BROWSER_ID;
  try {
    handler({...req,headers:{...req.headers,origin:"https://example.com"}},res);
    assert.equal(res.code,403);
    handler(req,res);
    const id=res.body.browser_id, cookie=res.headers["Set-Cookie"];
    assert.match(id,/^[0-9a-f]{32}$/);
    assert.match(cookie,/Secure; HttpOnly; SameSite=Strict/);
    req.headers.cookie=cookie.split(";")[0];
    delete process.env.ODIN_TRUSTED_BROWSER_ID;
    assert.equal(access.authorized(req),false);
    process.env.ODIN_TRUSTED_BROWSER_ID=id;
    assert.equal(access.authorized(req),true);
    assert.equal(access.authorized({...req,headers:{cookie:"__Host-odin-device="+id}}),false);
    req.body.action="forget";
    handler(req,res);
    assert.match(res.headers["Set-Cookie"],/Max-Age=0/);
  } finally {
    if(old===undefined)delete process.env.ODIN_TRUSTED_BROWSER_ID;
    else process.env.ODIN_TRUSTED_BROWSER_ID=old;
  }
});
