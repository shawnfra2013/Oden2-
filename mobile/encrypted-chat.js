"use strict";
(() => {
  const el = id => document.getElementById(id);
  const status = message => { el("sealedStatus").textContent = message; };
  const bytes = text => Uint8Array.from(atob(text), c => c.charCodeAt(0));
  const encode = value => btoa(String.fromCharCode(...value));
  const text = new TextEncoder();
  const database = new Promise((resolve,reject) => {
    const req = indexedDB.open("odin-encrypted-chat",1);
    req.onupgradeneeded = () => req.result.createObjectStore("state");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(Error("Browser storage unavailable"));
  });
  async function state(name, value) {
    const db = await database;
    return new Promise((resolve,reject) => {
      const tx = db.transaction("state", value === undefined ? "readonly" : "readwrite");
      const store = tx.objectStore("state");
      const req = value === undefined ? store.get(name) : store.put(value,name);
      tx.oncomplete = () => resolve(req.result);
      tx.onabort = tx.onerror = () => reject(Error("Browser storage unavailable"));
    });
  }
  const aad = (id, direction) => text.encode("odin-chat-v1/"+id+"/"+direction);
  const post = body => authenticatedPost("/api/encrypted-chat",body,privateState.token);
  el("sealedPair").onclick = async () => {
    try {
      if (await state("pending")) throw Error("Finish or dismiss the pending reply first");
      const raw = bytes(el("sealedCode").value.trim());
      if (raw.length !== 32) throw Error("Invalid pairing code");
      await state("key",await crypto.subtle.importKey("raw",raw,"AES-GCM",false,["encrypt","decrypt"]));
      el("sealedCode").value = "";
      status("Browser paired");
    } catch (e) { status(e.message); }
  };
  let fileVersion = 0;
  window.addEventListener("odin-session-lock", () => { fileVersion++; });
  el("sealedFile").onchange = async event => {
    const version = ++fileVersion;
    const file = event.target.files[0];
    if (!file) return;
    try {
      if (!privateState.connected) throw Error("Unlock private access first");
      if (file.size > 1600) throw Error("Choose a text excerpt of up to 1,600 UTF-8 bytes");
      const excerpt = new TextDecoder("utf-8", {fatal:true}).decode(await file.arrayBuffer());
      if (version !== fileVersion || !privateState.connected) return;
      const box = el("sealedQuestion");
      const draft = [box.value.trim(), "File excerpt:", excerpt].filter(Boolean).join("\n");
      if (draft.length > box.maxLength) throw Error("Shorten the question before attaching the excerpt");
      box.value = draft;
      status("File loaded locally. Review the question before sending.");
    } catch (e) { status(e.message); }
    finally { if (version === fileVersion) event.target.value = ""; }
  };
  let locked = false;
  async function deliver() {
    if (locked) return;
    locked = true;
    try {
      if (!privateState.connected) throw Error("Unlock private access first");
      const key = await state("key");
      if (!key) throw Error("Pair this browser with Odin first");
      let pending = await state("pending");
      if (!pending) {
        const message = el("sealedQuestion").value.trim();
        if (!message || text.encode(message).length > 12000 || message.length > 4000) throw Error("Enter a question of up to 4,000 characters");
        const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), b=>b.toString(16).padStart(2,"0")).join("");
        const iv = crypto.getRandomValues(new Uint8Array(12));
        const encrypted = await crypto.subtle.encrypt({name:"AES-GCM",iv,additionalData:aad(id,"question")},key,text.encode(message));
        pending = {id,sealed:encode([...iv,...new Uint8Array(encrypted)])};
        await state("pending",pending);
      }
      status("Submitting encrypted message…");
      await post(pending);
      el("sealedQuestion").value = "";
      for (let i=0;i<24;i++) {
        if (!privateState.connected) throw Error("Session locked");
        const result = await post({id:pending.id});
        if (result.sealed) {
          const data = bytes(result.sealed);
          const clear = await crypto.subtle.decrypt({name:"AES-GCM",iv:data.slice(0,12),additionalData:aad(pending.id,"answer")},key,data.slice(12));
          if (!privateState.connected) throw Error("Session locked");
          el("sealedAnswer").textContent = new TextDecoder().decode(clear);
          await state("pending",null);
          status("Reply received from your local model");
          return;
        }
        status("Waiting for Odin…");
        await new Promise(r=>setTimeout(r,5000));
      }
      status("Still pending. Check the same message again.");
    } catch (e) { status(e.message); }
    finally { locked = false; }
  }
  el("sealedSend").onclick = deliver;
  el("sealedDismiss").onclick = async () => {
    if (!locked) { await state("pending",null); status("Pending receipt dismissed on this browser"); }
  };
  state("pending").then(p=>{ if (p) status("Pending message saved. Select Send or check reply to resume."); }).catch(e=>status(e.message));
})();
