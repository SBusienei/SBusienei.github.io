from __future__ import annotations

import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from portfolio_common import (
    ROOT,
    escape,
    fallback_svg,
    normalized_url,
    replace_generated_block,
    request_bytes,
    request_json,
    slugify,
    write_json_if_changed,
    write_text_if_changed,
)

DEV_URL = "https://dev.to/api/articles?username=sbusienei&per_page=100"
MEDIUM_URL = "https://medium.com/feed/@sbusienei"
GENERATED_DIR = ROOT / "img" / "articles" / "generated"
CONTENT_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"


def clean_text(value: str) -> str:
    plain = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", plain).strip()


def iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = parsedate_to_datetime(value)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def dev_articles() -> list[dict[str, object]]:
    records = []
    for item in request_json(DEV_URL):
        canonical = item.get("canonical_url") or item["url"]
        records.append(
            {
                "source": "DEV",
                "title": clean_text(item["title"]),
                "description": clean_text(item.get("description", "")),
                "url": item["url"],
                "canonical_url": canonical,
                "published_at": iso_date(item.get("published_timestamp", "")),
                "reading_time_minutes": int(item.get("reading_time_minutes") or 0),
                "cover_url": item.get("cover_image") or "",
            }
        )
    return records


def medium_articles() -> list[dict[str, object]]:
    body, _ = request_bytes(MEDIUM_URL, headers={"Accept": "application/rss+xml, application/xml"})
    root = ET.fromstring(body)
    records = []
    for item in root.findall("./channel/item"):
        title = clean_text(item.findtext("title", default=""))
        link = item.findtext("link", default="").strip()
        description = clean_text(item.findtext("description", default=""))
        content = item.findtext(CONTENT_TAG, default="")
        image_match = re.search(r'<img[^>]+src=["\']([^"\']+)', content, re.IGNORECASE)
        records.append(
            {
                "source": "MEDIUM",
                "title": title,
                "description": description[:280],
                "url": link,
                "canonical_url": link,
                "published_at": iso_date(item.findtext("pubDate", default="")),
                "reading_time_minutes": max(1, round(len(clean_text(content).split()) / 220)),
                "cover_url": html.unescape(image_match.group(1)) if image_match else "",
            }
        )
    return records


def deduplicate(records: list[dict[str, object]]) -> list[dict[str, object]]:
    selected: dict[str, dict[str, object]] = {}
    title_keys: dict[str, str] = {}
    for record in sorted(records, key=lambda item: str(item["published_at"]), reverse=True):
        canonical_key = normalized_url(str(record["canonical_url"]))
        title_key = re.sub(r"[^a-z0-9]+", "", str(record["title"]).lower())
        existing_key = canonical_key if canonical_key in selected else title_keys.get(title_key)
        if existing_key:
            existing = selected[existing_key]
            sources = sorted(set(existing.get("sources", [existing["source"]])) | {str(record["source"])})
            existing["sources"] = sources
            if existing["source"] != "DEV" and record["source"] == "DEV":
                record["sources"] = sources
                selected[existing_key] = record
            continue
        record["sources"] = [record["source"]]
        selected[canonical_key] = record
        title_keys[title_key] = canonical_key
    return sorted(selected.values(), key=lambda item: str(item["published_at"]), reverse=True)


def optimized_dev_image(url: str) -> str:
    if "media2.dev.to/dynamic/image/" not in url:
        return url
    encoded_origin = url.split("/https%3A", 1)
    if len(encoded_origin) != 2:
        return url
    return (
        "https://media2.dev.to/dynamic/image/"
        "width=600,height=252,fit=cover,gravity=auto,quality=70,format=webp/"
        "https%3A"
        + encoded_origin[1]
    )


def local_cover(record: dict[str, object]) -> str:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    key = normalized_url(str(record["canonical_url"]))
    stem = f"{slugify(str(record['title']))[:48]}-{hashlib.sha256(key.encode()).hexdigest()[:10]}"
    cover_url = str(record.get("cover_url") or "")
    if cover_url:
        try:
            body, content_type = request_bytes(optimized_dev_image(cover_url))
            extension = {
                "image/webp": ".webp",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/gif": ".gif",
            }.get(content_type)
            if extension and len(body) <= 2_000_000:
                output = GENERATED_DIR / f"{stem}{extension}"
                if not output.exists() or output.read_bytes() != body:
                    output.write_bytes(body)
                return output.relative_to(ROOT).as_posix()
        except RuntimeError as error:
            print(f"Cover download failed for {record['title']}: {error}", file=sys.stderr)
    output = GENERATED_DIR / f"{stem}.svg"
    write_text_if_changed(output, fallback_svg(str(record["title"]), "Writing"))
    return output.relative_to(ROOT).as_posix()


def render_card(record: dict[str, object]) -> str:
    published = datetime.fromisoformat(str(record["published_at"]).replace("Z", "+00:00"))
    meta = f"{record['source']} · {published.strftime('%b %Y').upper()} · {record['reading_time_minutes']} MIN"
    return f"""      <article class="article-card">
        <a class="article-image" href="{escape(record['url'])}" target="_blank" rel="noopener noreferrer">
          <img src="{escape(record['image'])}" alt="{escape(record['title'])} article cover" loading="lazy" decoding="async">
        </a>
        <div class="meta mono">{escape(meta)}</div>
        <h3><a href="{escape(record['url'])}" target="_blank" rel="noopener noreferrer">{escape(record['title'])}</a></h3>
        <p>{escape(record['description'])}</p>
      </article>"""


def main() -> None:
    allowlist = json.loads((ROOT / "data" / "featured-articles.json").read_text(encoding="utf-8"))["featured"]
    records = deduplicate(dev_articles() + medium_articles())
    by_url: dict[str, dict[str, object]] = {}
    for record in records:
        by_url[normalized_url(str(record["url"]))] = record
        by_url[normalized_url(str(record["canonical_url"]))] = record

    featured = []
    for configured in allowlist:
        configured_url = configured["url"] if isinstance(configured, dict) else configured
        record = by_url.get(normalized_url(configured_url))
        if record is None:
            raise ValueError(f"Featured article is missing from DEV/Medium feeds: {configured_url}")
        record = dict(record)
        if isinstance(configured, dict):
            record["title"] = configured.get("title") or record["title"]
            record["description"] = configured.get("description") or record["description"]
        record["image"] = local_cover(record)
        featured.append(record)

    retained_images = {Path(str(item["image"])).name for item in featured}
    for image in GENERATED_DIR.iterdir():
        if image.is_file() and image.name not in retained_images:
            image.unlink()

    stored_records = []
    for record in records:
        stored = {key: value for key, value in record.items() if key != "cover_url"}
        matched = next(
            (
                item
                for item in featured
                if normalized_url(str(item["canonical_url"])) == normalized_url(str(record["canonical_url"]))
            ),
            None,
        )
        if matched:
            stored["image"] = matched["image"]
        stored_records.append(stored)

    write_json_if_changed(
        ROOT / "data" / "articles.json",
        {
            "latest_published_at": max((str(item["published_at"]) for item in stored_records), default=""),
            "articles": stored_records,
        },
    )
    replace_generated_block(ROOT / "index.html", "ARTICLES", "\n".join(render_card(item) for item in featured))


if __name__ == "__main__":
    main()
