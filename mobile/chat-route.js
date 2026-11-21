"use strict";
const odinRoute = (() => {
  const el = id => document.getElementById(id);
  const defaults = {bridge:false, model:"local", mode:"plan"};
  let prefs = {...defaults};
  try {
    const stored = JSON.parse(localStorage.getItem("odin.chat.route.v1"));
    if (stored) prefs = {bridge:stored.bridge === true,model:stored.model === "cloud"?"cloud":"local",mode:stored.mode === "work"?"work":"plan"};
  } catch {}
  function show() {
    el("deviceBridge").checked=prefs.bridge;
    el("chatModel").value=prefs.model;
    el("chatMode").value=prefs.mode;
    el("localChatPanel").hidden=prefs.model!=="local" || !prefs.bridge;
    el("onlineChatPanel").hidden=prefs.model!=="cloud";
    el("deviceWorkPanel").hidden=!prefs.bridge || prefs.mode!=="work";
    el("routeStatus").textContent = prefs.model==="cloud" ? "Online model · Uses the host’s cloud API budget." :
      prefs.bridge ? "Odin handheld · Uses your local model over the private mailbox." :
      "Bridge off. Turn it on to reach the handheld from this phone. On Odin itself, local chat works offline.";
    el("modeStatus").textContent=prefs.mode==="plan"?"Plan gives you steps. Device actions are paused.":"Work drafts the requested result. Choose a device action separately.";
  }
  function change() {
    prefs={bridge:el("deviceBridge").checked,model:el("chatModel").value,mode:el("chatMode").value};
    try {localStorage.setItem("odin.chat.route.v1",JSON.stringify(prefs));} catch {}
    show(); window.dispatchEvent(new Event("odin-route-change"));
  }
  ["deviceBridge","chatModel","chatMode"].forEach(id=>el(id).addEventListener("change",change));
  show();
  return {get bridge(){return prefs.bridge;},get model(){return prefs.model;},get mode(){return prefs.mode;},
    work:()=>prefs.bridge && prefs.mode==="work"};
})();
