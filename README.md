# Jervis website

The official page for Jervis: what it is, what it can do, what stays on your computer, and a real download of the app.
It is a static site (HTML, CSS and a little JavaScript, no build step and no dependencies), kept separate from the app so
nothing here can affect how Jervis runs.

```
website/
  index.html               the page
  assets/css/site.css      styles (colours, type and corner shapes come from the app's own style.css)
  assets/js/site.js        menu, tabs, copy buttons, download note, the live voice core
  assets/js/orb.js         an unchanged copy of the app's orb.js (the animated core in the hero)
  assets/img/              screenshots of the real Jervis window, favicon, social image
  assets/fonts/            Inter, JetBrains Mono and Orbitron, self-hosted
  downloads/               Jervis-<version>.zip and release.json (made by the tool below)
  tools/build_release.py   builds the download from the app folder
  tools/screenshot_feed.py drives the real Jervis window for new screenshots
```

## Preview it

```
python3 -m http.server 8000 --directory website
```

Then open <http://localhost:8000>. Open it through a server rather than as a file, so the download link behaves like it
will online.

## Make a new download

After changing Jervis, rebuild the zip from the app folder:

```
python3 website/tools/build_release.py --verify
```

It packs only the app's own files (the Python modules, the window, `vendor/`, the launchers, `README.md` and
`.env.example`) into `website/downloads/Jervis-<version>.zip`. The version comes from `VERSION` in `run.py`, so bump it
there first. Your personal files are never included: `.env` with your API keys, `.cache` (Spotify sign-in),
`.calendar_token.json`, the Netflix browser profile, `transcripts/`, `logs/`, `images/`, caches, `venv/` and
`node_modules/`. As a final check, every packed file is scanned for the values in your `.env` and for anything shaped
like an API key, and the build stops if it finds one.

The tool also writes `downloads/release.json` and updates the version, file name, size and SHA-256 checksum shown on
the page, so the page always describes the exact file it links to. `--verify` unpacks the zip again and checks that it
opens cleanly, every `.py` file compiles, no personal file slipped in, and the checksum matches.

## Put it online

Upload the whole `website/` folder to any static host (GitHub Pages, Netlify, Cloudflare Pages, your own server).
The zip is served from the same place as the page, so the download works with no extra setup.

Once it has a real address, change the `og:image` tag in `index.html` to the full URL of
`assets/img/og-jervis.jpg`. Some sites only show a link preview when the image address is absolute.

## New screenshots

The screenshots are the real Jervis window, not mock-ups. To take new ones after the window changes, run
`venv/bin/python website/tools/screenshot_feed.py` from the app folder. It sends the window real replies made by
Jervis's own math, graph, globe and planet code, without a microphone or AI. The steps are in the file.
