from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from portfolio_common import ROOT, normalized_url


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "a":
            self.links.append(values)
        if tag in {"img", "script"} and values.get("src"):
            self.assets.append(values["src"])
        if tag == "link" and values.get("href"):
            self.assets.append(values["href"])


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_markers(source: str) -> None:
    for name in ("ARTICLES", "PROJECTS", "COMMUNITY"):
        start = f"<!-- AUTO-{name}:START -->"
        end = f"<!-- AUTO-{name}:END -->"
        if source.count(start) != 1 or source.count(end) != 1 or source.index(start) > source.index(end):
            fail(f"Invalid generated block markers for {name}")


def validate_data(source: str) -> None:
    featured = json.loads((ROOT / "data" / "featured-articles.json").read_text(encoding="utf-8"))["featured"]
    articles = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))["articles"]
    article_urls = {
        normalized_url(str(item["url"])) for item in articles
    } | {
        normalized_url(str(item["canonical_url"])) for item in articles
    }
    featured_urls = [item["url"] if isinstance(item, dict) else item for item in featured]
    missing = [url for url in featured_urls if normalized_url(url) not in article_urls]
    if missing:
        fail(f"Featured articles missing from synchronized data: {missing}")
    article_block = source.split("<!-- AUTO-ARTICLES:START -->", 1)[1].split("<!-- AUTO-ARTICLES:END -->", 1)[0]
    if article_block.count('class="article-card"') != len(featured):
        fail("Featured article card count does not match allowlist")

    projects = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))["projects"]
    repository_names = [item["repo"] for item in projects]
    if len(repository_names) != len(set(repository_names)):
        fail("Duplicate project repository entries")

    community = json.loads((ROOT / "data" / "community.yml").read_text(encoding="utf-8"))["entries"]
    entry_ids = [item["id"] for item in community]
    if len(entry_ids) != len(set(entry_ids)):
        fail("Duplicate community entry IDs")


def validate_html(source: str) -> None:
    parser = SiteParser()
    parser.feed(source)
    for asset in parser.assets:
        if urlsplit(asset).scheme or asset.startswith("//"):
            continue
        asset_path = ROOT / asset.split("?", 1)[0].split("#", 1)[0]
        if not asset_path.is_file():
            fail(f"Missing local asset: {asset}")

    generated_ranges = []
    for name in ("ARTICLES", "PROJECTS", "COMMUNITY"):
        generated_ranges.append(
            source.split(f"<!-- AUTO-{name}:START -->", 1)[1].split(f"<!-- AUTO-{name}:END -->", 1)[0]
        )
    generated_html = "\n".join(generated_ranges)
    generated_parser = SiteParser()
    generated_parser.feed(generated_html)
    for link in generated_parser.links:
        href = link.get("href", "")
        if href.startswith(("http://", "https://")):
            rel = set(link.get("rel", "").split())
            if link.get("target") != "_blank" or not {"noopener", "noreferrer"}.issubset(rel):
                fail(f"Generated external link lacks safe new-tab attributes: {href}")

    if '<button class="menu-btn"' not in source or source.count("<span aria-hidden=\"true\"></span>") < 3:
        fail("Responsive three-line menu markup is missing")
    style = (ROOT / "style.css").read_text(encoding="utf-8")
    if "nav.open .links" not in style or "align-items:flex-start" not in style:
        fail("Left-aligned responsive navigation styles are missing")
    script = (ROOT / "site.js").read_text(encoding="utf-8")
    if 'link.target = "_blank"' not in script or 'link.rel = "noopener noreferrer"' not in script:
        fail("External-link new-tab protection is missing")
    if not re.search(r"CLOUDFLARE-ANALYTICS.*site\.js", source, re.DOTALL):
        fail("Cloudflare Analytics insertion point is missing")


def main() -> None:
    if (ROOT / "learn.html").exists() or (ROOT / "learn.js").exists():
        fail("Private lab files must not be published")
    source = (ROOT / "index.html").read_text(encoding="utf-8")
    validate_markers(source)
    validate_data(source)
    validate_html(source)
    print("Portfolio validation passed")


if __name__ == "__main__":
    main()
