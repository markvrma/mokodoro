#!/usr/bin/env python3
"""mokodoro — always-on-top braille pixel-art pomodoro timer.

    mokodoro 25min | 1hr | 90s | 1h30m | 25

Keys: space = pause, m = mute, s = cycle tick sound, esc = quit.
Set MOKODORO_CHILD=1 to run in the foreground with stderr visible (debugging).
"""
import atexit
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave

# ---------------------------------------------------------------- duration

UNIT = {"s": 1, "sec": 1, "m": 60, "min": 60, "h": 3600, "hr": 3600, "hour": 3600}
TOKEN = r"(\d+)\s*(sec|min|hour|hr|s|m|h)?"  # longest-first: "min" must beat "m"


def parse(s):
    """'1h30m' -> 5400. Bare number means minutes. None if unparseable or zero."""
    s = s.strip().lower()
    if not re.fullmatch(rf"(?:{TOKEN}\s*)+", s):
        return None
    return sum(int(n) * UNIT[u or "min"] for n, u in re.findall(TOKEN, s)) or None


assert parse("25min") == 1500
assert parse("1hr") == 3600
assert parse("90s") == 90
assert parse("1h30m") == 5400
assert parse("25") == 1500
assert parse("0min") is None
assert parse("abc") is None
assert parse("") is None

# ---------------------------------------------------------------- braille art

# ponytail: a braille cell is 2x4 dots but a real dot is ~5px wide x 4px tall in
# Menlo, so square scaling renders digits 25% too wide. SX/SY are the
# calibration knob — bump SY if your font's linespace differs.
PX_SX, PX_SY = 2, 3

BITS = (0x01, 0x08, 0x02, 0x10, 0x04, 0x20, 0x40, 0x80)  # indexed dy*2+dx
BLANK = "⠀"  # blank braille, NOT a space: space is a different width

FONT3x5 = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    ":": ("000", "010", "000", "010", "000"),
}


def _pack(rows):
    """Rows of '0'/'1' -> list of braille strings, one per 4 pixel rows."""
    h, w = len(rows), len(rows[0])
    out = []
    for y in range(0, h, 4):
        line = ""
        for x in range(0, w, 2):
            mask = 0
            for dy in range(4):
                for dx in range(2):
                    yy, xx = y + dy, x + dx
                    if yy < h and xx < w and rows[yy][xx] == "1":
                        mask |= BITS[dy * 2 + dx]
            line += chr(0x2800 | mask)
        out.append(line)
    return out


def _scale(bitmap):
    return ["".join(c * PX_SX for c in row) for row in bitmap for _ in range(PX_SY)]


GLYPHS = {c: _pack(_scale(bm)) for c, bm in FONT3x5.items()}  # built once, at import
GH = len(next(iter(GLYPHS.values())))


def render(secs):
    """Seconds -> multi-line braille MM:SS. Depends on time only, never window size."""
    text = f"{secs // 60:02d}:{secs % 60:02d}"
    glyphs = [GLYPHS[c] for c in text]
    return "\n".join(BLANK.join(g[r] for g in glyphs) for r in range(GH))


assert len(render(1500).split("\n")) == GH
assert render(3600).count("\n") == GH - 1  # 1hr shows 60:00, no hour column

# ---------------------------------------------------------------- tick sounds

# ponytail: afplay has no --loop and the shortest clip is 3.5s, so respawning it
# would hiccup every few seconds. Decode once with afconvert (ships with macOS)
# and stitch enough copies to fill LOOP seconds -> one respawn per minute.
LOOP = 60.0
SOUNDS = sorted(glob.glob(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), "sounds", "*.mp3")))

_TMP = tempfile.mkdtemp(prefix="mokodoro-")
atexit.register(shutil.rmtree, _TMP, True)


