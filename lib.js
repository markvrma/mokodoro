// Shared, DOM-free logic: duration parsing, braille rendering, sound list.

// Sorted by file name; the order is what the sound button cycles through.
export const SOUNDS = [
  "sounds/11325622-clock-ticking-sound-effect-240503.mp3",
  "sounds/freesound_community-clock-ticking-103687.mp3",
  "sounds/freesound_community-ticking-clock_1-27477.mp3",
  "sounds/freesound_community-watch-ticking-contact-mic-28757.mp3",
  "sounds/freesound_community-water-dripping-63539.mp3",
];

// ---------------------------------------------------------------- duration

const UNIT = { s: 1, sec: 1, m: 60, min: 60, h: 3600, hr: 3600, hour: 3600 };
const TOKEN = String.raw`(\d+)\s*(sec|min|hour|hr|s|m|h)?`; // longest-first: "min" beats "m"

// "1h30m" -> 5400. Bare number means minutes. null if unparseable or zero.
export function parse(input) {
  const s = input.trim().toLowerCase();
  if (!new RegExp(`^(?:${TOKEN}\\s*)+$`).test(s)) return null;
  let total = 0;
  for (const [, n, u] of s.matchAll(new RegExp(TOKEN, "g"))) {
    total += Number(n) * UNIT[u || "min"];
  }
  return total || null;
}

// ---------------------------------------------------------------- braille art

// ponytail: a braille cell is 2x4 dots but a real dot is taller than wide in
// Menlo, so square scaling renders digits too wide. PX_SX/PX_SY is the
// calibration knob: raise PX_SY if your font's line height differs.
const PX_SX = 2;
const PX_SY = 3;

const BITS = [0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80]; // indexed dy*2+dx
export const BLANK = "⠀"; // blank braille, NOT a space: space is a different width

const FONT = {
  0: ["111", "101", "101", "101", "111"],
  1: ["010", "110", "010", "010", "111"],
  2: ["111", "001", "111", "100", "111"],
  3: ["111", "001", "111", "001", "111"],
  4: ["101", "101", "111", "001", "001"],
  5: ["111", "100", "111", "001", "111"],
  6: ["111", "100", "111", "101", "111"],
  7: ["111", "001", "001", "001", "001"],
  8: ["111", "101", "111", "101", "111"],
  9: ["111", "101", "111", "001", "111"],
  ":": ["000", "010", "000", "010", "000"],
};

function pack(rows) {
  const h = rows.length;
  const w = rows[0].length;
  const out = [];
  for (let y = 0; y < h; y += 4) {
    let line = "";
    for (let x = 0; x < w; x += 2) {
      let mask = 0;
      for (let dy = 0; dy < 4; dy++) {
        for (let dx = 0; dx < 2; dx++) {
          const yy = y + dy;
          const xx = x + dx;
          if (yy < h && xx < w && rows[yy][xx] === "1") mask |= BITS[dy * 2 + dx];
        }
      }
      line += String.fromCodePoint(0x2800 | mask);
    }
    out.push(line);
  }
  return out;
}

function scale(bitmap) {
  const out = [];
  for (const row of bitmap) {
    const wide = [...row].map((c) => c.repeat(PX_SX)).join("");
    for (let i = 0; i < PX_SY; i++) out.push(wide);
  }
  return out;
}

const GLYPHS = Object.fromEntries(
  Object.entries(FONT).map(([c, bm]) => [c, pack(scale(bm))]),
);
const GH = GLYPHS["0"].length;

// Seconds -> multi-line braille MM:SS. Depends only on time.
export function render(secs) {
  const pad = (n) => String(n).padStart(2, "0");
  const text = `${pad(Math.floor(secs / 60))}:${pad(secs % 60)}`;
  const glyphs = [...text].map((c) => GLYPHS[c]);
  const lines = [];
  for (let r = 0; r < GH; r++) lines.push(glyphs.map((g) => g[r]).join(BLANK));
  return lines.join("\n");
}
