from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "SBusienei-portfolio-automation/1.0"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text_if_changed(path: Path, content: str) -> bool:
    content = content.rstrip() + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


def write_json_if_changed(path: Path, value: Any) -> bool:
    return write_text_if_changed(path, json.dumps(value, indent=2, ensure_ascii=False))


def request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    attempts: int = 3,
    timeout: int = 20,
) -> tuple[bytes, str]:
    request_headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if headers:
        request_headers.update(headers)
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers=request_headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), response.headers.get_content_type()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(2**attempt)
    raise RuntimeError(f"Failed to fetch {url} after {attempts} attempts: {last_error}")


def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    attempts: int = 3,
    timeout: int = 20,
) -> Any:
    body, _ = request_bytes(url, headers=headers, attempts=attempts, timeout=timeout)
    return json.loads(body.decode("utf-8"))


def normalized_url(url: str) -> str:
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72] or hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def replace_generated_block(path: Path, name: str, rendered: str) -> bool:
    start = f"<!-- AUTO-{name}:START -->"
    end = f"<!-- AUTO-{name}:END -->"
    source = path.read_text(encoding="utf-8")
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError(f"{path} must contain exactly one {start} and {end} marker")
    before, remainder = source.split(start, 1)
    _, after = remainder.split(end, 1)
    replacement = f"{start}\n{rendered.rstrip()}\n      {end}"
    return write_text_if_changed(path, before + replacement + after)


def fallback_svg(title: str, subtitle: str = "Portfolio") -> str:
    digest = hashlib.sha256(title.encode("utf-8")).hexdigest()
    hue = int(digest[:4], 16) % 360
    initial = next((character.upper() for character in title if character.isalnum()), "P")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 420" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="hsl({hue} 45% 18%)"/>
      <stop offset="1" stop-color="hsl({(hue + 45) % 360} 45% 9%)"/>
    </linearGradient>
  </defs>
  <rect width="1000" height="420" rx="24" fill="url(#g)"/>
  <circle cx="820" cy="80" r="170" fill="none" stroke="#7ee0b5" stroke-opacity=".35" stroke-width="3"/>
  <circle cx="860" cy="340" r="120" fill="none" stroke="#7ee0b5" stroke-opacity=".2" stroke-width="3"/>
  <text x="70" y="238" fill="#f6f3ea" font-family="Arial, sans-serif" font-size="150" font-weight="700">{initial}</text>
  <text x="70" y="322" fill="#a9b9d6" font-family="Arial, sans-serif" font-size="34">{escape(subtitle)}</text>
</svg>"""
