import { SOUNDS, render } from "./lib.js";

const $ = (id) => document.getElementById(id);
const app = $("app");
const clock = $("clock");
const bar = $("bar"); // keep the reference: getElementById can't find it once it moves into the float window
const audio = $("tick");
const floatBtn = $("float");
const pauseBtn = $("pause");
const muteBtn = $("mute");
const sndBtn = $("snd");

const params = new URLSearchParams(location.search);
const secs = Math.max(1, Number(params.get("secs")) || 1500);

// ponytail: deadline-based clock, so background-tab timer throttling only delays
// redraws, never drifts the countdown.
const st = {
  left: secs,
  deadline: performance.now() + secs * 1000,
  paused: false,
  muted: false,
  snd: 0,
  done: false,
};
let pipWin = null;

audio.src = SOUNDS[0];
audio.loop = true; // native loop, so the tick never restarts

// Audio is owned here, in one place: play iff not muted, paused, or finished.
function sync() {
  const want = !st.muted && !st.paused && !st.done;
  if (want) {
    if (audio.paused) audio.play().catch(() => {}); // blocked until a user gesture
  } else {
    audio.pause();
  }
}

function tick() {
  if (!st.paused) st.left = Math.max(0, Math.round((st.deadline - performance.now()) / 1000));
  clock.textContent = render(st.left);
  if (st.left <= 0 && !st.done) {
    st.done = true;
    clock.classList.add("alarm");
    document.title = "time up - mokodoro";
    // ponytail: no OS notification yet; the red clock is the alarm
  }
  sync();
}

function togglePause() {
  st.paused = !st.paused;
  if (!st.paused) st.deadline = performance.now() + st.left * 1000;
  pauseBtn.textContent = st.paused ? "|>" : "||";
  sync();
}

function toggleMute() {
  st.muted = !st.muted;
  muteBtn.textContent = st.muted ? "mute" : "vol";
  sync();
}

function cycleSound() {
  st.snd = (st.snd + 1) % SOUNDS.length;
  audio.src = SOUNDS[st.snd]; // load() pauses it; sync() restarts if it should play
  sync();
}

// Only the float window scales the clock to its size. In the tab the CSS size stays
// fixed, so a stale px size can't inflate the tab's clock.
function fit() {
  if (!pipWin) {
    clock.style.fontSize = "";
    return;
  }
  const w = pipWin.innerWidth;
  const h = pipWin.innerHeight - bar.offsetHeight;
  clock.style.fontSize = `${Math.max(8, Math.min(Math.floor(h / 6), Math.floor(w / 12)))}px`;
}

function onKey(e) {
  switch (e.key) {
    case " ": e.preventDefault(); togglePause(); break;
    case "m": toggleMute(); break;
    case "s": cycleSound(); break;
    case "Escape": if (pipWin) pipWin.close(); break;
  }
}

function dock() {
  pipWin = null;
  document.body.classList.remove("floating");
  document.body.append(app);
  floatBtn.disabled = false;
  fit();
}

// Fallback when Document PiP is unavailable or refused: hand the remaining time
// to a small popup window (not always-on-top, but its own small window).
function handOffToPopup(reason) {
  console.error("float failed:", reason);
  alert(`float failed: ${reason}\nopening a small window instead.`);
  chrome.windows.create({
    url: chrome.runtime.getURL(`timer.html?secs=${Math.max(1, st.left)}`),
    type: "popup",
    width: 340,
    height: 160,
  });
  clearInterval(timerId);
  audio.pause();
  $("note").textContent = "moved to a small window. this tab is idle.";
  document.body.classList.add("floating");
}

// auto: tried on page load without a click. Chrome normally refuses PiP without a
// gesture, so on refusal we wait for the user's click instead of popping an alert.
async function float({ auto = false } = {}) {
  if (pipWin) return;
  if (!auto) sync(); // a real click: start audio here, it's the gesture autoplay needs
  if (!("documentPictureInPicture" in window)) {
    if (!auto) handOffToPopup("documentPictureInPicture is missing (needs Chrome/Edge 116+)");
    return;
  }
  floatBtn.disabled = true;
  try {
    pipWin = await documentPictureInPicture.requestWindow({ width: 340, height: 140 });
  } catch (err) {
    floatBtn.disabled = false;
    if (auto) {
      console.warn("auto-float refused, click float:", err);
      return;
    }
    handOffToPopup(`${err.name}: ${err.message}`);
    return;
  }
  // Style the float window with the same stylesheet (absolute URL, not relative).
  const css = document.createElement("link");
  css.rel = "stylesheet";
  css.href = chrome.runtime.getURL("timer.css");
  pipWin.document.head.append(css);
  pipWin.document.body.style.margin = "0";
  pipWin.document.body.append(app); // moves the live DOM; listeners stay attached
  document.body.classList.add("floating");
  pipWin.addEventListener("pagehide", dock);
  pipWin.addEventListener("resize", fit);
  pipWin.addEventListener("keydown", onKey);
  fit();
}

floatBtn.addEventListener("click", float);
pauseBtn.addEventListener("click", togglePause);
muteBtn.addEventListener("click", toggleMute);
sndBtn.addEventListener("click", cycleSound);
document.addEventListener("keydown", onKey);
window.addEventListener("resize", fit);

tick();
const timerId = setInterval(tick, 250);
if (params.get("float") === "1") float({ auto: true });
