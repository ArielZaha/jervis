"""Point the website at the current Jervis installers.

    python3 website/tools/sync_release.py            # the latest release of ArielZaha/jervis-app
    python3 website/tools/sync_release.py --tag v1.0.0
    python3 website/tools/sync_release.py --download   # also download both installers and hash them here

The installers are built and tested by GitHub Actions in the app's repository and published as a GitHub release
(they are too big for GitHub Pages). This reads that release with the GitHub CLI (`gh`), checks the published
checksums against the files themselves, and writes the facts into the page: download links, sizes, SHA-256 values,
the version, the structured data for search engines, and downloads/release.json. Nothing is uploaded.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

REPO = "ArielZaha/jervis-app"
SITE_URL = "https://arielzaha.github.io/jervis/"
WEBSITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(WEBSITE, "index.html")
DOWNLOADS = os.path.join(WEBSITE, "downloads")
PLATFORMS = {"win": ".exe", "mac": ".dmg"}


def say(message: str) -> None:
    print(message, flush=True)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def size_label(n: int) -> str:
    return f"{round(n / 1_000_000)} MB"


def fetch(url: str, path: str) -> None:
    with urllib.request.urlopen(url, timeout=60) as response, open(path, "wb") as f:
        while chunk := response.read(1 << 20):
            f.write(chunk)


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_release(tag: str) -> dict:
    endpoint = f"repos/{REPO}/releases/tags/{tag}" if tag else f"repos/{REPO}/releases/latest"
    data = json.loads(gh("api", endpoint))
    assets = {a["name"]: a for a in data["assets"]}
    sums_asset = assets.get("SHA256SUMS.txt")
    if not sums_asset:
        sys.exit(f"Release {data['tag_name']} has no SHA256SUMS.txt.")
    with tempfile.TemporaryDirectory() as tmp:
        sums_path = os.path.join(tmp, "sums")
        fetch(sums_asset["browser_download_url"], sums_path)
        published = {}
        with open(sums_path, encoding="utf-8") as f:
            for line in f:
                digest, _, name = line.strip().partition("  ")
                published[name.lstrip("*")] = digest
        release = {"version": data["tag_name"].lstrip("v"), "tag": data["tag_name"], "page": data["html_url"],
                   "built": data["published_at"][:10], "site_url": SITE_URL}
        for key, ext in PLATFORMS.items():
            asset = next((a for a in data["assets"] if a["name"].endswith(ext)), None)
            if not asset:
                sys.exit(f"Release {data['tag_name']} has no {ext} installer.")
            # The file GitHub serves must match the checksum the page shows: GitHub reports the SHA-256 of what it
            # stores; with --download (or on an older release without it) the file itself is downloaded and hashed.
            say(f"Checking {asset['name']} ({size_label(asset['size'])})…")
            stored = (asset.get("digest") or "").removeprefix("sha256:")
            if stored and "--download" not in sys.argv:
                actual = stored
            else:
                local = os.path.join(tmp, asset["name"])
                fetch(asset["browser_download_url"], local)
                actual = sha256(local)
            listed = published.get(asset["name"]) or published.get(asset["name"].replace(".", " ", 1))
            if not listed:
                sys.exit(f"{asset['name']} isn't listed in SHA256SUMS.txt.")
            if listed != actual:
                sys.exit(f"{asset['name']}: the published checksum doesn't match the file.")
            release.update({f"{key}_file": asset["name"], f"{key}_url": asset["browser_download_url"],
                            f"{key}_bytes": asset["size"], f"{key}_size": size_label(asset["size"]),
                            f"{key}_sha256": actual})
    return release


def update_page(release: dict) -> None:
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    unknown = set(re.findall(r'data-release="(\w+)"', html)) - set(release)
    if unknown:
        sys.exit(f"index.html asks for release facts that don't exist: {sorted(unknown)}")
    html, facts = re.subn(r'(<(\w+)[^>]*\bdata-release="(\w+)"[^>]*>)[^<]*(</\2>)',
                          lambda m: m.group(1) + str(release[m.group(3)]) + m.group(4), html)
    html, links = re.subn(r'href="[^"]*"(\s+data-release-href="(\w+)")',
                          lambda m: f'href="{release[m.group(2)]}"{m.group(1)}', html)
    data = {
        "@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Jervis",
        "description": "A voice assistant for Windows and macOS that plays media, opens apps, writes documents, "
                       "sets timers, solves and graphs math, and can use the mouse and keyboard when asked. "
                       "Its AI runs on your own computer.",
        "operatingSystem": "Windows 10, Windows 11, macOS 11 or later (Apple silicon)",
        "applicationCategory": "UtilitiesApplication",
        "softwareVersion": release["version"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": [{"@type": "Person", "name": "Ariel"}, {"@type": "Person", "name": "Shalev"}],
        "url": SITE_URL, "downloadUrl": release["page"],
        "screenshot": f"{SITE_URL}assets/img/jervis-chat-1600.webp",
    }
    block = json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    html = re.sub(r'(<script type="application/ld\+json">).*?(</script>)',
                  lambda m: f"{m.group(1)}\n  {block}\n  {m.group(2)}", html, count=1, flags=re.S)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    say(f"Updated index.html: {facts} release facts, {links} download links, structured data.")


def write_files(release: dict) -> None:
    os.makedirs(DOWNLOADS, exist_ok=True)
    with open(os.path.join(DOWNLOADS, "release.json"), "w", encoding="utf-8") as f:
        json.dump(release, f, indent=2)
        f.write("\n")
    with open(os.path.join(WEBSITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"  <url><loc>{SITE_URL}</loc><lastmod>{datetime.date.today().isoformat()}</lastmod></url>\n</urlset>\n")
    say("Wrote downloads/release.json and sitemap.xml.")


def main() -> None:
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else ""
    release = read_release(tag)
    update_page(release)
    write_files(release)
    say(f"The site now offers Jervis {release['version']}: {release['win_file']} ({release['win_size']}) and "
        f"{release['mac_file']} ({release['mac_size']}).")


if __name__ == "__main__":
    main()
