# mokodoro

A pomodoro timer for Chrome and Edge. The clock is drawn in braille pixel art,
and it can float above every other window (Document Picture-in-Picture).

## Features

- Durations like `25min`, `1hr`, `90s`, `1h30m`, or a bare number of minutes.
- Pause, mute, and cycle through five tick sounds.
- Float button pops the clock into a small always-on-top window.
- Works offline. Nothing is fetched from the network.

## Keys

| key   | action                                  |
|-------|-----------------------------------------|
| space | pause / resume                          |
| m     | mute / unmute                           |
| s     | cycle tick sound                        |
| esc   | dock the float window back into the tab |

## Install from source (developer mode)

1. Open `chrome://extensions` and turn on **Developer mode**.
2. Click **Load unpacked** and select this folder.
3. Click the mokodoro icon, pick a duration, and start.
4. Click **float** in the timer tab to pop it out. Audio starts on that click,
   because browsers block autoplay until you interact with the page.

Chrome or Edge 116 or newer is required for the float window. Without it the
timer falls back to a small popup window that does not stay on top.

## Build a store package

```sh
zip -r mokodoro.zip manifest.json popup.html popup.js timer.html timer.js \
    timer.css lib.js fonts icons/*.png sounds
```

`tests/` and `README.md` are not part of the package.

## Tests

```sh
node tests/lib.test.mjs
```

## Privacy

mokodoro collects no data, has no accounts, and makes no network requests. It
asks for no extension permissions. Settings live only in the open timer tab.

## Credits and licenses

- **Tick sounds** are from [freesound.org](https://freesound.org). Each file
  keeps its original freesound name in `sounds/`. Confirm each file's license
  there and add the required attribution before publishing.
- **Pixel font:** Press Start 2P by CodeMan38, SIL Open Font License 1.1.
  See `fonts/OFL.txt`.
- **Icon artwork:** `icons/rabbit.jpeg` is the source for the toolbar icon. Confirm
  you have rights to publish this image before submitting to the Web Store.
