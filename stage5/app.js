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
    " | "+(health.provider==="local"?"On-device model · no cloud calls":health.provider)+" | AI: "+(health.ai_enabled?"enabled":"disabled");
  el("localOptions").hidden=health.provider!=="local";
  aiReady=health.ai_enabled===true;
  el("send").disabled=sending||!aiReady;
  if(!sending)el("chatStatus").textContent=health.ai_enabled?
    "AI available. Responses are not independently verified.":
    "Local model is not enabled.";
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

const restartKey = "odin-restart-request";
let restartRequest;
let restartDeadline = 0;
let restartTimer;
try {
  const saved = sessionStorage.getItem(restartKey);
  if (/^[0-9a-f]{32}$/.test(saved || "")) restartRequest = saved;
} catch {}
if (restartRequest) {
  restartDeadline = Date.now() + 300000;
  checkRestart();
}

async function checkRestart() {
  clearTimeout(restartTimer);
  const button = el("restartServices");
  button.disabled = true;
  try {
    const result = await getJSON("/api/restart?id=" + restartRequest);
    if (result.phase === "finished") {
      el("restartStatus").textContent = result.reply;
      clearRestart();
      return;
    }
    el("restartStatus").textContent = "Restart requested. Waiting for Odin...";
  } catch {
    el("restartStatus").textContent = "Waiting for Odin to reconnect...";
  }
  if (Date.now() >= restartDeadline) {
    el("restartStatus").textContent = "Odin did not return a restart receipt. Refresh to check again.";
    button.disabled = false;
    return;
  }
  restartTimer = setTimeout(checkRestart, 2500);
}

function clearRestart() {
  restartRequest = undefined;
  try { sessionStorage.removeItem(restartKey); } catch {}
  el("restartServices").disabled = false;
}

el("restartServices").onclick = async () => {
  if (restartRequest) {
    restartDeadline = Date.now() + 300000;
    checkRestart();
    return;
  }
  if (!window.confirm("Restart Odin's configured services? The app will disconnect briefly.")) return;
  el("restartServices").disabled = true;
  restartRequest = Array.from(crypto.getRandomValues(new Uint8Array(16)),
    byte => byte.toString(16).padStart(2, "0")).join("");
  restartDeadline = Date.now() + 300000;
  try { sessionStorage.setItem(restartKey, restartRequest); } catch {}
  try {
    const response = await fetch("/api/restart", {
      method: "POST",
      headers: {"Content-Type":"application/json", "X-Odin-Request":"chat"},
      body: JSON.stringify({id: restartRequest})
    });
    if (response.status !== 202) {
      const result = await response.json();
      el("restartStatus").textContent = result.error || "Restart unavailable.";
      clearRestart();
      return;
    }
  } catch {
    // Restart may have disconnected the response after Odin accepted it.
  }
  checkRestart();
};

el("refreshApp").onclick = () => {
  if (sending) return;
  if (el("message").value.trim() && !window.confirm("Reload Odin and discard the current draft?")) {
    refreshHealth();
    refreshTasks();
    return;
  }
  window.location.reload();
};

let practiceView = 0;
async function showPractice() {
 const view = ++practiceView;
 if (!el("practicePanel").open) return;
 try {
  const followup = el("practiceSeries").value === "followup";
  const book = await getJSON(followup ? "/api/practice-followup" : "/api/practice");
  if (view !== practiceView) return;
  el("practiceSummary").textContent = (book.passed || 0) + " passed, " + (book.missed || 0) +
    " missed. " + (book.review_skills?.length ? "Review repeated errors in " + book.review_skills.join(", ") :
    "Keep current weights.");
  el("practiceNotes").replaceChildren(...book.notes.map(note => {
   const item = document.createElement("li");
   const grade = note.reviewed_state === "pass" && note.state === "miss" ? "Pass after capitalization review" : note.state;
   item.textContent = [note.question, grade, note.answer === undefined ? "" : "Answer: " + note.answer,
     note.expected === undefined ? "" : "Expected: " + note.expected, grade === note.state ? note.note : "Meaning matches the action key."].filter(Boolean).join(" · ");
   return item;
  }));
 } catch { el("practiceSummary").textContent = "Practice notebook unavailable."; }
}
el("practicePanel").addEventListener("toggle", showPractice);
el("practiceSeries").addEventListener("change", showPractice);
