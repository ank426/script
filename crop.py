#!/usr/bin/env python3
"""Detect and remove uniform white margins from manga page scans."""

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


def _margin_left(img: NDArray[np.uint8], threshold: int) -> int:
    w = img.shape[1]
    for x in range(w):
        if img[:, x, :3].min() < threshold:
            return x
    return w


def _margin_right(img: NDArray[np.uint8], threshold: int) -> int:
    w = img.shape[1]
    for x in range(w - 1, -1, -1):
        if img[:, x, :3].min() < threshold:
            return w - 1 - x
    return w


def save_png(path: Path, img: NDArray[np.uint8]) -> None:
    bgra = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    cv2.imwrite(str(path), bgra)


def collect_image_paths(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix.lstrip(".").lower() in IMAGE_EXTENSIONS)


def load_image(path: Path) -> tuple[str, NDArray[np.uint8]]:
    stem = path.stem
    img = Image.open(path).convert("RGBA")
    return stem, np.asarray(img, dtype=np.uint8)


def crop_and_save(stem: str, img: NDArray[np.uint8], output: Path, min_left: int, min_right: int) -> None:
    w = img.shape[1]
    new_w = w - min_left - min_right

    cropped = img[:, min_left : min_left + new_w]
    save_png(output / f"{stem}.png", cropped)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="crop", description="Detect and remove uniform white margins from manga scans"
    )
    parser.add_argument("input", type=Path, help="Input directory containing images")
    parser.add_argument("output", type=Path, help="Output directory for cropped images")
    parser.add_argument(
        "--white-threshold", type=int, default=250, help="Pixels with all channels >= this value are considered white"
    )
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

    # Check aspect ratios
    h0, w0 = images[0][1].shape[:2]
    ar = w0 / h0
    for stem, img in images:
        h, w = img.shape[:2]
        this_ar = w / h
        if abs(this_ar - ar) > 0.01:
            print(
                f"error: aspect ratio mismatch — {images[0][0]} is {ar:.4f} but {stem} is {this_ar:.4f}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Find minimum white margins
    t = time.monotonic()
    wt = args.white_threshold
    with ThreadPoolExecutor() as pool:
        lefts = pool.map(lambda item: _margin_left(item[1], wt), images)
        min_left = min(lefts)
    with ThreadPoolExecutor() as pool:
        rights = pool.map(lambda item: _margin_right(item[1], wt), images)
        min_right = min(rights)
    elapsed = int((time.monotonic() - t) * 1000)
    print(f"margins: left={min_left}px, right={min_right}px ({elapsed}ms)", file=sys.stderr)

    # Crop and save each image in parallel
    t = time.monotonic()
    with ThreadPoolExecutor() as pool:
        futures = [pool.submit(crop_and_save, stem, img, args.output, min_left, min_right) for stem, img in images]
        for f in tqdm(futures, desc="cropping", ncols=80, file=sys.stderr):
            f.result()
    elapsed = int((time.monotonic() - t) * 1000)
    print(f"cropped {len(images)} images in {elapsed}ms", file=sys.stderr)


if __name__ == "__main__":
    main()
