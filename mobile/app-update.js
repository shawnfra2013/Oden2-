"use strict";
(() => {
  const banner=document.getElementById("appUpdateStatus");
  const apply=document.getElementById("applyAppUpdate");
  const installed=document.querySelector('meta[name="odin-release"]').content;
  let next="", checking=false;
  function announce(msg){banner.hidden=false;banner.textContent=msg;}
  function busy(){
    return state.liveRefresh || privateState.sending || relayLocal.sending || document.querySelector('#sealedSend[aria-busy="true"]') ||
      privateState.token || privateState.history.length || document.querySelector("#sealedAnswer").textContent ||
      Array.from(document.querySelectorAll("input:not([type=checkbox]),textarea")).some(el=>el.value);
  }
  function reload(){
    const url=new URL(location.href);
    url.searchParams.set("odin_release",next);
    const active=document.querySelector("[data-tab].active");
    if(active) url.hash=active.dataset.tab;
    location.replace(url.href);
  }
  async function check(manual=false){
    if(checking || document.hidden) return;
    checking=true;
    try {
      const url=new URL("/",location.origin);url.searchParams.set("odin_check",Date.now());
      const response=await fetch(url,{cache:"no-store",signal:AbortSignal.timeout(12000)});
      if(!response.ok) throw Error();
      const html=await response.text();
      const version=html.match(/<meta name="odin-release" content="([0-9a-f]{16})">/);
      if(!version) throw Error();
      if(version[1]!==installed){
        next=version[1];
        if(!busy()){reload();return;}
        announce("App update ready. Apply it when you finish this session."); apply.hidden=false;
      }else if(manual){announce("App is current. Status refresh requested.");}
    }catch{if(manual)announce("Could not check for an app update. Your current screen is available.");}
    finally{checking=false;}
  }
  apply.onclick=()=>{if(next && (!busy() || window.confirm("Reload now? Unsaved drafts and this tab’s temporary session may be cleared.")))reload();};
  document.getElementById("refreshBtn").addEventListener("click",()=>{refreshFromDevice();checkCapabilities();window.dispatchEvent(new Event("odin-refresh-settings"));check(true);});
  const tab=location.hash.slice(1);
  if(["overview","activity","chat","system"].includes(tab)) navigate(tab);
  window.addEventListener("pageshow",()=>check());
  window.addEventListener("online",()=>check());
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)check();});
})();
