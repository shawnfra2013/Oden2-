"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const {webcrypto}=require("node:crypto");
const vault=require("../vault.js");
const token="private-access-token-abcdefghijklmnopqrstuvwxyz1234567890";
const password="four-unique-words-make-this-strong";

function fakeStorage(){
  const data=new Map();
  return {
    getItem(k){return data.has(k)?data.get(k):null;},
    setItem(k,v){data.set(k,String(v));},
    removeItem(k){data.delete(k);}
  };
}
test("save encrypts server bearer token and password unlock restores it",async()=>{
  const storage=fakeStorage();
  assert.equal(vault.hasSaved(storage),false);
  await vault.save(token,password,storage,webcrypto);
  assert.equal(vault.hasSaved(storage),true);
  const stored=storage.getItem(vault._test.STORAGE_KEY);
  assert.doesNotMatch(stored,/private-access-token/);
  assert.doesNotMatch(stored,/four-unique-words/);
  assert.equal(JSON.parse(stored).v,1);
  assert.equal(await vault.unlock(password,storage,webcrypto),token);
});
test("wrong password rejects without returning a token",async()=>{
  const storage=fakeStorage();
  await vault.save(token,password,storage,webcrypto);
  await assert.rejects(()=>vault.unlock("incorrect-passphrase",storage,webcrypto),
    /Incorrect password or saved access is damaged/);
});
test("tampered ciphertext rejects rather than returning corrupt credentials",async()=>{
  const storage=fakeStorage();
  await vault.save(token,password,storage,webcrypto);
  const record=JSON.parse(storage.getItem(vault._test.STORAGE_KEY));
  record.ciphertext=record.ciphertext.replace(/[A-Za-z]/,c=>c==="a"?"b":"a");
  storage.setItem(vault._test.STORAGE_KEY,JSON.stringify(record));
  await assert.rejects(()=>vault.unlock(password,storage,webcrypto),
    /Incorrect password or saved access is damaged/);
});
test("each explicit save gets a fresh random salt and IV",async()=>{
  const storage=fakeStorage();
  await vault.save(token,password,storage,webcrypto);
  const before=JSON.parse(storage.getItem(vault._test.STORAGE_KEY));
  await vault.save(token,password,storage,webcrypto);
  const after=JSON.parse(storage.getItem(vault._test.STORAGE_KEY));
  assert.notEqual(after.salt,before.salt);
  assert.notEqual(after.iv,before.iv);
});
test("short password cannot replace an existing encrypted vault",async()=>{
  const storage=fakeStorage();
  await vault.save(token,password,storage,webcrypto);
  const before=storage.getItem(vault._test.STORAGE_KEY);
  await assert.rejects(()=>vault.save(token,"short",storage,webcrypto),
    /12/);
  assert.equal(storage.getItem(vault._test.STORAGE_KEY),before);
});
test("forget removes saved access without requiring cloud credentials",async()=>{
  const storage=fakeStorage();
  await vault.save(token,password,storage,webcrypto);
  vault.forget(storage);
  assert.equal(vault.hasSaved(storage),false);
  await assert.rejects(()=>vault.unlock(password,storage,webcrypto),
    /No valid saved access/);
});
test("browser wiring offers password unlock plus manual token fallback",()=>{
  const fs=require("node:fs");
  const path=require("node:path");
  const html=fs.readFileSync(path.resolve(__dirname,"../index.html"),"utf8");
  const app=fs.readFileSync(path.resolve(__dirname,"../app.js"),"utf8");
  assert.match(html,/id="vaultUnlockForm"/);
  assert.match(html,/id="vaultSaveForm"/);
  assert.match(html,/id="vaultForget"/);
  assert.match(html,/src="\/vault\.js\?v=[a-f0-9]{16}" defer/);
  assert.ok(html.includes('src="/vault.js?') && html.indexOf('src="/vault.js?')<html.indexOf('src="/app.js?'));
  assert.match(app,/OdinVault\.unlock\(password\)/);
  assert.match(app,/OdinVault\.save\(privateState\.token,password\)/);
  assert.match(app,/OdinVault\.forget\(\)/);
  assert.doesNotMatch(app,/localStorage\.setItem\([^)]*token/i);
});
