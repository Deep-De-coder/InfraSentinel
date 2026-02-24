from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic patch-panel dataset.")
    parser.add_argument("--out", default="data/synth/patchpanel_v1", help="Output dataset directory")
    parser.add_argument("--n", type=int, default=200, help="Number of samples")
    parser.add_argument("--ports", type=int, choices=[24, 48], default=24, help="Port count")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def _port_label_for(style: str, idx: int) -> str:
    if style == "numeric":
        return str(idx)
    if style == "alpha":
        bank = "A" if idx <= 24 else "B"
        offset = idx if idx <= 24 else idx - 24
        return f"{bank}{offset}"
    return f"P{idx:02d}"


def _random_cable_tag() -> str:
    return f"MDF-01-R{random.randint(1,20):02d}-P{random.randint(1,48):02d}"


def _apply_transforms(image: np.ndarray) -> tuple[np.ndarray, dict[str, bool]]:
    h, w = image.shape[:2]
    flags = {"blurred": False, "dark": False, "glare": False}

    angle = random.uniform(-4.0, 4.0)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    warped = cv2.warpAffine(image, m, (w, h), borderMode=cv2.BORDER_REPLICATE)

    if random.random() < 0.35:
        warped = cv2.GaussianBlur(warped, (5, 5), sigmaX=1.1)
        flags["blurred"] = True
    if random.random() < 0.35:
        warped = cv2.convertScaleAbs(warped, alpha=0.8, beta=-35)
        flags["dark"] = True
    if random.random() < 0.25:
        overlay = warped.copy()
        cx, cy = random.randint(60, w - 60), random.randint(40, h - 40)
        cv2.circle(overlay, (cx, cy), 28, (255, 255, 255), -1)
        warped = cv2.addWeighted(overlay, 0.2, warped, 0.8, 0)
        flags["glare"] = True
    return warped, flags


def main() -> None:
    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)

    out_dir = Path(args.out)
    img_dir = out_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    labels_path = out_dir / "labels.jsonl"
    meta_path = out_dir / "meta.json"

    font = ImageFont.load_default()
    entries: list[dict] = []
    styles = ["numeric", "alpha", "padded"]

    for i in range(args.n):
        width, height = 1280, 360
        canvas = Image.new("RGB", (width, height), color=(34, 34, 34))
        draw = ImageDraw.Draw(canvas)
        panel_rect = (60, 80, width - 60, height - 80)
        draw.rounded_rectangle(panel_rect, radius=10, fill=(56, 56, 56), outline=(120, 120, 120), width=3)

        ports = args.ports
        per_row = 24 if ports == 48 else ports
        rows = 2 if ports == 48 else 1
        style = random.choice(styles)
        chosen_port = random.randint(1, ports)
        port_text = _port_label_for(style, chosen_port)
        cable_tag = _random_cable_tag() if random.random() < 0.8 else None

        x0, y0 = 120, 135
        x_gap = 42 if per_row == 24 else 24
        y_gap = 64
        label_bbox = None

        for p in range(1, ports + 1):
            row = 0 if p <= per_row else 1
            col = (p - 1) if row == 0 else (p - 1 - per_row)
            x = x0 + col * x_gap
            y = y0 + row * y_gap
            draw.rectangle((x, y, x + 20, y + 20), fill=(180, 180, 190), outline=(20, 20, 20), width=1)
            label = _port_label_for(style, p)
            draw.text((x - 1, y + 26), label, fill=(220, 220, 220), font=font)
            if p == chosen_port:
                label_bbox = [x - 2, y + 24, 30, 14]

        tag_bbox = None
        if cable_tag:
            tx, ty = random.randint(180, width - 380), random.randint(38, 72)
            draw.rounded_rectangle((tx - 6, ty - 3, tx + 230, ty + 15), radius=3, fill=(228, 228, 228))
            draw.text((tx, ty), cable_tag, fill=(32, 32, 32), font=font)
            tag_bbox = [tx - 6, ty - 3, 236, 20]

        arr = cv2.cvtColor(np.array(canvas), cv2.COLOR_RGB2BGR)
        arr, quality_flags = _apply_transforms(arr)

        filename = f"panel_{i:05d}.png"
        cv2.imwrite(str(img_dir / filename), arr)
        entries.append(
            {
                "image": f"images/{filename}",
                "port_label": port_text,
                "cable_tag": cable_tag,
                "bbox_label": label_bbox,
                "bbox_tag": tag_bbox,
                "quality_flags": quality_flags,
                "ports": ports,
                "style": style,
            }
        )

    with labels_path.open("w", encoding="utf-8") as f:
        for item in entries:
            f.write(json.dumps(item) + "\n")

    meta = {
        "name": "patchpanel_v1",
        "count": len(entries),
        "ports": args.ports,
        "seed": args.seed,
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Generated {len(entries)} samples at {out_dir}")


if __name__ == "__main__":
    main()
