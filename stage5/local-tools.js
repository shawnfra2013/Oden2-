"use strict";
(() => {
  const get = id => document.getElementById(id);
  const tools = get("localTools");
  const question = get(tools.dataset.question);
  const answer = get(tools.dataset.answer);
  const status = get("localToolsStatus");
  const synthesis = window.speechSynthesis;
  let recognition;
  function clear() {
    if (recognition) {
      recognition.onresult = null;
      recognition.abort();
      recognition = null;
    }
    synthesis?.cancel();
    status.textContent = "";
  }
  window.addEventListener("pagehide", clear);
  window.addEventListener("odin-session-lock", clear);
  get("stopVoice").onclick = clear;
  get("readLocal").onclick = () => {
    const reply = answer.textContent.trim();
    if (!reply) { status.textContent = "Send a question first."; return; }
    const voices = synthesis?.getVoices().filter(v => v.localService) || [];
    const voice = voices.find(v => v.lang.split("-")[0] === navigator.language.split("-")[0]) || voices[0];
    if (!voice) { status.textContent = "No installed local voice is available in this browser."; return; }
    clear();
    const speech = new SpeechSynthesisUtterance(reply);
    speech.voice = voice;
    speech.lang = voice.lang;
    speech.onerror = () => { status.textContent = "Playback stopped or unavailable."; };
    synthesis.speak(speech);
  };
  get("dictateLocal").onclick = async () => {
    const Engine = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Engine || !("processLocally" in Engine.prototype) || !Engine.available) {
      status.textContent = "This browser cannot confirm offline dictation support."; return;
    }
    clear();
    const instance = new Engine();
    recognition = instance;
    try {
      instance.processLocally = true;
      instance.lang = navigator.language;
      const availability = await Engine.available({langs:[instance.lang], processLocally:true});
      if (recognition !== instance) return;
      if (availability !== "available") { status.textContent = "Install a local speech pack for this language first."; return; }
      instance.onresult = event => {
        if (recognition !== instance) return;
        const value = [question.value.trim(), event.results[0][0].transcript].filter(Boolean).join(" ");
        if (value.length > question.maxLength) { status.textContent = "Dictation exceeds the question limit."; return; }
        question.value = value;
        status.textContent = "Review the question before sending.";
      };
      instance.onerror = () => { status.textContent = "Local dictation unavailable."; };
      instance.onend = () => { if (recognition === instance) recognition = null; };
      instance.start();
      status.textContent = "Listening on this device…";
    } catch { status.textContent = "Local dictation unavailable."; }
  };
  // The saved bookmark runs only when the reader selects it on a page.
  function clipPage() {
    const article = document.querySelector("article, main") || document.body;
    const excerpt = (String(window.getSelection()).trim() || article.innerText).slice(0, 1200);
    window.prompt("Copy this excerpt into your Odin question or project note.", excerpt);
  }
  get("clipBookmark").href = "javascript:(" + clipPage.toString() + ")();void 0";
})();
