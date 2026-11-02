from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

from portfolio_common import (
    ROOT,
    escape,
    fallback_svg,
    replace_generated_block,
    request_bytes,
    slugify,
    write_json_if_changed,
    write_text_if_changed,
)

GENERATED_DIR = ROOT / "img" / "community" / "generated"
REQUIRED_FIELDS = ("Organisation", "Role", "Period", "Summary", "Impact or evidence link")


def issue_fields(body: str) -> dict[str, str]:
    sections = re.split(r"^###\s+", body, flags=re.MULTILINE)[1:]
    fields: dict[str, str] = {}
    for section in sections:
        heading, _, value = section.partition("\n")
        cleaned = value.strip()
        if cleaned == "_No response_":
            cleaned = ""
        fields[heading.strip()] = cleaned
    missing = [field for field in REQUIRED_FIELDS if not fields.get(field)]
    if missing:
        raise ValueError(f"Missing required community fields: {', '.join(missing)}")
    evidence = fields["Impact or evidence link"]
    if urlsplit(evidence).scheme not in {"http", "https"}:
        raise ValueError("Impact or evidence link must be an http(s) URL")
    return fields


def local_image(url: str, title: str) -> str:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{slugify(title)}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
    if url:
        if urlsplit(url).scheme not in {"http", "https"}:
            raise ValueError("Logo/image must be an http(s) URL")
        body, content_type = request_bytes(url)
        extension = {
            "image/webp": ".webp",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/svg+xml": ".svg",
        }.get(content_type)
        if not extension or len(body) > 2_000_000:
            raise ValueError("Logo/image must be PNG, JPEG, GIF, WebP or SVG and no larger than 2 MB")
        output = GENERATED_DIR / f"{stem}{extension}"
        output.write_bytes(body)
    else:
        output = GENERATED_DIR / f"{stem}.svg"
        write_text_if_changed(output, fallback_svg(title, "Community"))
    return output.relative_to(ROOT).as_posix()


def render(entry: dict[str, str]) -> str:
    evidence = ""
    if entry.get("evidence_url"):
        evidence_label = entry.get("evidence_label") or "View evidence"
        evidence = (
            f'\n          <a href="{escape(entry["evidence_url"])}" '
            f'target="_blank" rel="noopener noreferrer">{escape(evidence_label)} →</a>'
        )
    return f"""      <article class="community-card">
        <div class="community-mark"><img src="{escape(entry['image'])}" alt="{escape(entry['organisation'])} logo" loading="lazy" decoding="async"></div>
        <div>
          <div class="meta mono">{escape(entry['organisation'].upper())} · {escape(entry['period'].upper())}</div>
          <h3>{escape(entry['role'])}</h3>
          <p>{escape(entry['summary'])}</p>{evidence}
        </div>
      </article>"""


def main() -> None:
    fields = issue_fields(os.environ.get("COMMUNITY_ISSUE_BODY", ""))
    path = ROOT / "data" / "community.yml"
    document = json.loads(path.read_text(encoding="utf-8"))
    entries = document["entries"]
    entry_id = slugify(f"{fields['Organisation']}-{fields['Role']}-{fields['Period']}")
    if any(item["id"] == entry_id for item in entries):
        raise ValueError(f"Community entry already exists: {entry_id}")
    entries.append(
        {
            "id": entry_id,
            "organisation": fields["Organisation"],
            "role": fields["Role"],
            "period": fields["Period"],
            "summary": fields["Summary"],
            "evidence_url": fields["Impact or evidence link"],
            "image": local_image(fields.get("Logo or image URL", ""), fields["Organisation"]),
        }
    )
    write_json_if_changed(path, document)
    replace_generated_block(ROOT / "index.html", "COMMUNITY", "\n".join(render(item) for item in entries))


if __name__ == "__main__":
    main()
