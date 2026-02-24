# Prepare Open Images Backgrounds

Open Images backgrounds are optional and used for synthetic augmentation.

## Steps

1. Download CC-licensed images from Open Images or equivalent sources.
2. Resize/crop as needed for synthetic backgrounds.
3. Place assets under:

```text
data/raw/open_images/
```

4. Keep attribution and source metadata with each batch.

## Notes

- The synthetic generator in this scaffold works without background images.
- If backgrounds exist, future generator versions can blend patch-panel renders into those scenes.