def loop_wav(idx):
    """Path to a ~LOOP-second loop of SOUNDS[idx], built on first use and cached."""
    out = os.path.join(_TMP, f"{idx}.wav")
    if os.path.exists(out):
        return out
    raw = out + ".raw"
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@22050", "-c", "1",
                    SOUNDS[idx], raw], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with wave.open(raw) as src:
        rate, frames = src.getframerate(), src.readframes(src.getnframes())
        reps = max(1, round(LOOP * rate * src.getsampwidth() / max(1, len(frames))))
    with wave.open(out, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(rate)
        dst.writeframes(frames * reps)
    os.remove(raw)
    assert os.path.getsize(out) > 44  # header-only means afconvert produced nothing
    return out


# ponytail: ONE owner of "at most one afplay, playing index N". Splitting that
# invariant between the caller and the tick watchdog is how a killed-but-unreaped
# process gets replaced while it is still audible.
_AUDIO = {"proc": None, "idx": None}


def audio_stop():
    proc = _AUDIO["proc"]
    if proc:
        proc.kill()
        proc.wait()  # reap, or poll() can still report it alive
        _AUDIO["proc"] = None


def audio_play(idx):
    """Idempotent: keeps SOUNDS[idx] looping, and nothing else."""
    proc = _AUDIO["proc"]
    if proc and _AUDIO["idx"] == idx and proc.poll() is None:
        return  # already playing the right one
    audio_stop()
    assert _AUDIO["proc"] is None, "previous sound outlived audio_stop()"
    _AUDIO["idx"] = idx
    _AUDIO["proc"] = subprocess.Popen(
        ["afplay", loop_wav(idx)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------- window

USAGE = "usage: mokodoro 25min | 1hr | 90s | 1h30m"
FG, DIM, ALARM = "#eaeaea", "#6a6a6a", "#ff3b30"


def follow_spaces(root):
    """Make the window cross Space switches and sit above fullscreen apps.

    ponytail: Tk's -topmost is only NSFloatingWindowLevel, which is per-Space --
    nothing in Tk crosses Spaces, so AppKit is the real fix here. pyobjc stays
    optional: without it we degrade to floating within the current Space.
    """
    try:
        from AppKit import (NSApp, NSStatusWindowLevel,
                            NSWindowCollectionBehaviorCanJoinAllSpaces,
                            NSWindowCollectionBehaviorStationary)
    except ImportError:
        return False
    root.update()  # the NSWindow has to exist before AppKit can see it
    for w in NSApp().windows():
        w.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                 | NSWindowCollectionBehaviorStationary)
        w.setLevel_(NSStatusWindowLevel)
    return True


def main():
    arg = " ".join(sys.argv[1:]) or "25min"
    secs = parse(arg)
    if secs is None:
        print(f"{USAGE}\nmokodoro: cannot read duration {arg!r}", file=sys.stderr)
        sys.exit(2)

    if os.environ.get("MOKODORO_CHILD") != "1":
        # fork+EXEC, not bare fork: Cocoa can't inherit the parent's mach ports,
        # and a forked-only child dies with "com.apple.view-bridge: Connection invalid".
        subprocess.Popen(
            [sys.executable, os.path.realpath(__file__), *sys.argv[1:]],
            env={**os.environ, "MOKODORO_CHILD": "1"},
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    import tkinter as tk
    import tkinter.font as tkfont

    root = tk.Tk()
    root.title("mokodoro")
    root.configure(bg="black")
    root.wm_attributes("-topmost", True)  # follow_spaces() upgrades this below
    root.geometry(f"340x140+{root.winfo_screenwidth() - 360}+20")
    root.minsize(200, 110)
    root.pack_propagate(False)  # font growth must not resize the window -> no <Configure> loop

    font = tkfont.Font(family="Menlo", size=20)  # NOT "monospace": resolves proportional
    small = tkfont.Font(family="Menlo", size=11)

    bar = tk.Frame(root, bg="black")
    bar.pack(side="bottom", fill="x")
    label = tk.Label(root, text=render(secs), font=font, bg="black", fg=FG)
    label.pack(expand=True)

    st = {"left": secs, "deadline": time.monotonic() + secs,
          "paused": False, "muted": not SOUNDS, "snd": 0, "rung": False}

    def button(text, cmd):
        b = tk.Label(bar, text=text, font=small, bg="black", fg=DIM,
                     padx=7, pady=3, cursor="pointinghand")
        b.bind("<Button-1>", lambda e: cmd())
        b.bind("<Enter>", lambda e: b.config(fg=FG))
        b.bind("<Leave>", lambda e: b.config(fg=DIM))
        return b

    atexit.register(audio_stop)

    def sync_audio():
        """Also the loop watchdog: afplay has no --loop, so respawn when it exits."""
        if not SOUNDS or st["muted"] or st["paused"] or st["left"] <= 0:
            audio_stop()
        else:
            audio_play(st["snd"])

    def toggle_pause():
        st["paused"] = not st["paused"]
        if not st["paused"]:
            st["deadline"] = time.monotonic() + st["left"]
        pause_b.config(text="|>" if st["paused"] else "||")
        sync_audio()

    def toggle_mute():
        st["muted"] = not st["muted"]
        mute_b.config(text="mute" if st["muted"] else "vol")
        sync_audio()

    def cycle_sound():
        if not SOUNDS:
            return
        st["snd"] = (st["snd"] + 1) % len(SOUNDS)
        sync_audio()  # audio_play swaps the process itself

    snd_b = button(">>", cycle_sound)
    mute_b = button("mute" if st["muted"] else "vol", toggle_mute)
    pause_b = button("||", toggle_pause)
    for b in (snd_b, mute_b, pause_b):  # side=right stacks leftward: pause | vol | snd
        b.pack(side="right")

    last = [None]

    def on_resize(event):
        if event.widget is not root or (event.width, event.height) == last[0]:
            return
        last[0] = (event.width, event.height)
        # resize == font size. The art itself never re-renders.
        usable = event.height - bar.winfo_reqheight()
        font.configure(size=max(8, min(usable // 6, event.width // 12)))

    def tick():
        if not st["paused"]:
            st["left"] = max(0, int(round(st["deadline"] - time.monotonic())))
        label.config(text=render(st["left"]))
        if st["left"] <= 0 and not st["rung"]:
            st["rung"] = True
            label.config(fg=ALARM)
            subprocess.Popen(["osascript", "-e", 'display notification "time up" '
                              'with title "mokodoro" sound name "Glass"'])
        sync_audio()
        root.after(250, tick)

    root.bind("<Configure>", on_resize)
    root.bind("<Escape>", lambda e: root.destroy())
    root.bind("<space>", lambda e: toggle_pause())
    root.bind("m", lambda e: toggle_mute())
    root.bind("s", lambda e: cycle_sound())
    follow_spaces(root)
    tick()
    root.mainloop()
    audio_stop()


if __name__ == "__main__":
    main()
