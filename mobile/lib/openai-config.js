"use strict";

function openAiApiKey() {
  return process.env.OPENAI_API_KEY || process.env.open_api_keyy;
}

function cloudChatConfigured() {
  return Boolean(openAiApiKey() && /^[A-Za-z0-9._-]{1,100}$/.test(process.env.ODIN_OPENAI_MODEL || ""));
}

module.exports = {openAiApiKey, cloudChatConfigured};
