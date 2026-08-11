#!/usr/bin/env python3
"""Prepare rig images for COLMAP (https://colmap.github.io/rigs.html)

- Rotates every image 180 degrees (fix for upside-down mounted cameras).
  Resolution, file type (JPEG), EXIF, ICC profile, quantization tables and
  chroma subsampling are preserved; nothing else is altered.
- Regroups images into camera1/ ... camera4/ folders based on the
  rgb_<N>_ filename prefix.
- Renames images to image0001.jpeg, image0002.jpeg, ... ordered by
  timestamp, with identical filenames across cameras for the same frame
  (frames are matched by their identical timestamp suffix).

Originals are left untouched; output goes to a new "images/" directory.
A frame_mapping.txt (frame name -> original timestamp) and a
rig_config.json template are written next to it.
"""

import json
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image
from PIL.JpegImagePlugin import JpegImageFile, get_sampling

SRC_DIR = Path("/home/dkhuttan/dataset/wrp_roof/before_solar_panels/wrp_roof_10Jul2026_rgbs")
OUT_DIR = SRC_DIR.parent / "wrp_roof_10Jul2026_rgbs_colmap" / "images"
NUM_CAMERAS = 4
NAME_RE = re.compile(r"^rgb_([1-4])_(\d+\.\d+)\.(jpe?g)$", re.IGNORECASE)


def collect_frames():
    """Group source images by timestamp -> {camera_id: path}"""
    frames = {}
    for path in SRC_DIR.iterdir():
        m = NAME_RE.match(path.name)
        if not m:
            sys.exit(f"Unexpected filename, refusing to continue: {path.name}")
        cam, ts = int(m.group(1)), m.group(2)
        if cam in frames.setdefault(ts, {}):
            sys.exit(f"Duplicate image for camera {cam} at timestamp {ts}")
        frames[ts][cam] = path
    incomplete = {ts: c for ts, c in frames.items() if len(c) != NUM_CAMERAS}
    if incomplete:
        sys.exit(f"{len(incomplete)} timestamps are missing cameras, e.g.: "
                 f"{list(incomplete)[:5]}")
    return frames


def flip_one(job):
    src, dst = job
    with Image.open(src) as im:
        if not isinstance(im, JpegImageFile):
            sys.exit(f"Not a JPEG: {src}")
        exif = im.info.get("exif")
        icc = im.info.get("icc_profile")
        qtables = getattr(im, "quantization", None)
        sampling = get_sampling(im)
        flipped = im.transpose(Image.Transpose.ROTATE_180)
    save_kwargs = {"format": "JPEG"}
    if qtables:
        save_kwargs["qtables"] = qtables
    else:
        save_kwargs["quality"] = 95
    if sampling >= 0:
        save_kwargs["subsampling"] = sampling
    if exif:
        save_kwargs["exif"] = exif
    if icc:
        save_kwargs["icc_profile"] = icc
    flipped.save(dst, **save_kwargs)


def main():
    frames = collect_frames()
    timestamps = sorted(frames, key=lambda ts: tuple(map(int, ts.split("."))))
    pad = max(4, len(str(len(timestamps))))

    for cam in range(1, NUM_CAMERAS + 1):
        (OUT_DIR / f"camera{cam}").mkdir(parents=True, exist_ok=True)

    jobs, mapping = [], []
    for idx, ts in enumerate(timestamps, start=1):
        name = f"image{idx:0{pad}d}.jpeg"
        mapping.append(f"{name}\t{ts}")
        for cam, src in frames[ts].items():
            jobs.append((src, OUT_DIR / f"camera{cam}" / name))

    print(f"{len(timestamps)} frames x {NUM_CAMERAS} cameras = {len(jobs)} images")
    done = 0
    with ProcessPoolExecutor() as pool:
        for _ in pool.map(flip_one, jobs, chunksize=32):
            done += 1
            if done % 500 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}")

    (OUT_DIR.parent / "frame_mapping.txt").write_text("\n".join(mapping) + "\n")

    rig_config = [{
        "cameras": [
            {"image_prefix": f"camera{cam}/", **({"ref_sensor": True} if cam == 1 else {})}
            for cam in range(1, NUM_CAMERAS + 1)
        ]
    }]
    (OUT_DIR.parent / "rig_config.json").write_text(json.dumps(rig_config, indent=4) + "\n")
    print(f"Done. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
