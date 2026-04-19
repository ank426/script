#!/usr/bin/env python3
"""Drop-in zip replacement with parallel compression.

Usage: zip.py [-j] output.zip path [path ...]

Recursive by default. -j junks (strips) directory paths.
"""

import argparse
import os
import struct
import sys
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import BinaryIO


def human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            return f"{size:.1f}{unit}" if unit != "B" else f"{int(size)}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


class ZipWriter:
    """Writes zip files from pre-compressed deflate data."""

    def __init__(self, f: BinaryIO) -> None:
        self._f = f
        self._entries: list[tuple[bytes, int]] = []  # (cd_entry, offset)

    def add(self, name: str, raw: bytes, orig_size: int, crc: int) -> None:
        name_bytes = name.encode("utf-8")
        offset = self._f.tell()
        header = struct.pack(
            "<4sHHHHHIIIHH",
            b"PK\x03\x04",
            20,
            1 << 11,  # UTF-8 flag
            8,  # deflate
            0,
            0,  # mod time/date
            crc,
            len(raw),
            orig_size,
            len(name_bytes),
            0,
        )
        self._f.write(header + name_bytes + raw)
        cd_entry = struct.pack(
            "<4sHHHHHHIIIHHHHHII",
            b"PK\x01\x02",
            20,
            20,
            1 << 11,
            8,
            0,
            0,
            crc,
            len(raw),
            orig_size,
            len(name_bytes),
            0,
            0,
            0,
            0,
            0,
            offset,
        )
        self._entries.append((cd_entry + name_bytes, offset))

    def close(self) -> None:
        cd_offset = self._f.tell()
        cd_data = b"".join(e for e, _ in self._entries)
        self._f.write(cd_data)
        self._f.write(
            struct.pack(
                "<4sHHHHIIH", b"PK\x05\x06", 0, 0, len(self._entries), len(self._entries), len(cd_data), cd_offset, 0
            )
        )


def collect_files(paths: list[str]) -> list[Path]:
    files = []
    for p in paths:
        path = Path(p)
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    files.append(f)
    return files


def compress_one(filepath: Path, junk: bool) -> tuple[str, int, bytes, int]:
    data = filepath.read_bytes()
    crc = zlib.crc32(data) & 0xFFFFFFFF
    obj = zlib.compressobj(6, zlib.DEFLATED, -15)  # raw deflate, no zlib wrapper
    raw = obj.compress(data) + obj.flush()
    arcname = filepath.name if junk else str(filepath)
    return arcname, len(data), raw, crc


def main() -> None:
    parser = argparse.ArgumentParser(description="Parallel zip")
    parser.add_argument("-j", action="store_true", help="junk (strip) directory paths")
    parser.add_argument("zipfile", help="output zip file")
    parser.add_argument("paths", nargs="+", help="files/directories to zip")
    args = parser.parse_args()

    files = collect_files(args.paths)
    if not files:
        print("zip.py: no files to add", file=sys.stderr)
        sys.exit(1)

    total = len(files)
    total_bytes = sum(f.stat().st_size for f in files)
    workers = min(os.cpu_count() or 4, total)
    compressed_bytes = 0
    lock = threading.Lock()

    def compress_and_track(filepath: Path) -> tuple[str, int, bytes, int]:
        nonlocal compressed_bytes
        result = compress_one(filepath, args.j)
        with lock:
            compressed_bytes += result[1]
            pct = compressed_bytes * 100 // total_bytes if total_bytes else 100
            elapsed = time.monotonic() - t0
            done = human_size(compressed_bytes)
            tot = human_size(total_bytes)
            print(f"\r  compressing: {pct:3d}% ({done}/{tot}) [{elapsed:.1f}s]", end="", flush=True)
        return result

    print(f"  {total} files, {human_size(total_bytes)}, {workers} threads")

    t0 = time.monotonic()
    results: list[tuple[str, int, bytes, int]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(compress_and_track, f) for f in files]
        for future in as_completed(futures):
            results.append(future.result())
    compress_time = time.monotonic() - t0
    print()

    written_bytes = 0
    write_total = sum(len(raw) for _, _, raw, _ in results)
    t1 = time.monotonic()
    with open(args.zipfile, "wb") as f:
        writer = ZipWriter(f)
        for arcname, orig_size, raw, crc in results:
            writer.add(arcname, raw, orig_size, crc)
            written_bytes += len(raw)
            pct = written_bytes * 100 // write_total if write_total else 100
            elapsed = time.monotonic() - t1
            done = human_size(written_bytes)
            tot = human_size(write_total)
            print(f"\r  writing:     {pct:3d}% ({done}/{tot}) [{elapsed:.1f}s]", end="", flush=True)
        writer.close()
    write_time = time.monotonic() - t1
    print()
    print(f"  done: compress {compress_time:.1f}s, write {write_time:.1f}s, total {compress_time + write_time:.1f}s")


if __name__ == "__main__":
    main()
