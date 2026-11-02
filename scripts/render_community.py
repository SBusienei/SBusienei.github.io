from __future__ import annotations

import json

from community_issue import render
from portfolio_common import ROOT, replace_generated_block


def main() -> None:
    document = json.loads((ROOT / "data" / "community.yml").read_text(encoding="utf-8"))
    replace_generated_block(
        ROOT / "index.html",
        "COMMUNITY",
        "\n".join(render(entry) for entry in document["entries"]),
    )


if __name__ == "__main__":
    main()
