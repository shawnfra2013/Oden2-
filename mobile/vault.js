"use strict";
// Local encrypted credential vault. Neither the unlock password nor an
// unencrypted bearer token is stored or sent to any service.
const OdinVault=(()=>{
  const STORAGE_KEY="odin-control.local-vault.v1";
  const ITERATIONS=310000;
  const CONTEXT="odin-control:local-access:v1";
  const encoder=new TextEncoder();
  const TOKEN=/^[A-Za-z0-9._~-]{32,256}$/;
  function validate(password,token){
    if(typeof password!=="string"||password.length<12||password.length>256)
      throw Error("Choose a password of 12–256 characters");
    if(token!==undefined && (typeof token!=="string"||!TOKEN.test(token)))
      throw Error("Invalid access token");
  }
  function encode(bytes){
    let str="";
    for(const item of bytes)str+=String.fromCharCode(item);
    return btoa(str);
  }
  function decode(value,expected){
    if(typeof value!=="string"||value.length>2000||!/^[A-Za-z0-9+/]+={0,2}$/.test(value))
      throw Error("Saved access is damaged");
    const data=Uint8Array.from(atob(value),s=>s.charCodeAt(0));
    if(expected && data.length!==expected)throw Error("Saved access is damaged");
    return data;
  }
  async function derive(password,salt,crypt){
    const material=await crypt.subtle.importKey(
      "raw",encoder.encode(password),"PBKDF2",false,["deriveKey"]
    );
    return crypt.subtle.deriveKey({
      name:"PBKDF2",salt,iterations:ITERATIONS,hash:"SHA-256"
    },material,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);
  }
  async function seal(token,password,crypt=globalThis.crypto){
    validate(password,token);
    if(!crypt?.subtle || !crypt?.getRandomValues)
      throw Error("Secure local encryption is unavailable");
    const salt=crypt.getRandomValues(new Uint8Array(16));
    const iv=crypt.getRandomValues(new Uint8Array(12));
    const key=await derive(password,salt,crypt);
    const ciphertext=await crypt.subtle.encrypt({
      name:"AES-GCM",iv,additionalData:encoder.encode(CONTEXT)
    },key,encoder.encode(token));
    return {v:1,salt:encode(salt),iv:encode(iv),
      ciphertext:encode(new Uint8Array(ciphertext))};
  }
  async function open(record,password,crypt=globalThis.crypto){
    validate(password);
    if(!record || record.v!==1)throw Error("Saved access is damaged");
    if(!crypt?.subtle)throw Error("Secure local encryption is unavailable");
    const salt=decode(record.salt,16);
    const iv=decode(record.iv,12);
    const cipher=decode(record.ciphertext);
    if(cipher.length<48 || cipher.length>600)throw Error("Saved access is damaged");
    try {
      const key=await derive(password,salt,crypt);
      const plain=await crypt.subtle.decrypt({
        name:"AES-GCM",iv,additionalData:encoder.encode(CONTEXT)
      },key,cipher);
      const token=new TextDecoder("utf-8",{fatal:true}).decode(plain);
      if(!TOKEN.test(token))throw Error("Invalid decoded token");
      return token;
    }catch{
      throw Error("Incorrect password or saved access is damaged");
    }
  }
  function hasSaved(storage=localStorage){
    return storage.getItem(STORAGE_KEY)!==null;
  }
  async function save(token,password,storage=localStorage,crypt=globalThis.crypto){
    // Do not touch the existing saved vault unless encryption succeeded.
    const record=await seal(token,password,crypt);
    storage.setItem(STORAGE_KEY,JSON.stringify(record));
  }
  async function unlock(password,storage=localStorage,crypt=globalThis.crypto){
    const raw=storage.getItem(STORAGE_KEY);
    if(!raw||raw.length>3000)throw Error("No valid saved access on this device");
    let record;
    try{record=JSON.parse(raw);}catch{throw Error("Saved access is damaged");}
    return open(record,password,crypt);
  }
  function forget(storage=localStorage){storage.removeItem(STORAGE_KEY);}
  return {hasSaved,save,unlock,forget,_test:{seal,open,STORAGE_KEY}};
})();
if(typeof module!=="undefined"&&module.exports)module.exports=OdinVault;
if(typeof window!=="undefined")window.OdinVault=OdinVault;
