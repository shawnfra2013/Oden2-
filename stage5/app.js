"use strict";
const el=id=>document.getElementById(id);
const storageKey="odin-stage5-conversation";
const noteKey="odin-local-project-note";
const noteSize=value=>new TextEncoder().encode(value).byteLength;
try { el("note").value=localStorage.getItem(noteKey)||""; } catch {}
el("saveNote").onclick=()=>{
 try {
  if(noteSize(el("note").value)>1600)throw Error("Use a shorter excerpt.");
  localStorage.setItem(noteKey,el("note").value);
  el("noteStatus").textContent="Saved on this browser.";
 } catch(e){el("noteStatus").textContent=e.message;}
};
el("forgetNote").onclick=()=>{
 try {
  localStorage.removeItem(noteKey);el("note").value="";el("useNote").checked=false;
  el("noteFile").value="";el("noteStatus").textContent="Saved note removed.";
 } catch(e){el("noteStatus").textContent=e.message;}
};
el("noteFile").onchange=async event=>{
 const file=event.target.files[0];
 if(!file)return;
 try {
  if(file.size>1600)throw Error("Paste a shorter excerpt (up to 1,600 UTF-8 bytes).");
  el("note").value=new TextDecoder("utf-8",{fatal:true}).decode(await file.arrayBuffer());
  el("noteStatus").textContent="Loaded. Select Include to use this note.";
 } catch(e){el("noteStatus").textContent=e.message;}
};
el("lookup").onclick=async()=>{
 const name=el("symbol").value.trim();
 el("sourceMatches").replaceChildren();el("lookup").disabled=true;
 try{
  const data=await getJSON("/api/source?symbol="+encodeURIComponent(name));
  el("sourceStatus").textContent=data.matches.length?"Select an excerpt to preview.":"No matching function in the indexed Python modules.";
  for(const item of data.matches){
   const button=document.createElement("button");
   button.type="button";button.textContent=item.label;
   button.onclick=()=>{
    el("note").value=item.reference;el("notePanel").open=true;el("useNote").checked=true;
    el("noteStatus").textContent="Selected source excerpt. Review before sending.";
   };
   el("sourceMatches").append(button);
  }
 }catch(e){el("sourceStatus").textContent=e.message;}
 finally{el("lookup").disabled=false;}
};
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
    " | "+(health.provider==="local"?"On-device model · zero OpenAI usage":health.provider)+" | AI: "+(health.ai_enabled?"enabled":"disabled");
  el("localOptions").hidden=health.provider!=="local";
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
  const body={message,conversation_id:conversationId};
  if(!el("localOptions").hidden){
   const reference=el("useNote").checked?el("note").value:"";
   if(noteSize(reference)>1600)throw Error("Shorten the project excerpt.");
   body.local_options={reference,quick:el("quick").checked};
  }
  const response=await fetch("/api/chat",{
   method:"POST",
   headers:{"Content-Type":"application/json","X-Odin-Request":"chat"},
   body:JSON.stringify(body)
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
   (result.persisted?"Saved":"Not saved")+" · "+(result.elapsed_ms/1000).toFixed(1)+" s";
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

async function watchDisconnectTest(){
 const panel=el("disconnectTest");
 if(!panel.open||panel.dataset.watching)return;
 panel.dataset.watching="1";
 try{
  while(panel.open){
   try{
    const r=await getJSON("/api/disconnect-test");
    let text="Waiting for /ping-disconnect-test in the private Odin Device Inbox.";
    if(r.state==="sent")text="Delivered. Attempts: "+r.attempts+". Failed deliveries: "+r.failures+".";
    else if(r.seconds>0)text="Reply saved. Turn Odin Wi-Fi OFF now. Delivery unlocks in "+r.seconds+" seconds.";
    else if(r.failures>0)text="Failed delivery recorded. Turn Wi-Fi ON now.";
    else if(r.id)text="Waiting for the first delivery attempt. Keep Wi-Fi off.";
    el("disconnectStatus").textContent=text+(r.id?" Request "+r.id.slice(-8):"");
   }catch{el("disconnectStatus").textContent="Local status unavailable. Keep Wi-Fi on or restore it.";}
   await new Promise(resolve=>setTimeout(resolve,1000));
  }
 }finally{delete panel.dataset.watching;}
}
el("disconnectTest").addEventListener("toggle",watchDisconnectTest);

el("practicePanel").addEventListener("toggle", async () => {
 if (!el("practicePanel").open) return;
 try {
  const book = await getJSON("/api/practice");
  el("practiceSummary").textContent = (book.passed || 0) + " passed, " + (book.missed || 0) +
    " missed. " + (book.review_skills?.length ? "Review repeated errors in " + book.review_skills.join(", ") :
    "Keep current weights.");
  el("practiceNotes").replaceChildren(...book.notes.map(note => {
   const item = document.createElement("li");
   item.textContent = [note.question, note.state, note.answer === undefined ? "" : "Answer: " + note.answer,
     note.expected === undefined ? "" : "Expected: " + note.expected, note.note].filter(Boolean).join(" · ");
   return item;
  }));
 } catch { el("practiceSummary").textContent = "Practice notebook unavailable."; }
});
