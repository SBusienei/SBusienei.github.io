from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

OWNER = "SBusienei"
REPOSITORY = "SBusienei.github.io"


def api(method: str, path: str, payload: dict[str, object] | None = None) -> object:
    token = os.environ["GITHUB_TOKEN"]
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.github.com/repos/{OWNER}/{REPOSITORY}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SBusienei-portfolio-automation/1.0",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8")) if response.length != 0 else {}


def main() -> None:
    workflow = os.environ.get("WORKFLOW_NAME", "Portfolio automation")
    run_url = os.environ.get("RUN_URL", "")
    title = f"[Automation failure] {workflow}"
    body = f"The latest **{workflow}** run failed.\n\n[Open the workflow run]({run_url})"
    try:
        api("POST", "/labels", {"name": "automation-failure", "color": "b60205", "description": "Portfolio automation needs attention"})
    except urllib.error.HTTPError as error:
        if error.code != 422:
            raise
    issues = api("GET", f"/issues?state=open&labels=automation-failure&per_page=100")
    existing = next((issue for issue in issues if issue["title"] == title and "pull_request" not in issue), None)
    if existing:
        api("POST", f"/issues/{existing['number']}/comments", {"body": body})
    else:
        api("POST", "/issues", {"title": title, "body": body, "labels": ["automation-failure"], "assignees": [OWNER]})


if __name__ == "__main__":
    main()
