# mokodoro

Always-on-top braille pixel-art pomodoro timer for macOS. Single Python file, stdlib + tkinter.

```
mokodoro 25min | 1hr | 90s | 1h30m | 25     # bare number = minutes
```

Keys: `space` pause, `m` mute, `s` cycle tick sound, `esc` quit.

Resizable window, follows you across Spaces, ticking sound while running,
macOS notification when the timer ends.

## Install

```sh
chmod +x mokodoro.py
ln -s "$PWD/mokodoro.py" ~/.local/bin/mokodoro
```

Optional: `pip install pyobjc-framework-Cocoa` for cross-Space window following.

## Sounds

`sounds/` holds ticking loops sourced from [freesound.org](https://freesound.org);
each file keeps its original freesound name. Check the individual licenses there
before reusing them.
