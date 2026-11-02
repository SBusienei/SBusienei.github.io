from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from portfolio_common import (
    ROOT,
    escape,
    fallback_svg,
    replace_generated_block,
    request_json,
    slugify,
    write_json_if_changed,
    write_text_if_changed,
)

OWNER = "SBusienei"
EXCLUDED_REPOSITORIES = {"05-jobs-extractor"}
GENERATED_DIR = ROOT / "img" / "projects" / "generated"


def github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def repositories() -> list[dict[str, Any]]:
    selected = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{OWNER}/repos?type=owner&sort=updated&per_page=100&page={page}"
        batch = request_json(url, headers=github_headers())
        for repository in batch:
            if (
                "portfolio" in (repository.get("topics") or [])
                and not repository["private"]
                and not repository["fork"]
                and not repository["archived"]
                and repository["name"] not in EXCLUDED_REPOSITORIES
            ):
                selected.append(repository)
        if len(batch) < 100:
            break
        page += 1
    return selected


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        return [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    return value.strip("'\"")


def parse_portfolio_yaml(source: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current_list = ""
    for raw_line in source.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_list:
            result.setdefault(current_list, []).append(parse_scalar(line.lstrip()[2:]))
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported portfolio.yml line: {raw_line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            result[key] = parse_scalar(value)
            current_list = ""
        else:
            result[key] = []
            current_list = key
    return result


def repository_metadata(repository: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{OWNER}/{repository['name']}/contents/portfolio.yml"
    try:
        response = request_json(url, headers=github_headers(), attempts=2)
    except RuntimeError as error:
        if "HTTP Error 404" in str(error):
            return {}
        raise
    return parse_portfolio_yaml(base64.b64decode(response["content"]).decode("utf-8"))


def generated_art(repository: str, title: str) -> str:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    output = GENERATED_DIR / f"{slugify(repository)}.svg"
    write_text_if_changed(output, fallback_svg(title, "Open-source project"))
    return output.relative_to(ROOT).as_posix()


def project_record(
    repository: dict[str, Any],
    metadata: dict[str, Any],
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    existing = existing or {}
    title = metadata.get("title") or existing.get("title") or repository["name"].replace("-", " ").title()
    summary = metadata.get("summary") or existing.get("summary") or repository.get("description")
    if not summary:
        raise ValueError(f"{repository['name']} needs a repository description or portfolio.yml summary")
    technologies = metadata.get("technologies") or existing.get("technologies") or []
    if not technologies and repository.get("language"):
        technologies = [repository["language"]]
    tags = metadata.get("tags") or existing.get("tags") or ["mle"]
    return {
        "repo": repository["name"],
        "title": title,
        "summary": summary,
        "shows": metadata.get("shows") or existing.get("shows") or "end-to-end implementation and delivery.",
        "tags": tags,
        "technologies": technologies,
        "code_url": metadata.get("code_url") or repository["html_url"],
        "live_url": metadata.get("live_url") or existing.get("live_url") or repository.get("homepage") or "",
        "image": metadata.get("image") or existing.get("image") or generated_art(repository["name"], title),
        "image_alt": metadata.get("image_alt") or existing.get("image_alt") or f"{title} project artwork",
    }


def render(project: dict[str, Any]) -> str:
    stack = "".join(f"<span>{escape(item)}</span>" for item in project["technologies"])
    live = (
        f'<a href="{escape(project["live_url"])}" target="_blank" rel="noopener noreferrer">Live app</a>'
        if project.get("live_url")
        else ""
    )
    return f"""      <article class="card" data-tags="{escape(' '.join(project['tags']))}">
        <img class="thumb" src="{escape(project['image'])}" alt="{escape(project['image_alt'])}" loading="lazy" decoding="async">
        <h3>{escape(project['title'])}</h3>
        <p>{escape(project['summary'])}</p>
        <p class="why"><b>Shows:</b> {escape(project['shows'])}</p>
        <div class="stack">{stack}</div>
        <div class="row"><a href="{escape(project['code_url'])}" target="_blank" rel="noopener noreferrer">Code</a>{live}</div>
      </article>"""


def main() -> None:
    current = json.loads((ROOT / "data" / "projects.json").read_text(encoding="utf-8"))["projects"]
    existing = {item["repo"]: item for item in current}
    discovered = repositories()
    records = [
        project_record(repository, repository_metadata(repository), existing.get(repository["name"]))
        for repository in discovered
    ]
    order = {item["repo"]: index for index, item in enumerate(current)}
    records.sort(key=lambda item: (order.get(item["repo"], 10_000), item["title"].lower()))
    write_json_if_changed(ROOT / "data" / "projects.json", {"projects": records})
    replace_generated_block(ROOT / "index.html", "PROJECTS", "\n".join(render(item) for item in records))


if __name__ == "__main__":
    main()
