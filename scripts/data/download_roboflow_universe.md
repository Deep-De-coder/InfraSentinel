# Download Roboflow Universe Data

This project does not hardcode Roboflow API keys. Use manual export or your own API token.

## Manual (Recommended)

1. Open Roboflow Universe and select a patch-panel / cable-label dataset.
2. Export in a preferred format (COCO, YOLOv8, etc.).
3. Unzip into `data/raw/roboflow/<dataset_name>/`.

## Optional CLI/API

If using Roboflow Python SDK:

```bash
pip install roboflow
```

Then use your own key in environment:

```bash
set ROBOFLOW_API_KEY=...
python your_download_script.py
```

Keep raw exports unmodified for provenance. Add conversion scripts separately under `scripts/data/` as needed.
