#!/usr/bin/env python3
"""
Simple image renamer: rename image files in a folder to a numeric sequence.

Usage examples:
    python rename_images.py --dir "C:/path/to/images" --prefix IMG --start 1 --padding 3

Key features:
- Filters by extensions (default: jpg,jpeg,png,gif,webp,bmp)
- Natural sorting (by filename) or by mtime
- Dry-run mode
- Collision-safe renaming: will append _1, _2 if target exists
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import csv
from typing import List, Iterable


def natural_key(s: str):
    # Split by digits so that file2 < file10.
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def find_images(directory: str, exts: List[str], sort_by: str = "name") -> List[str]:
    entries = []
    for name in os.listdir(directory):
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        low = name.lower()
        for e in exts:
            if low.endswith(e):
                entries.append(name)
                break

    if sort_by == "mtime":
        entries.sort(key=lambda n: os.path.getmtime(os.path.join(directory, n)))
    else:
        entries.sort(key=natural_key)

    return entries


def next_free_name(directory: str, candidate: str) -> str:
    base, ext = os.path.splitext(candidate)
    path = os.path.join(directory, candidate)
    if not os.path.exists(path):
        return candidate
    i = 1
    while True:
        newname = f"{base}_{i}{ext}"
        if not os.path.exists(os.path.join(directory, newname)):
            return newname
        i += 1


def rename_sequence(
    directory: str,
    prefix: str,
    start: int,
    padding: int,
    exts: List[str],
    dry_run: bool,
    sort_by: str,
    separator: str,
    pattern: str | None = None,
    map_csv: str | None = None,
) -> List[tuple[str, str]]:
    files = find_images(directory, exts, sort_by)
    results: List[tuple[str, str]] = []
    n = start
    for fname in files:
        _, ext = os.path.splitext(fname)
        number = str(n).zfill(padding)
        # If a pattern is provided it takes precedence. The pattern is a
        # Python-format string that receives `n` as an integer, so the user
        # can express zero-padding like `{n:03d}`.
        if pattern:
            try:
                rendered = pattern.format(n=n)
            except Exception as e:
                # Fall back to simple numbering on format failure
                rendered = f"{prefix}{separator}{number}" if prefix else number
            # If the rendered pattern already contains an extension, keep it;
            # otherwise append the original file extension.
            base_part, pat_ext = os.path.splitext(rendered)
            if pat_ext:
                newname = rendered
            else:
                newname = rendered + ext
        else:
            newbase = f"{prefix}{separator}{number}" if prefix else number
            newname = newbase + ext
        newname = next_free_name(directory, newname)
        src = os.path.join(directory, fname)
        dst = os.path.join(directory, newname)
        results.append((src, dst))
        n += 1

    # perform renames
    for src, dst in results:
        if dry_run:
            print(f"DRY-RUN: {os.path.basename(src)} -> {os.path.basename(dst)}")
        else:
            print(f"Renaming: {os.path.basename(src)} -> {os.path.basename(dst)}")
            os.rename(src, dst)

    # export mapping CSV if requested (columns: name_raw, name_change)
    if map_csv:
        try:
            with open(map_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["name_raw", "name_change"])
                for src, dst in results:
                    writer.writerow([os.path.basename(src), os.path.basename(dst)])
            print(f"Mapping written to: {map_csv}")
        except Exception as e:
            print(f"Warning: failed to write mapping file {map_csv}: {e}")

    return results


def apply_csv_mapping(directory: str, csv_path: str, dry_run: bool) -> List[tuple[str, str]]:
    """Apply explicit mapping from a CSV file with headers `name_raw,name_change`.

    - `name_raw` must match the basename of an existing file in `directory`.
    - `name_change` is the desired new basename. If it lacks an extension the
      source file's extension is preserved.
    - Collisions are resolved by appending _1/_2 etc. to the desired name.
    Returns a list of (src_path, dst_path) tuples for actions taken (or planned).
    """
    actions: List[tuple[str, str]] = []
    if not os.path.isfile(csv_path):
        print(f"Mapping CSV not found: {csv_path}")
        return actions

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if 'name_raw' not in reader.fieldnames or 'name_change' not in reader.fieldnames:
            print("CSV must contain headers: name_raw,name_change")
            return actions
        for row in reader:
            raw = (row.get('name_raw') or '').strip()
            want = (row.get('name_change') or '').strip()
            if not raw or not want:
                print(f"Skipping invalid row: {row}")
                continue
            src = os.path.join(directory, raw)
            if not os.path.exists(src):
                # Try case-insensitive match as a convenience
                found = None
                for name in os.listdir(directory):
                    if name.lower() == raw.lower():
                        found = os.path.join(directory, name)
                        break
                if found:
                    src = found
                else:
                    print(f"Source not found for mapping: {raw}")
                    continue

            # Ensure desired name has an extension; if not, keep source ext
            base, ext = os.path.splitext(want)
            if not ext:
                _, src_ext = os.path.splitext(src)
                dst_name = base + src_ext
            else:
                dst_name = want

            dst_name = next_free_name(directory, dst_name)
            dst = os.path.join(directory, dst_name)
            actions.append((src, dst))

    for src, dst in actions:
        if dry_run:
            print(f"DRY-RUN: {os.path.basename(src)} -> {os.path.basename(dst)}")
        else:
            print(f"Renaming: {os.path.basename(src)} -> {os.path.basename(dst)}")
            try:
                os.rename(src, dst)
            except Exception as e:
                print(f"Failed to rename {src} -> {dst}: {e}")

    return actions


def parse_ext_list(s: str) -> List[str]:
    parts = [p.strip().lower() for p in s.split(",") if p.strip()]
    normalized = []
    for p in parts:
        if not p.startswith("."):
            p = "." + p
        normalized.append(p)
    return normalized


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Rename images in a folder to a numeric sequence")
    p.add_argument("--dir", "-d", default=".", help="Directory containing images")
    p.add_argument("--prefix", "-p", default="", help="Prefix to add before the numeric sequence")
    p.add_argument("--start", type=int, default=1, help="Start number (default: 1)")
    p.add_argument("--padding", type=int, default=3, help="Zero-padding width (default: 3)")
    p.add_argument(
        "--exts",
        default="jpg,jpeg,png,gif,webp,bmp",
        help="Comma-separated list of extensions to include (default: common image types)",
    )
    p.add_argument(
        "--pattern",
        default=None,
        help=(
            "Filename pattern using Python format with `n` as the sequence integer. "
            "Examples: 'test_board_{n}', 'test_board_{n:03d}.png'. If provided, this takes precedence "
            "over --prefix/--sep/--padding."
        ),
    )
    p.add_argument(
        "--map-csv",
        default=None,
        help=(
            "Write a CSV file with two columns: name_raw,name_change. "
            "Useful to record or undo renames."
        ),
    )
    p.add_argument(
        "--apply-csv",
        default=None,
        help=(
            "Read a CSV with headers name_raw,name_change and perform the renames in the target directory. "
            "This mode ignores --pattern/--prefix/--padding and applies the explicit mapping."
        ),
    )
    p.add_argument("--dry-run", action="store_true", help="Show changes without renaming files")
    p.add_argument(
        "--sort",
        choices=("name", "mtime"),
        default="name",
        help="Sort files by 'name' (natural) or 'mtime' (modification time). Default: name",
    )
    p.add_argument(
        "--sep",
        default="_",
        help="Separator between prefix and number (default: '_')",
    )
    return p


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    directory = os.path.abspath(args.dir)
    # Try a few common normalizations if the provided path doesn't exist.
    def resolve_directory(p: str) -> str | None:
        candidates = []
        candidates.append(p)
        # strip accidental surrounding quotes
        candidates.append(p.strip('"').strip("'"))
        # expand ~
        candidates.append(os.path.expanduser(p))
        # absolute
        try:
            candidates.append(os.path.abspath(p))
        except Exception:
            pass
        # swap back/forward slashes
        candidates.append(p.replace('\\', '/'))
        candidates.append(p.replace('/', '\\'))

        # de-escape common escaped characters (in case the shell produced control chars)
        try:
            decoded = p.encode('utf-8').decode('unicode_escape')
            candidates.append(decoded)
        except Exception:
            pass

        # return the first existing candidate
        seen = set()
        for c in candidates:
            if not c:
                continue
            if c in seen:
                continue
            seen.add(c)
            if os.path.isdir(c):
                return os.path.abspath(c)
        return None

    resolved = resolve_directory(args.dir)
    if not resolved:
        print(f"Error: directory not found: {args.dir}")
        print("Tried several path normalizations. Please check the path. Candidates tried:")
        samples = [args.dir, args.dir.strip('"').strip("'"), os.path.expanduser(args.dir), os.path.abspath(args.dir), args.dir.replace('\\', '/'), args.dir.replace('/', '\\')]
        for s in samples:
            print(f"  - {s}")
        return 2
    directory = resolved
    exts = parse_ext_list(args.exts)
    # If an explicit mapping CSV is supplied, apply it and exit.
    if args.apply_csv:
        apply_csv_mapping(directory=directory, csv_path=args.apply_csv, dry_run=args.dry_run)
        return 0

    rename_sequence(
        directory=directory,
        prefix=args.prefix,
        start=args.start,
        padding=args.padding,
        exts=exts,
        dry_run=args.dry_run,
        sort_by=args.sort,
        separator=args.sep,
        pattern=args.pattern,
        map_csv=args.map_csv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
