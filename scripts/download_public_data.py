from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data import download_public_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Download a public research dataset for Quant Research Lab.")
    parser.add_argument("--dataset", required=True, help="Dataset id from the public dataset registry.")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "data"),
        help="Directory where the normalized CSV should be written.",
    )
    args = parser.parse_args()

    payload = download_public_dataset(args.dataset, args.output_dir)
    print(payload)


if __name__ == "__main__":
    main()
