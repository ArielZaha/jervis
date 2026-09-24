#!/usr/bin/env python3
"""Build the Jervis download that the website offers:   python3 website/tools/build_release.py

Packs the app (the folder above website/) into website/downloads/Jervis-<version>.zip, the same way Jervis has always
been shared: a plain folder you unzip and start with run.py / start_jervis.bat, which install everything on first run.

Only an allowlist of app files goes in. Personal files never do: .env (API keys), .cache (Spotify sign-in),
.calendar_token.json, the Netflix browser profile, transcripts, logs, pictures, caches, venv and node_modules. As a
last check, every packed file is scanned for the actual values in .env and for API-key shapes; a match aborts the build.

It then writes downloads/release.json and updates the version, file name, size and SHA-256 shown in website/index.html,
so the page always describes the exact file it links to. Run with --verify to also unpack the zip and check it.
"""
import hashlib
import json
import os
import py_compile
import re
import sys
import tempfile
import zipfile
from datetime import date

WEBSITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.dirname(WEBSITE)
DOWNLOADS = os.path.join(WEBSITE, "downloads")
PAGE = os.path.join(WEBSITE, "index.html")
TOP_FOLDER = "Jervis"  # the folder people get when they unzip

# What the app is made of (top level of the app folder), plus the bundled vendor/ folder.
INCLUDE_EXTENSIONS = (".py", ".js", ".bat", ".command")
INCLUDE_FILES = {"index.html", "style.css", "package.json", "package-lock.json", "requirements.txt",
                 "requirements-local-images.txt", ".env.example", "README.md"}
INCLUDE_DIRS = {"vendor"}
# Never shipped, whatever the allowlist says.
NEVER_NAMES = {".env", ".cache", ".calendar_token.json", "timers.json", ".DS_Store"}
NEVER_DIRS = {"venv", ".venv", "node_modules", "__pycache__", "transcripts", "logs", "images", "website",
              ".jervis-netflix-profile", ".claude", ".electron-cache", ".git"}
KEY_SHAPES = re.compile(rb"gsk_[A-Za-z0-9]{20,}|sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{20,}")
NOT_SECRET = re.compile(r"(_URI|_URL|_MODEL|_BACKEND|_READING)$")  # .env settings that are configuration, not secrets
REQUIRED = ["run.py", "app.py", "main.js", "index.html", "renderer.js", "package.json", "requirements.txt",
            ".env.example", "README.md", "start_jervis.bat", "vendor/katex/katex.min.js"]
EXECUTABLE = {"run.py"}


def say(message: str) -> None:
    print(f"[release] {message}", flush=True)


def app_version() -> str:
    with open(os.path.join(APP, "run.py"), encoding="utf-8") as f:
        match = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    if not match:
        sys.exit("Could not read VERSION from run.py.")
    return match.group(1)


def blocked(relpath: str) -> bool:
    parts = relpath.split("/")
    name = parts[-1]
    return (name in NEVER_NAMES or name.endswith("_cache.json") or name.endswith(".zip") or name.endswith(".pyc")
            or any(p in NEVER_DIRS for p in parts[:-1]) or (name.startswith(".") and name != ".env.example"))


def collect() -> list:
    files = []
    for name in sorted(os.listdir(APP)):
        path = os.path.join(APP, name)
        if os.path.isfile(path) and (name in INCLUDE_FILES or name.endswith(INCLUDE_EXTENSIONS)):
            files.append(name)
        elif os.path.isdir(path) and name in INCLUDE_DIRS:
            for root, dirs, names in os.walk(path):
                dirs[:] = sorted(d for d in dirs if d not in NEVER_DIRS)
                for n in sorted(names):
                    files.append(os.path.relpath(os.path.join(root, n), APP).replace(os.sep, "/"))
    return [f for f in files if not blocked(f)]


