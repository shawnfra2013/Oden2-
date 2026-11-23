"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");

test("phone diagnostics link to the private workflow and omit retired relay controls", () => {
  const html = readFileSync(join(__dirname, "../index.html"), "utf8");
  assert.match(html, /Odin-private-bridge\/actions\/workflows\/odin-private-mailbox\.yml/);
  assert.doesNotMatch(html, /data-legacy-relay|data-relay-quick|restartAllButton/);
});
