# Data Guide

InfraSentinel CV data is split into open-source raw sources, synthetic training/eval assets, and hand-curated real eval sets.

## Structure

- `raw/roboflow/`: optional exports from Roboflow Universe.
- `raw/textocr/`: optional TextOCR assets.
- `raw/open_images/`: optional background images (CC/Open Images).
- `synth/patchpanel_v1/`: generated synthetic patch-panel dataset.
- `real_eval/`: manually curated evaluation images + labels.

## Fastest Path (No External Downloads)

```bash
make synth
```

This creates synthetic images and labels under `data/synth/patchpanel_v1/`.

## Optional Data Downloads

- Roboflow: see `scripts/data/download_roboflow_universe.md`
- TextOCR helper: run `python scripts/data/download_textocr.py --help`
- Open Images prep: see `scripts/data/prepare_open_images.md`

## Labels Format

`labels.jsonl` entries typically include:

- `image`
- `port_label`
- `cable_tag` (optional)
- `bbox_label` (optional)
- `bbox_tag` (optional)
- `quality_flags`
