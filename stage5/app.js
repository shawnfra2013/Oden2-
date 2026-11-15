"use strict";
const el=id=>document.getElementById(id);
async function getJSON(path){
 const response=await fetch(path,{cache:"no-store"});
 if(!response.ok)throw Error("HTTP "+response.status);
 return response.json();
}
async function refresh(){
 try{
  const health=await getJSON("/api/health");
  el("health").textContent="Backend: "+health.status+
    " | AI: "+(health.ai_enabled?"enabled":"disabled");
  el("send").disabled=!health.ai_enabled;
  el("chatStatus").textContent=health.ai_enabled?
    "AI available. Responses are not independently verified.":
    "AI disabled during isolated testing.";
  const tasks=await getJSON("/api/tasks");
  el("tasks").textContent=JSON.stringify(tasks.counts,null,2);
 }catch(e){
  el("health").textContent="Backend unavailable: "+e.message;
  el("send").disabled=true;
 }
}
el("send").addEventListener("click",async()=>{
 const message=el("message").value.trim();
 if(!message)return;
 el("send").disabled=true;
 el("chatStatus").textContent="Waiting for AI response...";
 try{
  const response=await fetch("/api/chat",{
   method:"POST",
   headers:{"Content-Type":"application/json","X-Odin-Request":"chat"},
   body:JSON.stringify({message})
  });
  const result=await response.json();
  if(!response.ok)throw Error(result.error||"Request failed");
  el("answer").textContent=result.answer;
  el("chatStatus").textContent="Response received · Unverified · Not saved";
 }catch(e){
  el("chatStatus").textContent=e.message;
 }finally{
  el("send").disabled=false;
 }
});
refresh();
