#!/usr/bin/env python3
"""Detect and split two-page manga spreads into individual pages."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2  # ty: ignore[unresolved-import]
import numpy as np
from numpy.typing import NDArray
from PIL import Image
from tqdm import tqdm

IMAGE_EXTENSIONS = frozenset(("png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif", "gif"))


def save_png(path: Path, img: NDArray[np.uint8]) -> None:
    bgra = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    cv2.imwrite(str(path), bgra)


def column_activity(img: NDArray[np.uint8], x: int) -> float:
    h = img.shape[0]
    if h <= 1:
        return 0.0
    col = img[:, x, :3].astype(np.int16)
    diffs = np.abs(col[1:] - col[:-1])
    return float(diffs.sum()) / ((h - 1) * 3.0 * 255.0)


def column_sad(col1: NDArray[np.int16], col2: NDArray[np.int16], shift: int) -> tuple[int, int]:
    h1 = col1.shape[0]
    h2 = col2.shape[0]
    y_start = max(0, -shift)
    y_end = min(h1, h2 - shift)
    if y_start >= y_end:
        return 0, 0
    s1 = col1[y_start:y_end]
    s2 = col2[y_start + shift : y_end + shift]
    sad = int(np.sum(np.abs(s1 - s2)))
    return sad, y_end - y_start


def split_ratio(img: NDArray[np.uint8], mid: int, band_r: int, win_r: int) -> tuple[float, float, float]:
    w = img.shape[1]
    h = img.shape[0]
    if mid < band_r + win_r or mid + band_r + win_r >= w or h == 0:
        return 1.0, 0.0, 0.0

    col_start = mid - band_r - win_r
    cols: list[NDArray[np.int16]] = [
        img[:, x, :3].astype(np.int16) for x in range(col_start, col_start + 2 * (band_r + win_r))
    ]

    self_sum = 0
    self_count = 0
    cross_sum = 0
    cross_count = 0

    for bx in range(2 * band_r):
        x = mid - band_r + bx
        is_left = x < mid
        ci = x - col_start

        for dx in range(-win_r, win_r + 1):
            nx = x + dx
            if nx < 0 or nx >= w:
                continue
            ni = nx - col_start
            neighbor_is_left = nx < mid
            is_self = neighbor_is_left == is_left

            for dy in range(-win_r, win_r + 1):
                if dx == 0 and dy == 0:
                    continue
                sad, count = column_sad(cols[ci], cols[ni], dy)
                if is_self:
                    self_sum += sad
                    self_count += count
                else:
                    cross_sum += sad
                    cross_count += count

    norm = 3.0 * 255.0
    avg_self = self_sum / (self_count * norm) if self_count > 0 else 0.0
    avg_cross = cross_sum / (cross_count * norm) if cross_count > 0 else 0.0

    ratio = (1.0 if avg_cross < 1e-6 else avg_cross / 1e-6) if avg_self < 1e-6 else avg_cross / avg_self

    return ratio, avg_self, avg_cross


def collect_image_paths(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lstrip(".").lower() in IMAGE_EXTENSIONS)


def load_image(path: Path) -> tuple[str, NDArray[np.uint8]]:
    stem = path.stem
    img = Image.open(path).convert("RGBA")
    return stem, np.asarray(img, dtype=np.uint8)


def process_image(
    stem: str, img: NDArray[np.uint8], output: Path, split_threshold: float, band_r: int, win_r: int, debug: bool
) -> None:
    w = img.shape[1]
    mid = w // 2

    if mid > band_r + win_r:
        ratio, self_diff, cross_diff = split_ratio(img, mid, band_r, win_r)
    else:
        ratio, self_diff, cross_diff = 1.0, 0.0, 0.0

    gutter_fallback = self_diff < 0.001 and cross_diff < 0.001
    if gutter_fallback:
        sample_dist = min(100, mid // 2)
        left_x = mid - sample_dist
        right_x = min(mid + sample_dist, w - 2)
        left_act = column_activity(img, left_x)
        right_act = column_activity(img, right_x)
        gutter_fallback = left_act > 0.01 or right_act > 0.01

    should_split = ratio > split_threshold or gutter_fallback

    if debug:
        reason = "gutter" if gutter_fallback else "ratio" if should_split else "no"
        print(f"{stem}: ratio={ratio:.4f} self={self_diff:.4f} cross={cross_diff:.4f} → {reason}", file=sys.stderr)

    if should_split:
        right_half = img[:, mid:]
        left_half = img[:, :mid]
        save_png(output / f"{stem}_a.png", right_half)
        save_png(output / f"{stem}_b.png", left_half)
    else:
        save_png(output / f"{stem}.png", img)


def main() -> None:
    parser = argparse.ArgumentParser(prog="kiru", description="Detect and split two-page manga spreads")
    parser.add_argument("input", type=Path, help="Input directory containing images")
    parser.add_argument("output", type=Path, help="Output directory for processed images")
    parser.add_argument(
        "--split-threshold", type=float, default=1.45, help="Split ratio threshold — above this the image is split"
    )
    parser.add_argument(
        "--band-radius", type=int, default=2, help="Number of columns on each side of midpoint to sample"
    )
    parser.add_argument(
        "--window-radius", type=int, default=2, help="Window radius for neighbor comparisons (window is (2W+1)x(2W+1))"
    )
    parser.add_argument("--debug", action="store_true", help="Print per-image debug info")
    args = parser.parse_args()

    if not args.input.is_dir():
        print("error: input path is not a directory", file=sys.stderr)
        sys.exit(1)

    input_canon = args.input.resolve()
    output_canon = args.output.resolve() if args.output.exists() else args.output
    if input_canon == output_canon:
        print("error: input and output directories must be different", file=sys.stderr)
        sys.exit(1)

    if args.output.exists():
        shutil.rmtree(args.output)
    args.output.mkdir(parents=True, exist_ok=True)

    paths = collect_image_paths(args.input)
    if not paths:
        print("no images found in input directory", file=sys.stderr)
        sys.exit(1)

    # Load all images in parallel
    t = time.monotonic()
    images: list[tuple[str, NDArray[np.uint8]]] = []
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(load_image, p) for p in paths]
        for f in tqdm(futures, desc="loading", ncols=80, file=sys.stderr):
            images.append(f.result())
    elapsed = int((time.monotonic() - t) * 1000)
    print(f"loaded {len(images)} images in {elapsed}ms", file=sys.stderr)

    # Process each image in parallel
    t = time.monotonic()
    with ThreadPoolExecutor() as pool:
        futures = [
            pool.submit(
                process_image,
                stem,
                img,
                args.output,
                args.split_threshold,
                args.band_radius,
                args.window_radius,
                args.debug,
            )
            for stem, img in images
        ]
        for f in tqdm(futures, desc="splitting", ncols=80, file=sys.stderr):
            f.result()
    elapsed = int((time.monotonic() - t) * 1000)
    print(f"processed {len(images)} images in {elapsed}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
