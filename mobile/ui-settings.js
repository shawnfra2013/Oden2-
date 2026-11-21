"use strict";
(() => {
  const heading = document.querySelector("[data-odin-chat-heading]");
  const original = heading.textContent;
  function paint(settings) {
    document.documentElement.dataset.odinAccent = settings.accent;
    document.documentElement.dataset.odinSize = settings.size;
    heading.textContent = settings.heading || original;
  }
  const panel = document.getElementById("uiEdits");
  if (!panel) {
    fetch("/ui-settings.json").then(r => r.json()).then(paint).catch(() => {});
    return;
  }
  const el = id => document.getElementById(id);
  const status = text => { el("editStatus").textContent = text; };
  let saved, busy = false;
  const draft = () => ({heading:el("editHeading").value, accent:el("editAccent").value, size:el("editSize").value});
  function fill(settings) {
    el("editHeading").value = settings.heading;
    el("editAccent").value = settings.accent;
    el("editSize").value = settings.size;
    paint(settings);
  }
  async function request(url, data) {
    const response = await fetch(url, data ? {method:"POST", headers:{"Content-Type":"application/json","X-Odin-Request":"chat"}, body:JSON.stringify(data)} : {cache:"no-store"});
    const result = await response.json();
    if (!response.ok) throw Error(result.error || "Request failed");
    return result;
  }
  function display(row) {
    saved = row; fill(row.settings);
    status(row.pending ? row.pending + " approved edit(s) waiting for upload." :
      row.branch ? "Uploaded for review: " + row.branch : "Ready for an offline edit.");
  }
  async function load() {
    try { display(await request("/api/ui-edits")); } catch(e) {status(e.message);}
  }
  panel.addEventListener("input", () => {if (saved) { paint(draft()); status("Local preview. Approve to save and queue upload."); }});
  el("editReload").onclick = load;
  el("editApprove").onclick = async () => {
    if (!saved || busy) return;
    busy = true;
    try {display(await request("/api/ui-edits",{settings:draft(),version:saved.version}));}
    catch(e) {status(e.message);} finally {busy=false;}
  };
  el("editSuggest").onclick = async () => {
    if (!saved || busy) return;
    busy = true;
    try {
      status("Waiting for the local model…");
      const brief = el("editBrief").value.trim();
      if (!brief) throw Error("Describe one appearance change first.");
      const response = await request("/api/chat", {message:
        "Update these UI settings according to the request. Keep unspecified values. Reply only with one JSON object. " +
        'Keys: heading (plain text up to 48 characters), accent (original, teal or gold), size (standard or large). ' +
        "Current: " + JSON.stringify(draft()) + ". Request: " + brief.slice(0,200),
        local_options:{reference:"",quick:true}});
      const raw = response.answer.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
      let proposed;
      try { proposed = JSON.parse(raw); } catch { throw Error("Odin did not return valid settings. Your draft is still available."); }
      if (!proposed || typeof proposed.heading !== "string" || !/^[\p{L}\p{N}_ .!?'-]{0,48}$/u.test(proposed.heading) ||
          !["original","teal","gold"].includes(proposed.accent) || !["standard","large"].includes(proposed.size))
        throw Error("Odin returned an unsupported setting. Your draft is still available.");
      fill(proposed); status("Model suggestion ready. Review the preview before approving.");
    } catch(e) {status(e.message);} finally {busy=false;}
  };
  load();
})();
