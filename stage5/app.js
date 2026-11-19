"use strict";
const el=id=>document.getElementById(id);
let conversationId;
async function getJSON(path){
 const response=await fetch(path,{cache:"no-store"});
 if(!response.ok)throw Error("HTTP "+response.status);
 return response.json();
}
async function refreshHealth(){
 try{
  const health=await getJSON("/api/health");
  el("health").textContent="Backend: "+health.status+
    " | AI: "+(health.ai_enabled?"enabled":"disabled");
  el("send").disabled=!health.ai_enabled;
  el("chatStatus").textContent=health.ai_enabled?
    "AI available. Responses are not independently verified.":
    "AI disabled during isolated testing.";
 }catch(e){
  el("health").textContent="Backend unavailable: "+e.message;
  el("send").disabled=true;
  el("chatStatus").textContent="AI availability could not be checked.";
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
   body:JSON.stringify({message,conversation_id:conversationId})
  });
  const result=await response.json();
  if(!response.ok){
   if(response.status===404&&conversationId){
    conversationId=undefined;
    throw Error("Conversation expired. Send again to start a new chat.");
   }
   throw Error(result.error||"Request failed");
  }
  conversationId=result.conversation_id;
  el("answer").textContent=result.answer;
  el("chatStatus").textContent="Response received · Unverified · "+
   (result.persisted?"Saved":"Not saved");
 }catch(e){
  el("chatStatus").textContent=e.message;
 }finally{
  el("send").disabled=false;
 }
});
async function refreshTasks(){
 try{
  const tasks=await getJSON("/api/tasks");
  el("tasks").textContent=JSON.stringify(tasks.counts,null,2);
 }catch(e){
  el("tasks").textContent="Task counts unavailable: "+e.message;
 }
}
refreshHealth();
refreshTasks();