def secrets() -> list:
    """The values in .env, so the build can prove none of them ended up in the zip. Plain settings (URLs, model names,
    on/off switches) are skipped: their defaults legitimately appear in the app's code and in .env.example."""
    values = []
    try:
        with open(os.path.join(APP, ".env"), encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    key = key.strip().removeprefix("export ").strip()
                    if NOT_SECRET.search(key):
                        continue
                    value = value.split(" #", 1)[0].strip().strip("\"'")
                    if len(value) >= 8:
                        values.append(value.encode())
    except FileNotFoundError:
        pass
    return values


def scan(files: list) -> None:
    values = secrets()
    for rel in files:
        with open(os.path.join(APP, rel), "rb") as f:
            data = f.read()
        if any(v in data for v in values):
            sys.exit(f"ABORTED: {rel} contains a value from .env. Nothing was written.")
        if rel.endswith((".py", ".js", ".md", ".txt", ".example", ".bat", ".command", ".html", ".json")) and KEY_SHAPES.search(data):
            sys.exit(f"ABORTED: {rel} contains something shaped like an API key. Nothing was written.")


def build(version: str, files: list) -> str:
    os.makedirs(DOWNLOADS, exist_ok=True)
    for old in os.listdir(DOWNLOADS):
        if old.startswith("Jervis-") and old.endswith(".zip"):
            os.remove(os.path.join(DOWNLOADS, old))
    target = os.path.join(DOWNLOADS, f"Jervis-{version}.zip")
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in files:
            src = os.path.join(APP, rel)
            info = zipfile.ZipInfo(f"{TOP_FOLDER}/{rel}", date_time=zipfile.ZipInfo.from_file(src).date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if rel.endswith(".command") or rel in EXECUTABLE else 0o644
            info.external_attr = (0o100000 | mode) << 16  # a regular file, with its permissions for macOS unzip
            with open(src, "rb") as f:
                z.writestr(info, f.read())
    return target


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def size_label(n: int) -> str:
    return f"{n / (1024 * 1024):.1f} MB"


def update_page(release: dict) -> None:
    """Rewrite the release facts in index.html: elements marked data-release="<key>" and links to the zip."""
    if not os.path.exists(PAGE):
        say("index.html not found; skipped updating the page.")
        return
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    unknown = set(re.findall(r'data-release="(\w+)"', html)) - set(release)
    if unknown:
        sys.exit(f"index.html asks for release facts that don't exist: {sorted(unknown)} (known: {sorted(release)})")
    html, count = re.subn(r'(<(\w+)[^>]*\bdata-release="(\w+)"[^>]*>)[^<]*(</\2>)',
                          lambda m: m.group(1) + str(release[m.group(3)]) + m.group(4), html)
    html, links = re.subn(r'href="downloads/Jervis-[^"]+\.zip"', f'href="downloads/{release["file"]}"', html)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    say(f"Updated index.html: {count} release facts, {links} download links.")


def verify(zip_path: str, release: dict) -> None:
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(zip_path) as z:
        if z.testzip() is not None:
            sys.exit("VERIFY FAILED: the zip is corrupt.")
        names = z.namelist()
        bad = [n for n in names if blocked(n.split("/", 1)[1])]
        missing = [r for r in REQUIRED if f"{TOP_FOLDER}/{r}" not in names]
        if bad or missing:
            sys.exit(f"VERIFY FAILED: blocked files {bad}, missing files {missing}")
        z.extractall(tmp)
        for name in names:
            if name.endswith(".py"):
                py_compile.compile(os.path.join(tmp, name), cfile=os.path.join(tmp, "check.pyc"), doraise=True)
        for name in names:
            if name.endswith(".command") and not (z.getinfo(name).external_attr >> 16) & 0o111:
                sys.exit(f"VERIFY FAILED: {name} is not marked executable.")
    if sha256(zip_path) != release["sha256"]:
        sys.exit("VERIFY FAILED: checksum changed.")
    say(f"Verified: {len(names)} files unpack cleanly, every .py compiles, no personal files, checksum matches.")


def site_url() -> str:
    """The public address the site is published at: --site-url, else the one remembered from the last build."""
    url = ""
    if "--site-url" in sys.argv:
        i = sys.argv.index("--site-url")
        url = sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
    elif os.path.exists(os.path.join(DOWNLOADS, "release.json")):
        with open(os.path.join(DOWNLOADS, "release.json"), encoding="utf-8") as f:
            url = json.load(f).get("site_url", "")
    if url and not re.match(r"^https://[^\s\"'<>]+$", url):
        sys.exit(f"--site-url must be a full https:// address, got {url!r}")
    return url.rstrip("/") + "/" if url else ""


def write_search_files(release: dict) -> None:
    """With a public address: absolute canonical and link-preview tags, structured data, robots.txt and sitemap.xml,
    so search engines and link previews point at the real site."""
    url = release.get("site_url", "")
    with open(PAGE, encoding="utf-8") as f:
        html = f.read()
    data = {
        "@context": "https://schema.org", "@type": "SoftwareApplication", "name": "Jervis",
        "description": "A voice assistant for macOS and Windows that plays media, opens apps, writes documents, "
                       "sets timers, and solves and graphs math.",
        "operatingSystem": "macOS, Windows 10, Windows 11", "applicationCategory": "UtilitiesApplication",
        "softwareVersion": release["version"], "fileSize": release["size"],
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "author": [{"@type": "Person", "name": "Ariel"}, {"@type": "Person", "name": "Shalev"}],
    }
    if url:
        data.update({"url": url, "downloadUrl": f"{url}downloads/{release['file']}",
                     "screenshot": f"{url}assets/img/jervis-chat-1600.webp"})
    block = json.dumps(data, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    html = re.sub(r'(<script type="application/ld\+json">).*?(</script>)', lambda m: f"{m.group(1)}\n  {block}\n  {m.group(2)}",
                  html, count=1, flags=re.S)
    html = re.sub(r'\n  <link rel="canonical"[^>]*>|\n  <meta property="og:url"[^>]*>', "", html)
    if url:
        html = html.replace('<meta name="theme-color"', f'<link rel="canonical" href="{url}" />\n  '
                            f'<meta property="og:url" content="{url}" />\n  <meta name="theme-color"', 1)
    image = f"{url}assets/img/og-jervis.jpg" if url else "assets/img/og-jervis.jpg"
    html = re.sub(r'(<meta property="og:image" content=")[^"]*(")', lambda m: m.group(1) + image + m.group(2), html)
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)
    if not url:
        say("No --site-url given: skipped robots.txt and sitemap.xml.")
        return
    with open(os.path.join(WEBSITE, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {url}sitemap.xml\n")
    with open(os.path.join(WEBSITE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                f"  <url><loc>{url}</loc><lastmod>{release['built']}</lastmod></url>\n</urlset>\n")
    say(f"Search files written for {url}: canonical, link-preview tags, structured data, robots.txt, sitemap.xml.")


def main() -> None:
    version = app_version()
    url = site_url()   # read before the build rewrites release.json
    files = collect()
    missing = [r for r in REQUIRED if r not in files]
    if missing:
        sys.exit(f"The app folder is missing required files: {missing}")
    scan(files)
    zip_path = build(version, files)
    size = os.path.getsize(zip_path)
    release = {"version": version, "file": os.path.basename(zip_path), "bytes": size, "size": size_label(size),
               "sha256": sha256(zip_path), "files": len(files), "built": date.today().isoformat(), "site_url": url}
    with open(os.path.join(DOWNLOADS, "release.json"), "w", encoding="utf-8") as f:
        json.dump(release, f, indent=2)
        f.write("\n")
    say(f"Built {release['file']}: {len(files)} files, {release['size']}, sha256 {release['sha256']}")
    update_page(release)
    write_search_files(release)
    if "--verify" in sys.argv:
        verify(zip_path, release)


if __name__ == "__main__":
    main()
