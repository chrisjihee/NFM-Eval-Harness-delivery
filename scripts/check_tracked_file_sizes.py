#!/usr/bin/env python3
"""Fail if any git-tracked file exceeds a size threshold.

Delivery guard: the INL bundle must not ship model weights, caches, or large
raw artifacts. This checks only *tracked* files (what would actually be
delivered), not the working tree.

Usage:
    python scripts/check_tracked_file_sizes.py --max-mb 50

Exit codes:
    0  all tracked files are within the limit
    1  one or more tracked files exceed the limit
    2  not a git repository / git error
"""
import argparse
import os
import subprocess
import sys


def tracked_files():
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            check=True, capture_output=True, text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"error: cannot list tracked files: {exc}", file=sys.stderr)
        sys.exit(2)
    return [p for p in out.split("\0") if p]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-mb", type=float, default=50.0,
                    help="maximum allowed tracked-file size in MB (default 50)")
    args = ap.parse_args()
    limit = args.max_mb * 1024 * 1024

    offenders = []
    for path in tracked_files():
        try:
            size = os.path.getsize(path)
        except OSError:
            continue  # tracked but missing locally; nothing to ship
        if size > limit:
            offenders.append((size, path))

    if offenders:
        print(f"FAIL: {len(offenders)} tracked file(s) exceed {args.max_mb} MB:")
        for size, path in sorted(offenders, reverse=True):
            print(f"  {size / 1024 / 1024:7.1f} MB  {path}")
        sys.exit(1)
    print(f"OK: no tracked file exceeds {args.max_mb} MB.")


if __name__ == "__main__":
    main()
