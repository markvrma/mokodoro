// Run: node tests/lib.test.mjs
import assert from "node:assert/strict";
import { parse, render } from "../lib.js";

assert.equal(parse("25min"), 1500);
assert.equal(parse("1hr"), 3600);
assert.equal(parse("90s"), 90);
assert.equal(parse("1h30m"), 5400);
assert.equal(parse("25"), 1500);
assert.equal(parse("0min"), null);
assert.equal(parse("abc"), null);
assert.equal(parse(""), null);

const lines = render(1500).split("\n");
assert.equal(lines.length, 4); // 15 pixel rows / 4 dots per braille row, rounded up
assert.equal(render(3600).split("\n").length, 4); // 1hr shows 60:00, no hour column

console.log("lib.js: all checks passed");
