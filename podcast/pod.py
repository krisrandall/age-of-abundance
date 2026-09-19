#!/usr/bin/env python3
"""pod.py — the whole podcast service in one file.

    pod.py import --show unfinished-cubby --from URL_OR_FILE      one-off: pull a show off its old host
    pod.py new    --show S --mp3 FILE --title "Topic - Guest" --guest "Guest" [--image FILE] [--draft]
    pod.py build  [--show S]          episodes -> public/<show>/feed.xml + pages
    pod.py check  [--show S] [--live] everything that must be true before (and after) a deploy
    pod.py deploy [--show S]          build, check, mp3s to the GitHub release, pages into site/public, push, check --live
    pod.py serve  [--port 8000]       look at public/ locally

Plain files in, plain files out. The contract for shows/ is FORMATS.md. Stdlib + PyYAML;
shells out to curl, ffprobe, rsync, xmllint, gh. See ../WHY.md for the order of
trade-offs and ../CLAUDE.md for the rules.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
SHOWS = ROOT / "shows"
PUBLIC = ROOT / "public"
TEMPLATES = ROOT / "templates"
SITE_PUBLIC = REPO / "site" / "public"     # the Astro site's verbatim-copied folder: the built shows go here
SECRETS = REPO / ".secrets"
GENERATOR = "age-of-abundance pod.py"

NS = {
    "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
    "podcast": "https://podcastindex.org/namespace/1.0",
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
}
ALLOWED_TAGS = {"p", "a", "ul", "ol", "li", "em", "strong", "br", "b", "i"}
PLACEHOLDER = "[Kris:"
MEDIA_TYPES = {".mp3": "audio/mpeg"}
IMAGE_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
SUBSCRIBE_KEYS = [
    ("apple_url", "Apple Podcasts"),
    ("spotify_url", "Spotify"),
    ("pocketcasts_url", "Pocket Casts"),
    ("amazon_url", "Amazon Music"),
    ("youtube_url", "YouTube"),
]


# ----------------------------------------------------------------------------- small tools
class Fail(Exception):
    """A plain-words failure; the CLI prints it and exits 1."""


def say(msg: str) -> None:
    print(msg, flush=True)


def rel(path: Path) -> str:
    """A path as it is best shown: relative to podcast/ when inside it, else as is."""
    try:
        return str(Path(path).relative_to(ROOT))
    except ValueError:
        return str(path)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=False, text=True, capture_output=True, **kw)


def need(tool: str) -> None:
    if shutil.which(tool) is None:
        raise Fail(f"{tool} is not installed (needed by this command)")


def slugify(text: str, limit: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text[:limit].rstrip("-")


def title_stem(title: str) -> str:
    """'Topic - Guest' -> 'Topic' (the part before the last ' - ')."""
    head, sep, _ = title.rpartition(" - ")
    return head if sep else title


def guest_from_title(title: str) -> str:
    _, sep, tail = title.rpartition(" - ")
    return tail.strip() if sep else ""


def parse_iso(s: str) -> dt.datetime:
    d = dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def rfc2822(d: dt.datetime) -> str:
    return email.utils.format_datetime(d.astimezone(dt.timezone.utc), usegmt=True)


def now_utc() -> dt.datetime:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        return dt.datetime.fromtimestamp(int(epoch), tz=dt.timezone.utc)
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def cdata(text: str) -> str:
    return "<![CDATA[" + str(text).replace("]]>", "]]]]><![CDATA[>") + "]]>"


def yaml_mod():
    try:
        import yaml  # noqa: WPS433
    except ImportError as e:  # pragma: no cover
        raise Fail("PyYAML is missing: pip install -r requirements.txt") from e
    return yaml


FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.S)


def read_front_matter(path: Path) -> tuple[dict, str]:
    m = FM_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        raise Fail(f"{path}: no front matter (expected --- yaml --- body)")
    data = yaml_mod().safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise Fail(f"{path}: front matter is not a mapping")
    return data, m.group(2).strip()


def write_front_matter(path: Path, data: dict, body: str) -> None:
    text = yaml_mod().safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)
    path.write_text("---\n" + text + "---\n" + body.strip() + "\n", encoding="utf-8")


def ffprobe_seconds(path: Path) -> int:
    need("ffprobe")
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name",
             "-of", "json", str(path)])
    if r.returncode != 0:
        raise Fail(f"ffprobe failed on {path.name}: {r.stderr.strip()}")
    info = json.loads(r.stdout)
    codecs = {s.get("codec_name") for s in info.get("streams", [])}
    if "mp3" not in codecs:
        raise Fail(f"{path.name} is not an mp3 (codecs: {sorted(c for c in codecs if c)})")
    return int(round(float(info["format"]["duration"])))


def image_info(path: Path) -> tuple[int, int, str, str]:
    """(width, height, 'JPEG'|'PNG'|codec, pixel format) via ffprobe. CMYK JPEGs fail to decode, which is right."""
    need("ffprobe")
    r = run(["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,codec_name,pix_fmt", "-of", "json", str(path)])
    if r.returncode != 0:
        raise Fail(f"ffprobe could not read {path.name}: {r.stderr.strip()[:200]}")
    streams = json.loads(r.stdout).get("streams") or []
    if not streams:
        raise Fail(f"{path.name} is not an image ffprobe understands")
    st = streams[0]
    fmt = {"mjpeg": "JPEG", "png": "PNG"}.get(st.get("codec_name"), str(st.get("codec_name")))
    return int(st["width"]), int(st["height"]), fmt, str(st.get("pix_fmt", ""))


# ----------------------------------------------------------------------------- the content
class Episode:
    def __init__(self, show: "Show", path: Path):
        self.show, self.path = show, path
        self.fm, self.body = read_front_matter(path)
        self.stem = path.stem

    @property
    def title(self) -> str: return str(self.fm.get("title", "")).strip()
    @property
    def guest(self) -> str: return str(self.fm.get("guest") or guest_from_title(self.title))
    @property
    def number(self) -> int: return int(self.fm.get("episode", 0))
    @property
    def season(self) -> int: return int(self.fm.get("season", 1))
    @property
    def kind(self) -> str: return str(self.fm.get("type", "full"))
    @property
    def guid(self) -> str: return str(self.fm.get("guid", "")).strip()
    @property
    def draft(self) -> bool: return bool(self.fm.get("draft", False))
    @property
    def explicit(self) -> bool: return bool(self.fm.get("explicit", self.show.explicit))
    @property
    def published(self) -> dt.datetime: return parse_iso(self.fm["pubdate"])
    @property
    def slug(self) -> str: return re.sub(r"^ep\d+-", "", self.stem)
    @property
    def audio(self) -> Path: return self.show.media / str(self.fm.get("audio", ""))
    @property
    def image(self) -> Path | None:
        name = self.fm.get("image")
        return self.show.art / str(name) if name else None
    @property
    def link(self) -> str: return f"{self.show.site_url}/episodes/{self.slug}/"
    @property
    def audio_url(self) -> str: return f"{self.show.audio_base_url}/{self.audio.name}"
    @property
    def image_url(self) -> str:
        return f"{self.show.site_url}/art/{self.image.name}" if self.image else self.show.cover_url
    @property
    def length(self) -> int: return self.audio.stat().st_size
    @property
    def mime(self) -> str: return MEDIA_TYPES.get(self.audio.suffix.lower(), "")

    def duration(self) -> int:
        return ffprobe_seconds(self.audio)


class Show:
    def __init__(self, slug: str):
        self.slug = slug
        self.dir = SHOWS / slug
        if not (self.dir / "show.yaml").exists():
            raise Fail(f"no show at {self.dir} (expected show.yaml)")
        self.cfg = yaml_mod().safe_load((self.dir / "show.yaml").read_text(encoding="utf-8")) or {}
        self.episodes_dir = self.dir / "episodes"
        self.art = self.dir / "art"
        self.media = self.dir / "media"
        self.import_dir = self.dir / "import"
        self.public = PUBLIC / slug

    # settings
    def get(self, key: str, default=None): return self.cfg.get(key, default)
    @property
    def title(self) -> str: return str(self.cfg.get("title", self.slug))
    @property
    def site_url(self) -> str:
        """Where the feed and pages live, no trailing slash. May carry a path (GitHub Pages)."""
        if self.cfg.get("site_url"):
            return str(self.cfg["site_url"]).rstrip("/")
        if self.cfg.get("hostname"):
            return f"https://{self.cfg['hostname']}"
        raise Fail(f"{self.slug}/show.yaml: site_url is missing")
    @property
    def base_path(self) -> str:
        """The path part of site_url ('' or '/age-of-abundance/unfinished-cubby'), for links inside pages."""
        return re.sub(r"^https?://[^/]+", "", self.site_url).rstrip("/")
    @property
    def audio_base_url(self) -> str:
        """Where the mp3s are fetched from. Default: a media/ folder beside the feed (a server of our own);
        a GitHub release ('https://github.com/<owner>/<repo>/releases/download/<tag>') needs no server."""
        return str(self.cfg.get("audio_base_url") or f"{self.site_url}/media").rstrip("/")
    @property
    def serves_media_itself(self) -> bool: return not self.cfg.get("audio_base_url")
    @property
    def audio_release(self) -> str: return str(self.cfg.get("audio_release", ""))
    @property
    def publish_dir(self) -> Path:
        return Path(str(self.cfg["publish_dir"])) if self.cfg.get("publish_dir") else SITE_PUBLIC / self.slug
    @property
    def writes_index(self) -> bool: return bool(self.cfg.get("index_page", True))
    @property
    def feed_url(self) -> str: return f"{self.site_url}/feed.xml"
    @property
    def cover(self) -> Path: return self.art / str(self.cfg.get("cover", "cover.jpg"))
    @property
    def cover_url(self) -> str: return f"{self.site_url}/art/{self.cover.name}"
    @property
    def explicit(self) -> bool: return bool(self.cfg.get("explicit", False))
    @property
    def language(self) -> str: return str(self.cfg.get("language", "en"))

    def episodes(self, include_drafts: bool = False) -> list[Episode]:
        eps = [Episode(self, p) for p in sorted(self.episodes_dir.glob("ep*.html"))] \
            if self.episodes_dir.exists() else []
        eps = [e for e in eps if include_drafts or not e.draft]
        return sorted(eps, key=lambda e: (e.season, e.number, e.published), reverse=True)

    def next_number(self) -> int:
        eps = self.episodes(include_drafts=True)
        return (max(e.number for e in eps) + 1) if eps else 1


def all_shows() -> list[Show]:
    if not SHOWS.exists():
        return []
    return [Show(p.name) for p in sorted(SHOWS.iterdir()) if (p / "show.yaml").exists()]


def pick_shows(arg: str | None, required: bool = False) -> list[Show]:
    if arg:
        return [Show(arg)]
    if required:
        raise Fail("--show is required for this command")
    shows = all_shows()
    if not shows:
        raise Fail(f"no shows under {SHOWS}")
    return shows


# ----------------------------------------------------------------------------- import
def cmd_import(args) -> None:
    """Pull a show off its old host from its public RSS feed. Idempotent."""
    need("curl")
    slug = args.show
    src = args.source
    show_dir = SHOWS / slug
    for d in ("episodes", "art", "media", "import"):
        (show_dir / d).mkdir(parents=True, exist_ok=True)

    if re.match(r"^https?://", src):
        r = run(["curl", "-sSL", "--fail", "--retry", "3", src])
        if r.returncode != 0:
            raise Fail(f"could not fetch {src}: {r.stderr.strip()}")
        xml_text = r.stdout
        keep = show_dir / "import" / f"feed-{dt.date.today().isoformat()}.xml"
        if not keep.exists():
            keep.write_text(xml_text, encoding="utf-8")
            say(f"saved a copy of the old feed to {rel(keep)}")
    else:
        xml_text = Path(src).read_text(encoding="utf-8")

    root = ET.fromstring(xml_text)
    ch = root.find("channel")
    if ch is None:
        raise Fail("not an RSS feed (no <channel>)")

    def t(el, path, default=""):
        f = el.find(path, NS)
        return (f.text or "").strip() if f is not None and f.text else default

    def attr(el, path, name, default=""):
        f = el.find(path, NS)
        return f.get(name, default) if f is not None else default

    # the show
    cfg_path = show_dir / "show.yaml"
    cover_url = attr(ch, "itunes:image", "href") or t(ch, "image/url")
    cover_name = "cover" + (Path(cover_url.split("?")[0]).suffix.lower() or ".jpg")
    if not cfg_path.exists():
        cats = []
        for c in ch.findall("itunes:category", NS):
            sub = c.find("itunes:category", NS)
            cats.append([c.get("text", "")] + ([sub.get("text", "")] if sub is not None else []))
        cfg = {
            "title": t(ch, "title"),
            "site_url": args.site_url or "https://example.org/podcast",
            "status": "archive",
            "description": t(ch, "description"),
            "language": t(ch, "language", "en"),
            "copyright": t(ch, "copyright"),
            "license": t(ch, "podcast:license") or t(ch, "copyright"),
            "author": t(ch, "itunes:author"),
            "owner_name": t(ch, "itunes:owner/itunes:name") or t(ch, "itunes:author"),
            "owner_email": t(ch, "itunes:owner/itunes:email"),
            "explicit": t(ch, "itunes:explicit", "false").lower() in ("true", "yes"),
            "type": t(ch, "itunes:type", "episodic"),
            "medium": t(ch, "podcast:medium", "podcast"),
            "guid": t(ch, "podcast:guid") or str(uuid.uuid5(uuid.NAMESPACE_URL, t(ch, "atom:link[@rel='self']") or src)),
            "locked": True,
            "categories": cats,
            "cover": cover_name,
            "old_feed_url": attr(ch, "atom:link[@rel='self']", "href") or (src if src.startswith("http") else ""),
            "old_site_url": t(ch, "link"),
        }
        yaml_mod().safe_dump(cfg, open(cfg_path, "w", encoding="utf-8"), sort_keys=False, allow_unicode=True, width=1000)
        say(f"wrote {rel(cfg_path)} — set site_url (and audio_base_url) and check the words")
    else:
        say(f"{rel(cfg_path)} exists, left alone")

    downloads: list[tuple[str, Path, int | None, int | None]] = []  # url, dest, expected bytes, expected seconds
    if cover_url:
        downloads.append((cover_url, show_dir / "art" / cover_name, None, None))

    # the episodes
    items = ch.findall("item")
    written = skipped = 0
    seen_slugs: set[str] = set()
    for it in items:
        title = t(it, "title") or t(it, "itunes:title")
        number = t(it, "itunes:episode") or t(it, "podcast:episode")
        if not number:
            raise Fail(f"'{title}' has no itunes:episode number — give it one in the old host first")
        n = int(number)
        slug_ = slugify(title_stem(title))
        stem = f"ep{n:02d}-{slug_}"
        if stem in seen_slugs:
            raise Fail(f"two episodes would share the file name {stem}")
        seen_slugs.add(stem)
        enc_url = attr(it, "enclosure", "url")
        enc_len = int(attr(it, "enclosure", "length", "0") or 0)
        audio_name = stem + (Path(enc_url.split("?")[0]).suffix.lower() or ".mp3")
        img_url = attr(it, "itunes:image", "href")
        image_name = (stem + (Path(img_url.split("?")[0]).suffix.lower() or ".jpg")) if img_url else ""
        duration = t(it, "itunes:duration")
        secs = None
        if duration:
            parts = [int(float(p)) for p in duration.split(":")]
            secs = sum(p * 60 ** i for i, p in enumerate(reversed(parts)))
        pub = email.utils.parsedate_to_datetime(t(it, "pubDate")) if t(it, "pubDate") else now_utc()
        fm = {
            "title": title,
            "guest": guest_from_title(title),
            "episode": n,
            "season": int(t(it, "itunes:season") or t(it, "podcast:season") or 1),
            "type": t(it, "itunes:episodeType", "full"),
            "guid": t(it, "guid"),
            "pubdate": pub.astimezone(dt.timezone.utc).isoformat(),
            "audio": audio_name,
            "image": image_name,
            "youtube": "",
            "explicit": t(it, "itunes:explicit", "false").lower() in ("true", "yes"),
            "draft": False,
            "rsscom_url": enc_url,
            "rsscom_image_url": img_url,
        }
        body = t(it, "description") or t(it, "content:encoded")
        dest = show_dir / "episodes" / f"{stem}.html"
        if dest.exists() and not args.force:
            skipped += 1
        else:
            write_front_matter(dest, fm, body)
            written += 1
        downloads.append((enc_url, show_dir / "media" / audio_name, enc_len or None, secs))
        if img_url:
            downloads.append((img_url, show_dir / "art" / image_name, None, None))
    say(f"{len(items)} episodes in the feed: {written} files written, {skipped} already there")

    if args.no_media:
        return
    fetch_all(downloads)


def fetch_all(downloads: list[tuple[str, Path, int | None, int | None]]) -> None:
    """Download with resume; verify byte counts (and duration when known). Idempotent."""
    need("curl")
    problems = []
    for url, dest, expect, secs in downloads:
        if dest.exists() and expect and dest.stat().st_size == expect:
            continue
        if dest.exists() and not expect and dest.stat().st_size > 0:
            continue
        if dest.exists() and expect and dest.stat().st_size > expect:
            dest.unlink()  # something else entirely; start again
        part = dest.with_name(dest.name + ".part")
        say(f"fetching {dest.name} ({expect // 1_000_000 if expect else '?'} MB)")
        cmd = ["curl", "-L", "--fail", "--retry", "5", "--retry-all-errors", "-sS", "-o", str(part), url]
        if part.exists() and part.stat().st_size > 0:
            cmd[1:1] = ["-C", "-"]
        r = run(cmd)
        if r.returncode != 0 and "416" in (r.stderr or "") and part.exists():
            pass  # already complete; fall through to the size check
        elif r.returncode != 0:
            problems.append(f"{dest.name}: curl failed ({r.stderr.strip()[:200]})")
            continue
        size = part.stat().st_size if part.exists() else 0
        if expect and size != expect:
            problems.append(f"{dest.name}: got {size} bytes, feed says {expect} (kept the partial)")
            continue
        if secs is not None and dest.suffix.lower() in MEDIA_TYPES:
            got = ffprobe_seconds(part)
            if abs(got - secs) > 2:
                problems.append(f"{dest.name}: ffprobe says {got}s, feed said {secs}s")
                continue
        part.replace(dest)
    if problems:
        raise Fail("some downloads did not verify:\n  " + "\n  ".join(problems))
    say("all media present and verified")


def cmd_import_media_only(args) -> None:
    """Server-side helper: only the enclosures/art of a feed into --dest. No PyYAML needed."""
    src = args.source
    xml_text = run(["curl", "-sSL", "--fail", src]).stdout if src.startswith("http") else Path(src).read_text()
    ch = ET.fromstring(xml_text).find("channel")
    dest = Path(args.dest)
    (dest / "media").mkdir(parents=True, exist_ok=True)
    (dest / "art").mkdir(parents=True, exist_ok=True)
    downloads = []
    cover = ch.find("itunes:image", NS)
    if cover is not None:
        downloads.append((cover.get("href"), dest / "art" / ("cover" + Path(cover.get("href").split("?")[0]).suffix), None, None))
    for it in ch.findall("item"):
        title = (it.findtext("title") or "").strip()
        n = int(it.findtext("itunes:episode", namespaces=NS) or 0)
        stem = f"ep{n:02d}-{slugify(title_stem(title))}"
        enc = it.find("enclosure")
        downloads.append((enc.get("url"), dest / "media" / (stem + Path(enc.get("url").split("?")[0]).suffix.lower()),
                          int(enc.get("length") or 0) or None, None))
        img = it.find("itunes:image", NS)
        if img is not None:
            downloads.append((img.get("href"), dest / "art" / (stem + Path(img.get("href").split("?")[0]).suffix.lower()), None, None))
    fetch_all(downloads)


# ----------------------------------------------------------------------------- new
def cmd_new(args) -> None:
    show = Show(args.show)
    src = Path(args.mp3).expanduser()
    if not src.exists():
        raise Fail(f"no such file: {src}")
    if src.suffix.lower() not in MEDIA_TYPES:
        raise Fail(f"{src.name}: only .mp3 is served (convert with ffmpeg first)")
    secs = ffprobe_seconds(src)  # also proves it is an mp3
    title = args.title.strip()
    guest = (args.guest or guest_from_title(title)).strip()
    if guest and not title.endswith(f" - {guest}"):
        title = f"{title} - {guest}"
    n = args.number or show.next_number()
    stem = f"ep{n:02d}-{slugify(title_stem(title))}"
    for d in (show.episodes_dir, show.art, show.media):
        d.mkdir(parents=True, exist_ok=True)
    dest_md = show.episodes_dir / f"{stem}.html"
    if dest_md.exists():
        raise Fail(f"{rel(dest_md)} already exists")
    audio = show.media / f"{stem}.mp3"
    shutil.copy2(src, audio)
    if audio.stat().st_size != src.stat().st_size:
        raise Fail("copy of the mp3 came out a different size; try again")
    image_name = ""
    if args.image:
        img = Path(args.image).expanduser()
        if img.suffix.lower() not in IMAGE_TYPES:
            raise Fail("episode art must be .jpg or .png")
        image_name = f"{stem}{img.suffix.lower()}"
        shutil.copy2(img, show.art / image_name)
    fm = {
        "title": title,
        "guest": guest,
        "episode": n,
        "season": args.season,
        "type": args.type,
        "guid": str(uuid.uuid4()),
        "pubdate": (parse_iso(args.publish) if args.publish else now_utc()).isoformat(),
        "audio": audio.name,
        "image": image_name,
        "youtube": "",
        "explicit": show.explicit,
        "draft": bool(args.draft),
    }
    write_front_matter(dest_md, fm, f"<p>{PLACEHOLDER} what this conversation is about, in a paragraph or two]</p>")
    say(f"episode {n} scaffolded ({secs // 60} min): {rel(dest_md)}")
    say("write the description in that file (HTML: p, a, ul, ol, li, em, strong), then:")
    say(f"    python3 pod.py build --show {show.slug} && python3 pod.py check --show {show.slug} && python3 pod.py deploy --show {show.slug}")


# ----------------------------------------------------------------------------- build
def feed_xml(show: Show, episodes: list[Episode], built: dt.datetime) -> str:
    c = show.cfg
    o = []
    o.append('<?xml version="1.0" encoding="UTF-8"?>')
    o.append(f'<rss xmlns:podcast="{NS["podcast"]}" xmlns:itunes="{NS["itunes"]}" '
             f'xmlns:atom="{NS["atom"]}" xml:lang={quoteattr(show.language)} version="2.0">')
    o.append("  <channel>")
    o.append(f"    <title>{cdata(show.title)}</title>")
    o.append(f"    <link>{escape(show.site_url)}</link>")
    o.append(f'    <atom:link href={quoteattr(show.feed_url)} rel="self" type="application/rss+xml"/>')
    o.append(f"    <description>{cdata(str(c.get('description', '')).strip())}</description>")
    o.append(f"    <generator>{escape(GENERATOR)}</generator>")
    o.append(f"    <lastBuildDate>{rfc2822(built)}</lastBuildDate>")
    o.append(f"    <language>{escape(show.language)}</language>")
    if c.get("copyright"):
        o.append(f"    <copyright>{cdata(c['copyright'])}</copyright>")
    o.append(f"    <itunes:image href={quoteattr(show.cover_url)}/>")
    o.append(f"    <podcast:guid>{escape(str(c['guid']))}</podcast:guid>")
    o.append("    <image>")
    o.append(f"      <url>{escape(show.cover_url)}</url>")
    o.append(f"      <title>{escape(show.title)}</title>")
    o.append(f"      <link>{escape(show.site_url)}</link>")
    o.append("    </image>")
    locked = "yes" if c.get("locked", True) else "no"
    owner_attr = f" owner={quoteattr(c['owner_email'])}" if c.get("owner_email") else ""
    o.append(f"    <podcast:locked{owner_attr}>{locked}</podcast:locked>")
    if c.get("license"):
        o.append(f"    <podcast:license>{cdata(c['license'])}</podcast:license>")
    o.append(f"    <itunes:author>{escape(str(c.get('author', '')))}</itunes:author>")
    o.append("    <itunes:owner>")
    o.append(f"      <itunes:name>{escape(str(c.get('owner_name') or c.get('author', '')))}</itunes:name>")
    if c.get("owner_email"):
        o.append(f"      <itunes:email>{escape(c['owner_email'])}</itunes:email>")
    o.append("    </itunes:owner>")
    o.append(f"    <itunes:explicit>{'true' if show.explicit else 'false'}</itunes:explicit>")
    o.append(f"    <itunes:type>{escape(str(c.get('type', 'episodic')))}</itunes:type>")
    for cat in c.get("categories", []):
        cat = [cat] if isinstance(cat, str) else list(cat)
        if len(cat) == 1:
            o.append(f"    <itunes:category text={quoteattr(cat[0])}/>")
        else:
            o.append(f"    <itunes:category text={quoteattr(cat[0])}>")
            o.append(f"      <itunes:category text={quoteattr(cat[1])}/>")
            o.append("    </itunes:category>")
    o.append(f"    <podcast:medium>{escape(str(c.get('medium', 'podcast')))}</podcast:medium>")
    for e in episodes:
        o.append("    <item>")
        o.append(f"      <title>{cdata(e.title)}</title>")
        o.append(f"      <itunes:title>{cdata(e.title)}</itunes:title>")
        o.append(f"      <description>{cdata(e.body)}</description>")
        o.append(f"      <link>{escape(e.link)}</link>")
        o.append(f'      <enclosure url={quoteattr(e.audio_url)} length="{e.length}" type={quoteattr(e.mime)}/>')
        o.append(f'      <guid isPermaLink="false">{escape(e.guid)}</guid>')
        o.append(f"      <itunes:duration>{e.duration()}</itunes:duration>")
        o.append(f"      <itunes:episodeType>{escape(e.kind)}</itunes:episodeType>")
        o.append(f"      <itunes:season>{e.season}</itunes:season>")
        o.append(f"      <podcast:season>{e.season}</podcast:season>")
        o.append(f"      <itunes:episode>{e.number}</itunes:episode>")
        o.append(f"      <podcast:episode>{e.number}</podcast:episode>")
        o.append(f"      <itunes:explicit>{'true' if e.explicit else 'false'}</itunes:explicit>")
        o.append(f"      <pubDate>{rfc2822(e.published)}</pubDate>")
        o.append(f"      <itunes:image href={quoteattr(e.image_url)}/>")
        o.append("    </item>")
    o.append("  </channel>")
    o.append("</rss>")
    return "\n".join(o) + "\n"


def render(template: str, values: dict) -> str:
    """{{key}} -> html-escaped value; {{key_html}} -> verbatim."""
    def sub(m):
        key = m.group(1)
        v = values.get(key, "")
        return str(v) if key.endswith("_html") else html.escape(str(v), quote=True)
    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", sub, template)


def human_duration(secs: int) -> str:
    h, rem = divmod(secs, 3600)
    m = rem // 60
    return f"{h} h {m} min" if h else f"{m} min"


def subscribe_links_html(show: Show) -> str:
    links = [(show.cfg[k], label) for k, label in SUBSCRIBE_KEYS if show.cfg.get(k)]
    links.append((show.feed_url, "RSS"))
    return "\n".join(f'<a class="sub" href="{html.escape(u, quote=True)}">{html.escape(label)}</a>' for u, label in links)


def cmd_build(args) -> None:
    built = now_utc()
    for show in pick_shows(args.show):
        eps = show.episodes()
        out = show.public
        (out / "episodes").mkdir(parents=True, exist_ok=True)
        (out / "art").mkdir(exist_ok=True)
        # art is copied (small, in git); media is a symlink to the show's folder only when we serve it ourselves
        for p in show.art.glob("*"):
            if p.is_file():
                shutil.copy2(p, out / "art" / p.name)
        link = out / "media"
        if link.is_symlink() or link.exists():
            if link.is_symlink():
                link.unlink()
            else:
                shutil.rmtree(link)
        if show.serves_media_itself:
            link.symlink_to(os.path.relpath(show.media, out))
        base = show.base_path
        durations = {e.guid: e.duration() for e in eps}
        (out / "feed.xml").write_text(feed_xml(show, eps, built), encoding="utf-8")
        css = (TEMPLATES / "style.css").read_text(encoding="utf-8")
        (out / "style.css").write_text(css, encoding="utf-8")
        index_t = (TEMPLATES / "index.html").read_text(encoding="utf-8")
        ep_t = (TEMPLATES / "episode.html").read_text(encoding="utf-8")
        common = {
            "show_title": show.title,
            "show_description_html": "".join(f"<p>{html.escape(p.strip())}</p>" for p in str(show.cfg.get("description", "")).split("\n\n") if p.strip()),
            "base": base,
            "cover_url": f"{base}/art/{show.cover.name}",
            "cover_abs": show.cover_url,
            "feed_url": show.feed_url,
            "site_url": show.site_url,
            "subscribe_html": subscribe_links_html(show),
            "home_url": show.cfg.get("home_url", "https://age-of-abundance.org/"),
            "home_label": show.cfg.get("home_label", "Age of Abundance"),
            "status_note_html": html.escape(str(show.cfg.get("status_note", ""))),
            "year": str(built.year),
        }
        items = []
        for e in eps:
            item = {
                **common,
                "title": e.title,
                "guest": e.guest,
                "number": e.number,
                "date": e.published.strftime("%-d %B %Y"),
                "duration": human_duration(durations[e.guid]),
                "audio_url": e.audio_url,
                "image_url": f"{base}/art/" + (e.image.name if e.image else show.cover.name),
                "image_abs": e.image_url,
                "link": f"{base}/episodes/{e.slug}/",
                "description_html": e.body,
                "youtube_url": str(e.fm.get("youtube") or ""),
                "youtube_html": (f'<p><a href="{html.escape(str(e.fm["youtube"]), quote=True)}">Watch on YouTube</a></p>' if e.fm.get("youtube") else ""),
            }
            items.append(item)
            ep_dir = out / "episodes" / e.slug
            ep_dir.mkdir(parents=True, exist_ok=True)
            (ep_dir / "index.html").write_text(render(ep_t, item), encoding="utf-8")
        list_html = "\n".join(
            '<li class="ep"><a class="ep-art" href="{link}"><img src="{image_url}" alt="" loading="lazy"></a>'
            '<div class="ep-body"><h2><a href="{link}">{title}</a></h2>'
            '<p class="meta">Episode {number} · {date} · {duration}</p>'
            '<audio controls preload="none" src="{audio_url}"></audio></div></li>'.format(
                **{k: html.escape(str(v), quote=True) for k, v in i.items() if not k.endswith("_html")})
            for i in items)
        if show.writes_index:
            (out / "index.html").write_text(render(index_t, {**common, "episodes_html": list_html, "episode_count": len(items)}), encoding="utf-8")
        elif (out / "index.html").exists():
            (out / "index.html").unlink()
        # keep public/<show>/episodes free of pages for episodes that no longer exist
        want = {e.slug for e in eps}
        for d in (out / "episodes").iterdir():
            if d.is_dir() and d.name not in want:
                shutil.rmtree(d)
        say(f"{show.slug}: {len(eps)} episode(s) -> {rel(out)}/feed.xml")


# ----------------------------------------------------------------------------- check
REQUIRED_CHANNEL = ["title", "link", "description", "language", "itunes:image", "itunes:author",
                    "itunes:explicit", "itunes:category", "podcast:guid", "atom:link"]
REQUIRED_ITEM = ["title", "enclosure", "guid", "pubDate", "itunes:duration", "itunes:explicit"]


def check_show(show: Show, live: bool) -> list[str]:
    bad: list[str] = []
    eps = show.episodes(include_drafts=True)
    live_eps = [e for e in eps if not e.draft]

    # secrets never tracked (the repo is public)
    r = run(["git", "-C", str(REPO), "ls-files", str(SECRETS)])
    if r.stdout.strip():
        bad.append("files under .secrets/ are tracked by git: " + r.stdout.strip().replace("\n", ", "))

    # the show itself
    for key in ("title", "description", "author", "guid", "categories"):
        if not show.cfg.get(key):
            bad.append(f"show.yaml: {key} is empty")
    if PLACEHOLDER in str(show.cfg.get("description", "")):
        bad.append("show.yaml: description still holds a [Kris: …] placeholder")
    if not show.cover.exists():
        bad.append(f"cover art missing: {rel(show.cover)}")
    else:
        bad += check_image(show.cover, "cover")

    # every episode
    seen_guid: dict[str, str] = {}
    seen_num: dict[tuple[int, int], str] = {}
    for e in eps:
        who = e.path.name
        if not re.match(r"^ep\d{2,}-[a-z0-9-]+\.html$", who):
            bad.append(f"{who}: file name must be epNN-slug.html")
        if not e.title:
            bad.append(f"{who}: no title")
        if not e.guid:
            bad.append(f"{who}: no guid")
        elif e.guid in seen_guid:
            bad.append(f"{who}: guid duplicates {seen_guid[e.guid]}")
        seen_guid[e.guid] = who
        key = (e.season, e.number)
        if e.number < 1:
            bad.append(f"{who}: episode number must be 1 or more")
        elif key in seen_num:
            bad.append(f"{who}: season {e.season} episode {e.number} duplicates {seen_num[key]}")
        seen_num[key] = who
        try:
            if e.published > now_utc() + dt.timedelta(minutes=5):
                bad.append(f"{who}: pubdate is in the future ({e.fm['pubdate']})")
        except (KeyError, ValueError) as ex:
            bad.append(f"{who}: bad pubdate ({ex})")
        if e.kind not in ("full", "trailer", "bonus"):
            bad.append(f"{who}: type must be full, trailer or bonus")
        if e.draft:
            continue
        if PLACEHOLDER in e.body or not e.body.strip():
            bad.append(f"{who}: description is empty or still a [Kris: …] placeholder")
        if len(e.body) > 4000:
            bad.append(f"{who}: description is {len(e.body)} chars; Apple shows at most 4000")
        for tag in set(re.findall(r"</?([a-zA-Z0-9]+)", e.body)):
            if tag.lower() not in ALLOWED_TAGS:
                bad.append(f"{who}: <{tag}> is not one of the tags podcast apps keep ({', '.join(sorted(ALLOWED_TAGS))})")
        if not e.fm.get("audio"):
            bad.append(f"{who}: no audio file named")
        elif not re.match(r"^[a-z0-9.-]+$", e.audio.name) or not e.audio.name.startswith(e.stem):
            bad.append(f"{who}: audio file must be {e.stem}.mp3 (letters, digits, dots, hyphens)")
        elif not e.audio.exists():
            bad.append(f"{who}: audio file missing: {rel(e.audio)}")
        elif not e.mime:
            bad.append(f"{who}: only .mp3 is served")
        if e.image:
            if not e.image.exists():
                bad.append(f"{who}: episode art missing: {rel(e.image)}")
            else:
                bad += check_image(e.image, who)

    # the old feed, while it is kept: same GUIDs, same titles and numbers
    for old in sorted(show.import_dir.glob("*.xml")) if show.import_dir.exists() else []:
        ch = ET.fromstring(old.read_text(encoding="utf-8")).find("channel")
        old_items = {(it.findtext("guid") or "").strip(): it for it in ch.findall("item")}
        ours = {e.guid: e for e in live_eps}
        for g in old_items.keys() - ours.keys():
            bad.append(f"guid {g} ('{old_items[g].findtext('title')}') is in {old.name} but not in episodes/")
        for g in ours.keys() - old_items.keys():
            bad.append(f"guid {g} ({ours[g].path.name}) is not in {old.name} — new episodes do not belong in an archive show" if show.cfg.get("status") == "archive" else "")
        for g in ours.keys() & old_items.keys():
            it = old_items[g]
            if (it.findtext("title") or "").strip() != ours[g].title:
                bad.append(f"{ours[g].path.name}: title differs from {old.name}")
            if int(it.findtext("itunes:episode", namespaces=NS) or 0) != ours[g].number:
                bad.append(f"{ours[g].path.name}: episode number differs from {old.name}")
        old_guid = (ch.findtext("podcast:guid", namespaces=NS) or "").strip()
        if old_guid and old_guid != str(show.cfg.get("guid")):
            bad.append(f"show.yaml guid differs from {old.name} ({old_guid})")
    bad = [b for b in bad if b]

    # the built feed
    feed = show.public / "feed.xml"
    if not feed.exists():
        bad.append(f"{rel(feed)} not built yet (run build)")
        return bad
    need("xmllint")
    r = run(["xmllint", "--noout", str(feed)])
    if r.returncode != 0:
        bad.append(f"feed.xml is not well-formed: {r.stderr.strip()[:300]}")
        return bad
    root = ET.fromstring(feed.read_bytes())
    ch = root.find("channel")
    for tag in REQUIRED_CHANNEL:
        if ch.find(tag, NS) is None:
            bad.append(f"feed.xml: channel lacks <{tag}>")
    items = ch.findall("item")
    if len(items) != len(live_eps):
        bad.append(f"feed.xml has {len(items)} items, episodes/ has {len(live_eps)} live episodes (rebuild)")
    for it in items:
        for tag in REQUIRED_ITEM:
            if it.find(tag, NS) is None:
                bad.append(f"feed.xml: item '{it.findtext('title')}' lacks <{tag}>")
        enc = it.find("enclosure")
        if enc is not None:
            local = show.media / Path(enc.get("url")).name
            if local.exists() and str(local.stat().st_size) != enc.get("length"):
                bad.append(f"feed.xml: enclosure length for {local.name} is stale (rebuild)")

    if live:
        bad += check_live(show, items, ch)
    return bad


def check_image(path: Path, who: str) -> list[str]:
    bad = []
    try:
        w, h, fmt, space = image_info(path)
    except Fail as ex:
        return [str(ex)]
    if w != h:
        bad.append(f"{who}: art must be square, {path.name} is {w}x{h}")
    if not (1400 <= w <= 3000):
        bad.append(f"{who}: art must be 1400–3000 px, {path.name} is {w}px")
    if fmt not in ("JPEG", "PNG"):
        bad.append(f"{who}: art must be JPEG or PNG, {path.name} is {fmt}")
    if "gray" in space:
        bad.append(f"{who}: art must be in colour (RGB), {path.name} is {space}")
    return bad


def http_req(method: str, url: str, headers: dict | None = None, timeout: int = 60):
    """(status, headers, body) of the FINAL response after redirects, via curl. Body only for GET."""
    need("curl")
    cmd = ["curl", "-sS", "-L", "--max-time", str(timeout), "-A", "pod.py check", "-D", "-"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    body_file = None
    if method == "HEAD":
        cmd += ["-I"]
    else:
        body_file = tempfile.NamedTemporaryFile(delete=False)
        body_file.close()
        cmd += ["-o", body_file.name]
    r = run(cmd + [url])
    if r.returncode != 0:
        return 0, {"error": r.stderr.strip()[:200]}, b""
    blocks = [b for b in re.split(r"\r?\n\r?\n", r.stdout.strip()) if b.startswith("HTTP/")]
    if not blocks:
        return 0, {"error": "no response"}, b""
    lines = blocks[-1].splitlines()
    status = int(lines[0].split()[1])
    hd = {}
    for line in lines[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            hd[k.strip().lower()] = v.strip()
    body = b""
    if body_file:
        body = Path(body_file.name).read_bytes()
        os.unlink(body_file.name)
    return status, hd, body


def check_live(show: Show, items, ch) -> list[str]:
    bad = []
    local = (show.public / "feed.xml").read_bytes()
    st, hd, body = http_req("GET", show.feed_url)
    if st != 200:
        return [f"live: GET {show.feed_url} -> {st} {hd.get('error', '')}"]
    ctype = hd.get("content-type", "")
    if not (ctype.startswith("application/rss+xml") or ctype.startswith("application/xml") or ctype.startswith("text/xml")):
        bad.append(f"live: feed content-type is {ctype!r}, want an XML type")
    if body != local:
        bad.append("live: the feed on the server differs from public/feed.xml (deploy)")
    for it in items:
        enc = it.find("enclosure")
        url = enc.get("url")
        st, hd, _ = http_req("HEAD", url, {"Accept-Encoding": "gzip"})
        if st != 200:
            bad.append(f"live: HEAD {url} -> {st} {hd.get('error', '')}")
            continue
        ctype = hd.get("content-type", "")
        # GitHub serves release assets as application/octet-stream; apps go by the enclosure's type attribute
        if not (ctype.startswith("audio/mpeg") or ctype.startswith("application/octet-stream")):
            bad.append(f"live: {Path(url).name} content-type {ctype!r}")
        if hd.get("accept-ranges") != "bytes":
            bad.append(f"live: {Path(url).name} does not advertise byte ranges")
        if hd.get("content-length") != enc.get("length"):
            bad.append(f"live: {Path(url).name} is {hd.get('content-length')} bytes on the server, feed says {enc.get('length')}")
        if hd.get("content-encoding"):
            bad.append(f"live: {Path(url).name} is being compressed ({hd.get('content-encoding')}) — podcast apps need it raw")
        img = it.find("itunes:image", NS)
        if img is not None:
            st, hd, _ = http_req("HEAD", img.get("href"))
            if st != 200:
                bad.append(f"live: HEAD {img.get('href')} -> {st}")
        st, hd, _ = http_req("HEAD", it.findtext("link"))
        if st != 200:
            bad.append(f"live: HEAD {it.findtext('link')} -> {st}")
    if items:
        url = items[0].find("enclosure").get("url")
        st, hd, _ = http_req("GET", url, {"Range": "bytes=0-1"})
        if st != 206:
            bad.append(f"live: a Range request on {Path(url).name} returned {st}, want 206")
    cover = ch.find("itunes:image", NS)
    if cover is not None:
        st, _, _ = http_req("HEAD", cover.get("href"))
        if st != 200:
            bad.append(f"live: HEAD {cover.get('href')} -> {st}")
    if show.writes_index:
        st, hd, _ = http_req("HEAD", show.site_url + "/")
        if st != 200 or not hd.get("content-type", "").startswith("text/html"):
            bad.append(f"live: HEAD {show.site_url}/ -> {st} {hd.get('content-type', '')}")
    return bad


def cmd_check(args) -> None:
    failed = False
    for show in pick_shows(args.show):
        bad = check_show(show, args.live)
        if bad:
            failed = True
            say(f"{show.slug}: {len(bad)} problem(s)")
            for b in bad:
                say(f"  - {b}")
        else:
            say(f"{show.slug}: ok ({len(show.episodes())} episodes{', live checks passed' if args.live else ''})")
    if failed:
        sys.exit(1)


# ----------------------------------------------------------------------------- deploy
def release_assets(tag: str) -> dict[str, int]:
    r = run(["gh", "release", "view", tag, "--repo", repo_slug(), "--json", "assets"])
    if r.returncode != 0:
        raise Fail(f"no GitHub release tagged {tag} ({r.stderr.strip()[:200]}); create it: gh release create {tag} --title ...")
    return {a["name"]: int(a["size"]) for a in json.loads(r.stdout)["assets"]}


def repo_slug() -> str:
    r = run(["git", "-C", str(REPO), "remote", "get-url", "origin"])
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+)", r.stdout)
    if not m:
        raise Fail("origin is not a GitHub remote")
    return m.group(1)


def push_audio(show: Show, eps: list[Episode]) -> None:
    """Every episode's mp3 as an asset of the show's release; already-present files are left alone."""
    need("gh")
    if not show.audio_release:
        raise Fail(f"{show.slug}: audio_release (the GitHub release tag) is not set in show.yaml")
    have = release_assets(show.audio_release)
    for e in eps:
        name, size = e.audio.name, e.length
        if name in have and have[name] == size:
            continue
        if name in have:
            raise Fail(f"{show.slug}: {name} is on the release with a different size ({have[name]} vs {size}); "
                       "a published file is never replaced — fix the local copy or use a new file name")
        say(f"{show.slug}: uploading {name} ({size // 1_000_000} MB) to release {show.audio_release}")
        r = subprocess.run(["gh", "release", "upload", show.audio_release, str(e.audio), "--repo", repo_slug()])
        if r.returncode != 0:
            raise Fail(f"{show.slug}: upload of {name} failed")
    have = release_assets(show.audio_release)
    missing = [e.audio.name for e in eps if have.get(e.audio.name) != e.length]
    if missing:
        raise Fail(f"{show.slug}: not on the release with the right size: {', '.join(missing)}")


def cmd_deploy(args) -> None:
    need("rsync")
    cmd_build(args)
    cmd_check(argparse.Namespace(show=args.show, live=False))
    shows = pick_shows(args.show)
    for show in shows:
        eps = show.episodes()
        if show.serves_media_itself:
            raise Fail(f"{show.slug}: no audio_base_url — this deploy publishes through GitHub; "
                       "set audio_base_url/audio_release in show.yaml")
        push_audio(show, eps)
        dest = show.publish_dir
        dest.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["rsync", "-rt", "--delete", "--exclude=/media", f"{show.public}/", f"{dest}/"])
        if r.returncode != 0:
            raise Fail(f"{show.slug}: copying the built pages into {rel(dest)} failed")
        say(f"{show.slug}: pages and feed -> {dest.relative_to(REPO)}")
    paths = [str(s.publish_dir) for s in shows]
    run(["git", "-C", str(REPO), "add", "-A", *paths])
    if run(["git", "-C", str(REPO), "diff", "--cached", "--quiet", "--", *paths]).returncode == 0:
        say("nothing new to publish (the site already has this build)")
    else:
        msg = "podcast: publish " + ", ".join(s.slug for s in shows)
        if run(["git", "-C", str(REPO), "commit", "-q", "-m", msg, "--", *paths]).returncode != 0:
            raise Fail("commit failed")
        if run(["git", "-C", str(REPO), "push", "-q"]).returncode != 0:
            raise Fail("push failed — the pages are committed locally; push by hand")
        say("pushed; GitHub Pages rebuilds the site in a minute or two")
    # wait for the live feed to match, then run the full live check
    for show in shows:
        local = (show.public / "feed.xml").read_bytes()
        for _ in range(30):
            st, _, body = http_req("GET", show.feed_url)
            if st == 200 and body == local:
                break
            time.sleep(10)
        else:
            say(f"{show.slug}: the live feed still differs after five minutes; check GitHub Actions")
    cmd_check(argparse.Namespace(show=args.show, live=True))


# ----------------------------------------------------------------------------- serve
def cmd_serve(args) -> None:
    if not PUBLIC.exists():
        raise Fail("nothing built yet (run build)")
    os.chdir(PUBLIC)
    handler = http.server.SimpleHTTPRequestHandler
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as srv:
        say(f"serving {PUBLIC} at http://127.0.0.1:{args.port}/<show>/  (Ctrl-C to stop)")
        for s in all_shows():
            say(f"  http://127.0.0.1:{args.port}/{s.slug}/")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass


# ----------------------------------------------------------------------------- cli
def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="pod.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("import", help="pull a show off its old host (one-off, idempotent)")
    s.add_argument("--show", required=True)
    s.add_argument("--from", dest="source", required=True, help="feed URL or a saved feed file")
    s.add_argument("--site-url", help="where the feed will live, written into show.yaml")
    s.add_argument("--force", action="store_true", help="overwrite episode files that exist")
    s.add_argument("--no-media", action="store_true", help="metadata only, no downloads")
    s.set_defaults(fn=cmd_import)

    s = sub.add_parser("import-media-only", help="server-side: just the audio and art of a feed into --dest")
    s.add_argument("--from", dest="source", required=True)
    s.add_argument("--dest", required=True)
    s.set_defaults(fn=cmd_import_media_only)

    s = sub.add_parser("new", help="scaffold an episode from an mp3")
    s.add_argument("--show", required=True)
    s.add_argument("--mp3", required=True)
    s.add_argument("--title", required=True, help='"Topic - Guest" (the guest is appended if missing)')
    s.add_argument("--guest", default="")
    s.add_argument("--image", help="episode art (jpg/png, square, 1400-3000 px)")
    s.add_argument("--publish", help="ISO date/time; default now")
    s.add_argument("--number", type=int, help="episode number; default next")
    s.add_argument("--season", type=int, default=1)
    s.add_argument("--type", choices=["full", "trailer", "bonus"], default="full")
    s.add_argument("--draft", action="store_true")
    s.set_defaults(fn=cmd_new)

    for name, fn, hlp in (("build", cmd_build, "write feed.xml and pages to public/<show>/"),
                          ("deploy", cmd_deploy, "build, check, audio to the GitHub release, pages into site/, push, check --live")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("--show")
        s.set_defaults(fn=fn)

    s = sub.add_parser("check", help="everything that must be true before a deploy")
    s.add_argument("--show")
    s.add_argument("--live", action="store_true", help="also probe the live server")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("serve", help="local preview of public/")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except Fail as ex:
        say(f"error: {ex}")
        sys.exit(1)


if __name__ == "__main__":
    main()
