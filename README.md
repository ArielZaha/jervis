# Jervis website

The official page for Jervis: what it is, what it can do, what stays on your computer, and a real download of the app.
It is a static site (HTML, CSS and a little JavaScript, no build step and no dependencies), kept separate from the app so
nothing here can affect how Jervis runs.

```
website/
  index.html               the page
  assets/css/site.css      styles (colours, type and corner shapes come from the app's own style.css)
  assets/js/site.js        menu, tabs, copy buttons, download buttons, the live voice core
  assets/js/orb.js         an unchanged copy of the app's orb.js (the animated core in the hero)
  assets/img/              screenshots of the real Jervis window, favicon, social image
  assets/fonts/            Inter, JetBrains Mono and Orbitron, self-hosted
  downloads/release.json   the current release's files, sizes and checksums (written by the tool below)
  tools/sync_release.py    points the page at the latest installers
  tools/screenshot_feed.py drives the real Jervis window for new screenshots
```

## Preview it

```
python3 -m http.server 8000 --directory website
```

Then open <http://localhost:8000>. Open it through a server rather than as a file, so the download link behaves like it
will online.

## Point the page at a new version

The installers are built, install-tested and published by GitHub Actions in the app's repository
([ArielZaha/jervis-app](https://github.com/ArielZaha/jervis-app)): pushing a tag like `v1.0.1` there makes a release
with `Jervis Setup.exe`, the Mac `.dmg` and `SHA256SUMS.txt`. They are too big for GitHub Pages, so the page links to
the release. After a release, run:

```
python3 website/tools/sync_release.py
```

It reads the latest release with the GitHub CLI, downloads both installers to check them against the published
checksums, and writes the version, the download links, the sizes and the SHA-256 values into `index.html`, the
structured data for search engines, `downloads/release.json` and `sitemap.xml`. Then commit and push the website.

## Where it lives

The site is published with GitHub Pages from [ArielZaha/jervis](https://github.com/ArielZaha/jervis) at
<https://arielzaha.github.io/jervis/>: pushing to `main` updates it within a minute or two. The installers are served
by GitHub Releases from the app's repository, so nothing large lives here.

## New screenshots

The screenshots are the real Jervis window, not mock-ups. To take new ones after the window changes, run
`venv/bin/python website/tools/screenshot_feed.py` from the app folder. It sends the window real replies made by
Jervis's own math, graph, globe and planet code, without a microphone or AI. The steps are in the file.
