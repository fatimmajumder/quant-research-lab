from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.platform import get_research_platform


def main() -> None:
    target = ROOT / "examples" / "platform_snapshot.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(get_research_platform(), indent=2))
    print({"output_path": str(target)})


if __name__ == "__main__":
    main()
