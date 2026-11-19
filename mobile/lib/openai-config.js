"use strict";

function openAiApiKey() {
  return process.env.OPENAI_API_KEY || process.env.open_api_keyy;
}

module.exports = {openAiApiKey};
