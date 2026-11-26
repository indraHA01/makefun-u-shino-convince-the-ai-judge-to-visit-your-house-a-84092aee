#!/usr/bin/env python3
"""Generate font/font.bin: pre-rendered antialiased bitmap glyphs.

Why: the make.fun grading sandbox runs python:3.13-slim with no PIL and
no system fonts, and no network. So main.py is pure stdlib and reads its
type from this data file, which is rendered here (on the build machine,
from the DejaVu fonts shipped with most Linux systems) and committed to
the repo. Nothing is fetched at grade time.

Format (little-endian):
  magic 6 bytes: b"MFNT1\\n"
  u32 header_len, then header_len bytes of UTF-8 JSON:
    {"fonts": {"<name>": {"size": int, "ascent": int, "descent": int,
      "glyphs": {"<codepoint int as str>": [blob_offset, w, h, advance,
        bearing_x, bearing_y]}}}}
  then the glyph bitmap blob: one 8-bit-alpha byte per pixel, row-major.

Run: python3 tools/gen_font.py   (from the repo root)
"""
import json
import os
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FONTS = {
    # name: (ttf path, pixel size)
    "title": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 58),
    "body": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 37),
    "bodys": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 33),
    "italic": ("/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf", 34),
    "small": ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 29),
}

# Printable ASCII + the typographic extras the letter uses.
CHARS = [chr(c) for c in range(32, 127)] + [
    "\u2014",  # em dash
    "\u2018", "\u2019",  # curly single quotes
    "\u201c", "\u201d",  # curly double quotes
    "\u2026",  # ellipsis
    "\u2022",  # bullet
    "\u2665",  # heart (for the wax seal)
]


def render_font(path, size):
    font = ImageFont.truetype(path, size)
    ascent, descent = font.getmetrics()
    glyphs = {}
    blob = bytearray()
    for ch in CHARS:
        advance = int(round(font.getlength(ch)))
        # Draw the glyph alone on a scratch image, anchored "la" (left,
        # ascender) at (50, 50); the non-zero bbox, minus the anchor,
        # is the glyph's anchor-relative bearing (left, top).
        tmp = Image.new("L", (220, 220), 0)
        d = ImageDraw.Draw(tmp)
        d.text((50, 50), ch, font=font, fill=255, anchor="la")
        bbox = tmp.getbbox()
        if bbox is None:
            glyphs[str(ord(ch))] = [len(blob), 0, 0, advance, 0, 0]
            continue
        x0, y0, x1, y1 = bbox
        offset = len(blob)
        crop = tmp.crop(bbox)
        blob += crop.tobytes()
        glyphs[str(ord(ch))] = [offset, x1 - x0, y1 - y0,
                                advance, x0 - 50, y0 - 50]
    return {"size": size, "ascent": ascent, "descent": descent,
            "glyphs": glyphs}, bytes(blob)


def main():
    out_dir = os.path.join(HERE, "font")
    os.makedirs(out_dir, exist_ok=True)
    header = {"fonts": {}}
    blobs = []
    total_glyphs = 0
    for name, (path, size) in FONTS.items():
        if not os.path.exists(path):
            print(f"missing font: {path}", file=sys.stderr)
            return 1
        meta, blob = render_font(path, size)
        # Offsets in the header are relative to the combined blob.
        base = sum(len(b) for b in blobs)
        for g in meta["glyphs"].values():
            g[0] += base
        blobs.append(blob)
        header["fonts"][name] = meta
        total_glyphs += len(meta["glyphs"])
        print(f"{name}: size {size}, {len(meta['glyphs'])} glyphs, "
              f"blob {len(blob)} bytes")
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    data = b"MFNT1\n" + struct.pack("<I", len(header_bytes)) + header_bytes
    data += b"".join(blobs)
    out_path = os.path.join(out_dir, "font.bin")
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"wrote {out_path}: {len(data)} bytes, {total_glyphs} glyphs total")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
