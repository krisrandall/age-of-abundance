"""Unit tests for pod.py — the pure parts, plus one end-to-end build of a throwaway show.
Run: cd podcast && python3 -m unittest"""
import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pod  # noqa: E402


class PureFunctions(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(pod.slugify("Work life balance just means lazy"), "work-life-balance-just-means-lazy")
        self.assertEqual(pod.slugify("A Yarn about The Voice - Dinnawhan & BJ"), "a-yarn-about-the-voice-dinnawhan-bj")
        self.assertEqual(pod.slugify("Café, Über & 100%"), "cafe-uber-100")
        self.assertLessEqual(len(pod.slugify("x " * 100)), 60)

    def test_title_stem_and_guest(self):
        self.assertEqual(pod.title_stem("Good Karma - Amy Churchouse"), "Good Karma")
        self.assertEqual(pod.guest_from_title("Good Karma - Amy Churchouse"), "Amy Churchouse")
        self.assertEqual(pod.title_stem("No guest here"), "No guest here")
        self.assertEqual(pod.guest_from_title("No guest here"), "")
        self.assertEqual(pod.title_stem("Work-life - a - b"), "Work-life - a")

    def test_rfc2822_is_gmt_like_the_old_feed(self):
        d = pod.parse_iso("2023-09-14T04:03:44+00:00")
        self.assertEqual(pod.rfc2822(d), "Thu, 14 Sep 2023 04:03:44 GMT")
        d = pod.parse_iso("2026-09-14T21:00:00+10:00")
        self.assertEqual(pod.rfc2822(d), "Mon, 14 Sep 2026 11:00:00 GMT")

    def test_cdata_splits_terminator(self):
        self.assertEqual(pod.cdata("a]]>b"), "<![CDATA[a]]]]><![CDATA[>b]]>")
        self.assertEqual(pod.cdata("<p>x &amp; y</p>"), "<![CDATA[<p>x &amp; y</p>]]>")

    def test_render_escapes_unless_html(self):
        out = pod.render("<h1>{{title}}</h1>{{body_html}}", {"title": "A & B <c>", "body_html": "<p>ok</p>"})
        self.assertEqual(out, "<h1>A &amp; B &lt;c&gt;</h1><p>ok</p>")
        self.assertEqual(pod.render("{{missing}}", {}), "")

    def test_front_matter_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ep01-x.html"
            fm = {"title": "T: with colon - G", "episode": 1, "pubdate": "2026-01-01T00:00:00+00:00", "draft": False}
            pod.write_front_matter(p, fm, "<p>body</p>\n")
            got, body = pod.read_front_matter(p)
            self.assertEqual(got, fm)
            self.assertEqual(body, "<p>body</p>")
            self.assertEqual(list(got), list(fm))  # key order kept

    def test_human_duration(self):
        self.assertEqual(pod.human_duration(3452), "57 min")
        self.assertEqual(pod.human_duration(5379), "1 h 29 min")


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("xmllint"),
                     "needs ffmpeg and xmllint")
class EndToEnd(unittest.TestCase):
    """A throwaway show: new -> build -> check, in a temp copy of the layout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.old = (pod.SHOWS, pod.PUBLIC)
        pod.SHOWS, pod.PUBLIC = self.tmp / "shows", self.tmp / "public"
        show = pod.SHOWS / "testshow"
        (show / "art").mkdir(parents=True)
        (show / "show.yaml").write_text(
            "title: Test Show\nsite_url: https://podcast.example.org\ndescription: Just a test.\nauthor: A\n"
            "guid: 11111111-1111-5111-8111-111111111111\ncategories:\n  - [Government]\n"
            "home_url: https://example.org/\n", encoding="utf-8")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0x2f6f5e:s=1400x1400",
                        "-frames:v", "1", str(show / "art" / "cover.jpg")], check=True)
        self.mp3 = self.tmp / "in.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "2",
                        "-q:a", "9", str(self.mp3)], check=True)

    def tearDown(self):
        pod.SHOWS, pod.PUBLIC = self.old
        shutil.rmtree(self.tmp)

    def test_new_build_check(self):
        pod.main(["new", "--show", "testshow", "--mp3", str(self.mp3), "--title", "First words", "--guest", "Simon"])
        ep = next((pod.SHOWS / "testshow" / "episodes").glob("ep01-*.html"))
        self.assertEqual(ep.name, "ep01-first-words.html")
        fm, body = pod.read_front_matter(ep)
        self.assertEqual(fm["title"], "First words - Simon")
        self.assertIn(pod.PLACEHOLDER, body)
        # a placeholder must not ship
        pod.main(["build", "--show", "testshow"])
        with self.assertRaises(SystemExit):
            pod.main(["check", "--show", "testshow"])
        pod.write_front_matter(ep, fm, "<p>Simon and Kris talk about <em>the basics</em>.</p>")
        os.environ["SOURCE_DATE_EPOCH"] = "1800000000"
        try:
            pod.main(["build", "--show", "testshow"])
            pod.main(["check", "--show", "testshow"])
        finally:
            del os.environ["SOURCE_DATE_EPOCH"]
        feed = pod.PUBLIC / "testshow" / "feed.xml"
        root = ET.fromstring(feed.read_bytes())
        ch = root.find("channel")
        self.assertEqual(ch.findtext("title"), "Test Show")
        self.assertEqual(ch.find("atom:link", pod.NS).get("href"), "https://podcast.example.org/feed.xml")
        self.assertEqual(ch.findtext("podcast:locked", namespaces=pod.NS), "yes")
        items = ch.findall("item")
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it.findtext("guid"), fm["guid"])
        self.assertEqual(it.find("enclosure").get("url"), "https://podcast.example.org/media/ep01-first-words.mp3")
        self.assertEqual(it.find("enclosure").get("length"), str(self.mp3.stat().st_size))
        self.assertEqual(it.findtext("itunes:duration", namespaces=pod.NS), "2")
        self.assertEqual(it.findtext("link"), "https://podcast.example.org/episodes/first-words/")
        self.assertEqual(it.find("itunes:image", pod.NS).get("href"), "https://podcast.example.org/art/cover.jpg")
        self.assertTrue((pod.PUBLIC / "testshow" / "episodes" / "first-words" / "index.html").exists())
        self.assertTrue((pod.PUBLIC / "testshow" / "media").is_symlink())
        self.assertIn("preload=\"none\"", (pod.PUBLIC / "testshow" / "index.html").read_text())
        # a second episode gets the next number and a fresh guid
        pod.main(["new", "--show", "testshow", "--mp3", str(self.mp3), "--title", "Second - Ada"])
        ep2 = pod.SHOWS / "testshow" / "episodes" / "ep02-second.html"
        self.assertTrue(ep2.exists())
        self.assertNotEqual(pod.read_front_matter(ep2)[0]["guid"], fm["guid"])


if __name__ == "__main__":
    unittest.main()
