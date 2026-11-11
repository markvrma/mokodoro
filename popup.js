import { parse } from "./lib.js";

const input = document.getElementById("dur");
const err = document.getElementById("err");

// Opens the timer as its own tab; that tab owns the clock and the float window.
function start(text) {
  const secs = parse(text);
  if (!secs) {
    err.textContent = `cannot read "${text}"`;
    return;
  }
  chrome.tabs.create({ url: chrome.runtime.getURL(`timer.html?secs=${secs}&float=1`) });
  window.close();
}

document.getElementById("go").addEventListener("click", () => start(input.value));
input.addEventListener("keydown", (e) => { if (e.key === "Enter") start(input.value); });
for (const b of document.querySelectorAll("button[data-d]")) {
  b.addEventListener("click", () => start(b.dataset.d));
}
input.focus();
input.select();
