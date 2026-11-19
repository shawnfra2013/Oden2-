"use strict";
const el=id=>document.getElementById(id);
const storageKey="odin-stage5-conversation";
let conversationId;
try{
 const saved=sessionStorage.getItem(storageKey);
 if(/^[0-9a-f]{32}$/.test(saved||""))conversationId=saved;
}catch{}
function selectConversation(id){
 conversationId=id;
 try{
  if(id)sessionStorage.setItem(storageKey,id);
  else sessionStorage.removeItem(storageKey);
 }catch{}
}
el("newChat").addEventListener("click",()=>{
 selectConversation(undefined);
 el("answer").textContent="";
 el("message").value="";
 el("chatStatus").textContent="New conversation.";
});
async function getJSON(path){
 const response=await fetch(path,{cache:"no-store"});
 if(!response.ok)throw Error("HTTP "+response.status);
 return response.json();
}
let checking=false;
let sending=false;
let aiReady=false;
let retry;
async function refreshHealth(){
 if(checking)return;
 checking=true;
 clearTimeout(retry);
 try{
  const health=await getJSON("/api/health");
  el("health").textContent="Backend: "+health.status+
    " | AI: "+(health.ai_enabled?"enabled":"disabled");
  aiReady=health.ai_enabled===true;
  el("send").disabled=sending||!aiReady;
  if(!sending)el("chatStatus").textContent=health.ai_enabled?
    "AI available. Responses are not independently verified.":
    "AI disabled during isolated testing.";
 }catch(e){
  aiReady=false;
  el("health").textContent="Backend unavailable: "+e.message;
  el("send").disabled=true;
  if(!sending)el("chatStatus").textContent="Connection lost. Retrying in 5 seconds.";
  retry=setTimeout(refreshHealth,5000);
 }finally{
  checking=false;
 }
}
el("send").addEventListener("click",async()=>{
 const message=el("message").value.trim();
 if(!message||sending||!aiReady)return;
 sending=true;
 el("send").disabled=true;
 el("newChat").disabled=true;
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
    selectConversation(undefined);
    throw Error("Conversation expired. Send again to start a new chat.");
   }
   throw Error(result.error||"Request failed");
  }
  selectConversation(result.conversation_id);
  el("answer").textContent=result.answer;
  el("chatStatus").textContent="Response received · Unverified · "+
   (result.persisted?"Saved":"Not saved");
 }catch(e){
  if(e instanceof TypeError){aiReady=false;retry=setTimeout(refreshHealth,1000);}
  el("chatStatus").textContent=e.message;
 }finally{
  el("newChat").disabled=false;
  sending=false;
  el("send").disabled=!aiReady;
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
el("reconnect").addEventListener("click",()=>{refreshHealth();refreshTasks();});
window.addEventListener("online",refreshHealth);
document.addEventListener("visibilitychange",()=>{if(!document.hidden)refreshHealth();});
refreshHealth();
refreshTasks();
