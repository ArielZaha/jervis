#!/bin/bash
# Installs Jervis on a Mac:  curl -fsSL https://arielzaha.github.io/jervis/install-mac.sh | bash
#
# Downloads the current Jervis for Mac, checks it against the SHA-256 published on the website, copies Jervis to
# Applications and opens him. Jervis isn't notarized by Apple yet (that needs a paid developer account), so a copy
# downloaded in a browser is stopped by macOS ("Apple could not verify Jervis…"). A download made here isn't marked
# as coming from a browser, so Jervis opens normally. Nothing else on the Mac is changed.
set -euo pipefail

SITE="https://arielzaha.github.io/jervis"
DEST="${JERVIS_INSTALL_DIR:-/Applications}"

say() { printf '\033[1m%s\033[0m\n' "$*"; }
fail() { printf 'Could not install Jervis: %s\n' "$*" >&2; exit 1; }

[ "$(uname -s)" = "Darwin" ] || fail "this installer is for macOS."
[ "$(uname -m)" = "arm64" ] || fail "Jervis for Mac needs Apple silicon (an M1 or newer)."

say "Finding the current version of Jervis…"
info="$(curl -fsSL --retry 3 "$SITE/downloads/release.json?$(date +%s)")" || fail "the website can't be reached."
field() { plutil -extract "$1" raw -o - - <<<"$info"; }
version="$(field version)"; url="$(field mac_url)"; sha="$(field mac_sha256)"
[ -n "$url" ] && [ -n "$sha" ] || fail "the website didn't say where Jervis is."

work="$(mktemp -d)"
trap 'hdiutil detach "$work/disk" -quiet >/dev/null 2>&1 || true; rm -rf "$work"' EXIT

say "Downloading Jervis ${version}…"
for attempt in 1 2 3 4 5; do
  curl -fL --retry 3 --connect-timeout 20 -C - --progress-bar -o "$work/Jervis.dmg" "$url" && break
  [ "$attempt" = 5 ] && fail "the download kept failing. Check the internet connection and try again."
  sleep 2
done

say "Checking the download…"
actual="$(shasum -a 256 "$work/Jervis.dmg" | cut -d' ' -f1)"
[ "$actual" = "$sha" ] || fail "the downloaded file isn't the published Jervis (checksum mismatch). Try again."

if [ -d "$DEST/Jervis.app" ]; then
  say "Closing the Jervis that's running now…"
  "$DEST/Jervis.app/Contents/MacOS/Jervis" --quit >/dev/null 2>&1 || true
  for _ in $(seq 1 20); do pgrep -f "$DEST/Jervis.app/Contents/" >/dev/null || break; sleep 0.5; done
  pkill -f "$DEST/Jervis.app/Contents/" 2>/dev/null || true
fi

say "Installing Jervis in ${DEST}…"
mkdir -p "$DEST"
hdiutil attach "$work/Jervis.dmg" -nobrowse -readonly -mountpoint "$work/disk" -quiet
if ! { rm -rf "$DEST/Jervis.app" && ditto "$work/disk/Jervis.app" "$DEST/Jervis.app"; } 2>/dev/null; then
  say "Your password is needed to write to ${DEST}."
  sudo rm -rf "$DEST/Jervis.app"
  sudo ditto "$work/disk/Jervis.app" "$DEST/Jervis.app"
  sudo chown -R "$(id -u):$(id -g)" "$DEST/Jervis.app"
fi
xattr -dr com.apple.quarantine "$DEST/Jervis.app" 2>/dev/null || true

say "Jervis ${version} is installed. Opening him…"
[ -n "${JERVIS_NO_OPEN:-}" ] || open "$DEST/Jervis.app"
