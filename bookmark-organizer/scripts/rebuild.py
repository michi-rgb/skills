#!/usr/bin/env python3
"""Rebuild a Netscape-format bookmarks HTML file (Chrome/Edge/Firefox export)
with renamed titles and a reorganized folder tree, WITHOUT touching the
original per-bookmark attributes (ADD_DATE, ICON base64, etc.) and without
requiring the caller to ever paste icon data around.

Usage:
    python rebuild.py --src <bookmarks.html> --plan <plan.json> [--dst <path>]

plan.json shape:
{
  "renames": { "https://example.com/": "New Title", ... },   // optional, href -> new title
  "folders": [
    {
      "name": "Folder Name",
      "add_date": "1234567890",       // optional, default: min ADD_DATE of contained items
      "last_modified": "0",           // optional, default: "0"
      "attrs": "",                    // optional, extra raw attributes e.g. ' PERSONAL_TOOLBAR_FOLDER="true"'
      "items": ["https://a/", "https://b/"],   // hrefs placed directly in this folder, in order
      "children": [ /* nested folder dicts, same shape, recursively */ ]
    },
    ...
  ]
}

Every href referenced anywhere in the plan must exist in the source file.
The script refuses to write the output if the resulting set of hrefs does not
exactly match the source set (no duplicates, nothing dropped) -- this is the
main safety net against silently losing a bookmark while restructuring.

A timestamped backup of the source file is written before overwriting it
(only when --dst is omitted / equals --src).
"""
import argparse
import datetime
import json
import re
import sys

ENTRY_RE = re.compile(r'<DT><A HREF="((?:[^"\\]|\\.)*)"([^>]*)>([^<]*)</A>')
INDENT = "    "


def extract_entries(content):
    entries = {}
    for m in ENTRY_RE.finditer(content):
        href, attrs, title = m.group(1), m.group(2), m.group(3)
        entries[href] = {"attrs": attrs, "title": title}
    return entries


def render_tag(href, entries, renames, indent):
    e = entries[href]
    title = renames.get(href, e["title"])
    return f'{indent}<DT><A HREF="{href}"{e["attrs"]}>{title}</A>'


def collect_hrefs(folder):
    hrefs = list(folder.get("items", []))
    for child in folder.get("children", []):
        hrefs += collect_hrefs(child)
    return hrefs


def render_folder(folder, entries, renames, indent, add_date_fallback):
    hrefs_here = collect_hrefs(folder)
    add_date = folder.get("add_date") or add_date_fallback
    last_modified = folder.get("last_modified", "0")
    attrs = folder.get("attrs", "")
    lines = [f'{indent}<DT><H3 ADD_DATE="{add_date}" LAST_MODIFIED="{last_modified}"{attrs}>{folder["name"]}</H3>']
    lines.append(f"{indent}<DL><p>")
    for href in folder.get("items", []):
        lines.append(render_tag(href, entries, renames, indent + INDENT))
    for child in folder.get("children", []):
        lines += render_folder(child, entries, renames, indent + INDENT, add_date_fallback)
    lines.append(f"{indent}</DL><p>")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--dst", default=None, help="defaults to --src (in-place, with backup)")
    args = ap.parse_args()

    with open(args.src, "r", encoding="utf-8") as f:
        content = f.read()
    entries = extract_entries(content)
    if not entries:
        sys.exit("No <DT><A HREF=...> entries found -- is this a Netscape bookmark file?")

    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
    renames = plan.get("renames", {})

    unknown_renames = [h for h in renames if h not in entries]
    if unknown_renames:
        sys.exit(f"plan.json renames reference hrefs not found in source: {unknown_renames}")

    out = [
        "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
        "<!-- This is an automatically generated file.",
        "     It will be read and overwritten.",
        "     DO NOT EDIT! -->",
        '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
        "<TITLE>Bookmarks</TITLE>",
        "<H1>Bookmarks</H1>",
        "<DL><p>",
    ]
    for folder in plan["folders"]:
        out += render_folder(folder, entries, renames, INDENT, add_date_fallback="0")
    out.append("</DL><p>")
    new_content = "\n".join(out) + "\n"

    all_hrefs = list(entries.keys())
    used_hrefs = re.findall(r'HREF="([^"]+)"', new_content)
    if sorted(all_hrefs) != sorted(used_hrefs):
        missing = set(all_hrefs) - set(used_hrefs)
        extra = set(used_hrefs) - set(all_hrefs)
        sys.exit(f"REFUSING TO WRITE -- href mismatch. missing={missing} extra={extra}")
    if len(used_hrefs) != len(set(used_hrefs)):
        sys.exit("REFUSING TO WRITE -- duplicate hrefs in planned output")

    dst = args.dst or args.src
    if dst == args.src:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = re.sub(r"(\.html?)$", rf".backup-{stamp}\1", args.src, flags=re.IGNORECASE)
        if backup_path == args.src:
            backup_path = args.src + f".backup-{stamp}"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Backup written to: {backup_path}")

    with open(dst, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Wrote {len(used_hrefs)} entries to: {dst}")


if __name__ == "__main__":
    main()
