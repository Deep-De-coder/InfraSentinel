from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TextOCR dataset download helper.")
    parser.add_argument("--out", default="data/raw/textocr", help="Output directory path")
    parser.add_argument(
        "--url",
        default="",
        help="Optional direct URL to a TextOCR archive (zip/tar). If omitted, instructions are printed.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.url:
        print("TextOCR helper: no URL provided.")
        print("Recommended steps:")
        print("1) Review official TextOCR release page and licensing")
        print("2) Download image and annotation archives manually")
        print(f"3) Place files under: {out_dir.resolve()}")
        print("4) Keep original archives for provenance")
        return

    parsed = urlparse(args.url)
    if parsed.scheme not in {"http", "https"}:
        print("Invalid URL. Only http/https are supported.")
        return

    filename = Path(parsed.path).name or "textocr_download.bin"
    target = out_dir / filename
    print(f"Downloading {args.url} -> {target}")
    urlretrieve(args.url, target)  # noqa: S310
    print("Download complete.")


if __name__ == "__main__":
    main()
