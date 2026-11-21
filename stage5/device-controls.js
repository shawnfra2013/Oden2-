"use strict";
(() => {
  const get = id => document.getElementById(id);
  const panel = get("deviceControls");
  const labels = {chat:"Open chat", notebook:"Open notebook", editor:"Open UI editor"};
  const store = "odin-device-controls-v1";
  const actions = {
    chat: () => get("message").focus(),
    notebook: () => openPanel("practicePanel"),
    editor: () => openPanel("uiEdits")
  };
  let bindings = {};
  try {
    const saved = JSON.parse(localStorage.getItem(store) || "{}");
    for (const [key, action] of Object.entries(saved))
      if (Object.hasOwn(actions, action)) bindings[key] = action;
  } catch {}
  let capture = null, timer = 0, held = new Map();
  function openPanel(id) {
    const target = get(id);
    target.open = true;
    target.querySelector("summary").focus();
    target.scrollIntoView({block:"nearest"});
  }
  function render() {
    get("buttonList").replaceChildren(...Object.entries(bindings).map(([key, action]) => {
      const li = document.createElement("li");
      li.textContent = labels[action] + " — " + key;
      return li;
    }));
  }
  function save(next) {
    try {localStorage.setItem(store, JSON.stringify(next)); bindings = next; render(); return true;}
    catch {get("buttonStatus").textContent = "Browser storage unavailable."; return false;}
  }
  function press(key) {
    if (capture) {
      const action = capture;
      capture = null;
      const next = {...bindings};
      for (const old of Object.keys(next)) if (next[old] === action) delete next[old];
      next[key] = action;
      if (save(next)) get("buttonStatus").textContent = labels[action] + " assigned to " + key + ".";
      return true;
    }
    if (!Object.hasOwn(bindings, key)) return false;
    actions[bindings[key]]();
    return true;
  }
  function editable() {
    return document.activeElement?.matches("textarea,input,select,[contenteditable=true]");
  }
  window.addEventListener("keydown", event => {
    if (document.hidden || event.repeat || event.ctrlKey || event.altKey || event.metaKey || event.shiftKey ||
        editable() || !event.code) return;
    if (capture && event.code === "Escape") { cancel(); return; }
    if (/^(Tab|Enter|Space|Escape|Shift|Control|Meta|Alt|Power|AudioVolume|Browser)/.test(event.code)) return;
    if (press("key " + event.code)) event.preventDefault();
  });
  function scan() {
    timer = 0;
    if (document.hidden || !document.hasFocus()) {held.clear(); return;}
    let pads;
    try { pads = Array.from(navigator.getGamepads?.() || []).filter(Boolean); }
    catch {return;}
    const next = new Map();
    for (const pad of pads) {
      const previous = held.get(pad.index);
      const buttons = pad.buttons.map(b => b.pressed);
      next.set(pad.index, buttons);
      buttons.forEach((down, i) => {
        if (previous && down && !previous[i] && (capture || !editable()))
          press("pad " + pad.id.slice(0,100) + " button " + i);
      });
    }
    held = next;
    if (pads.length && (capture || Object.keys(bindings).some(k => k.startsWith("pad ")))) {
      timer = window.setTimeout(scan, 40);
    }
  }
  function start() {clearTimeout(timer); scan();}
  function cancel() {capture = null; get("buttonStatus").textContent = ""; }
  get("buttonBind").onclick = () => {
    capture = get("buttonAction").value;
    get("buttonStatus").textContent = "Press and release a controller button or a keyboard key. Escape cancels.";
    start();
  };
  get("buttonCancel").onclick = cancel;
  get("buttonRemove").onclick = () => {
    cancel();
    const action = get("buttonAction").value;
    if (save(Object.fromEntries(Object.entries(bindings).filter(([,a]) => a !== action))))
      get("buttonStatus").textContent = "Assignment removed.";
  };
  panel.addEventListener("toggle", () => {if (!panel.open) cancel();});
  window.addEventListener("gamepadconnected", start);
  window.addEventListener("focus", start);
  window.addEventListener("blur", () => {cancel(); clearTimeout(timer); held.clear();});
  document.addEventListener("visibilitychange", start);
  render(); start();
})();
