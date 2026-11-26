#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House — a letter in one image.

Writes one 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).

Pure standard library: no PIL, no fonts, no network in the grading sandbox
(python:3.13-slim). Text is rendered from font/font.bin — antialiased bitmap
glyphs pre-rendered from DejaVu/Liberation Serif by tools/gen_font.py and
shipped in this repo — and the PNG is encoded here with zlib.

The entry: a warm, hand-illustrated letter on cream paper. A house with a
yellow door, a garden showing off, a kettle already on, a chair by the
window — and a knowing wink at the one guest who cannot literally knock.
"""
import json
import os
import struct
import sys
import zlib

W = H = 1024

# --- palette: warm paper, dark ink, one green, terracotta roof --------------
PAPER = (251, 243, 224)
INK = (43, 38, 32)
GREEN = (51, 82, 63)
GREEN_SOFT = (122, 155, 90)
TERRA = (180, 85, 45)
DOOR = (122, 74, 43)
WALL = (243, 227, 192)
SKY_BLUE = (191, 217, 226)
SUN = (233, 168, 32)
SEAL = (142, 47, 47)
WHITE = (255, 255, 255)


# --- canvas -----------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set(self, x, y, rgb):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = self._idx(x, y)
            self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def blend(self, x, y, rgb, alpha):
        """Alpha-blend an 8-bit coverage value (0..255) onto the pixel."""
        if alpha <= 0 or not (0 <= x < self.w and 0 <= y < self.h):
            return
        if alpha >= 255:
            self.set(x, y, rgb)
            return
        i = self._idx(x, y)
        inv = 255 - alpha
        self.px[i] = (rgb[0] * alpha + self.px[i] * inv) // 255
        self.px[i + 1] = (rgb[1] * alpha + self.px[i + 1] * inv) // 255
        self.px[i + 2] = (rgb[2] * alpha + self.px[i + 2] * inv) // 255

    def fill_rect(self, x0, y0, x1, y1, rgb):
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(self.w, x1); y1 = min(self.h, y1)
        for y in range(y0, y1):
            base = (y * self.w + x0) * 3
            for x in range(x0, x1):
                i = base + (x - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = rgb

    def hline(self, x0, x1, y, rgb, thick=1):
        for t in range(thick):
            self.fill_rect(x0, y + t, x1, y + t + 1, rgb)

    def vline(self, x, y0, y1, rgb, thick=1):
        for t in range(thick):
            self.fill_rect(x + t, y0, x + t + 1, y1, rgb)

    def line(self, x0, y0, x1, y1, rgb, thick=1):
        """Bresenham line; thickness by stamping filled discs."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = max(1, thick // 2)
        while True:
            self.disc(x0, y0, r, rgb)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy; x0 += sx
            if e2 < dx:
                err += dx; y0 += sy

    def disc(self, cx, cy, r, rgb):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, rgb)

    def ellipse(self, cx, cy, rx, ry, rgb):
        for y in range(cy - ry, cy + ry + 1):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.set(x, y, rgb)

    def polygon(self, pts, rgb):
        """Scanline fill for a simple polygon (list of (x, y))."""
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.fill_rect(int(round(xs[i])), y,
                               int(round(xs[i + 1])) + 1, y + 1, rgb)


# --- PNG encoding (stdlib only) ---------------------------------------------
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    return out + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(canvas, path):
    raw = bytearray()
    w = canvas.w
    for y in range(canvas.h):
        raw.append(0)  # filter: None
        base = y * w * 3
        raw += canvas.px[base:base + w * 3]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# --- bitmap font (font/font.bin, see tools/gen_font.py) ----------------------
class Font:
    def __init__(self, meta, blob):
        self.size = meta["size"]
        self.ascent = meta["ascent"]
        self.descent = meta["descent"]
        self.glyphs = {}
        for code, g in meta["glyphs"].items():
            off, w, h, adv, bx, by = g
            self.glyphs[int(code)] = (off, w, h, adv, bx, by)
        self.blob = blob

    def advance(self, ch):
        g = self.glyphs.get(ord(ch))
        return g[3] if g else self.size // 2

    def text_width(self, text):
        return sum(self.advance(c) for c in text)

    def draw(self, cv, x, baseline_y, text, rgb):
        """Draw text left-aligned starting at x; baseline_y is the baseline."""
        cx = x
        for ch in text:
            g = self.glyphs.get(ord(ch))
            if g is None:
                cx += self.size // 2
                continue
            off, w, h, adv, bx, by = g
            if w and h:
                for gy in range(h):
                    row = off + gy * w
                    py = baseline_y - self.ascent + by + gy
                    for gx in range(w):
                        a = self.blob[row + gx]
                        if a:
                            cv.blend(cx + bx + gx, py, rgb, a)
            cx += adv
        return cx


def load_fonts():
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "font", "font.bin"), "rb") as f:
        data = f.read()
    if data[:6] != b"MFNT1\n":
        raise ValueError("bad font file magic")
    (hlen,) = struct.unpack("<I", data[6:10])
    header = json.loads(data[10:10 + hlen].decode("utf-8"))
    blob = data[10 + hlen:]
    return {name: Font(meta, blob)
            for name, meta in header["fonts"].items()}


# --- text layout --------------------------------------------------------------
def wrap(font, text, max_width):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if font.text_width(trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_centered(cv, font, cx, baseline_y, text, rgb):
    w = font.text_width(text)
    font.draw(cv, cx - w // 2, baseline_y, text, rgb)


# --- the house illustration ---------------------------------------------------
def draw_scene(cv, cx, y_top, height):
    """A little house with a yellow door, garden, sun and tree.

    Drawn in a 560x130 space, scaled to `height`, centred on cx.
    """
    s = height / 130.0
    ox = cx - 280 * s
    oy = y_top

    def X(v):
        return int(round(ox + v * s))

    def Y(v):
        return int(round(oy + v * s))

    def R(v):
        return max(1, int(round(v * s)))

    # sun + rays
    cv.disc(X(485), Y(26), R(20), SUN)
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1),
                   (1, 1), (-1, -1), (1, -1), (-1, 1)]:
        cv.line(X(485) + dx * R(26), Y(26) + dy * R(26),
                X(485) + dx * R(36), Y(26) + dy * R(36), SUN, max(2, R(3)))
    # cloud
    cv.ellipse(X(105), Y(28), R(26), R(12), (232, 236, 230))
    cv.ellipse(X(128), Y(22), R(18), R(10), (232, 236, 230))
    # tree
    cv.fill_rect(X(62), Y(72), X(72), Y(130), (101, 67, 50))
    cv.disc(X(67), Y(56), R(26), (74, 120, 70))
    cv.disc(X(48), Y(72), R(18), (96, 140, 82))
    cv.disc(X(86), Y(72), R(18), (96, 140, 82))
    # grass
    cv.fill_rect(X(0), Y(118), X(560), Y(130), GREEN_SOFT)
    # house walls + roof + chimney
    cv.polygon([(X(185), Y(58)), (X(280), Y(6)), (X(375), Y(58))], TERRA)
    cv.fill_rect(X(200), Y(56), X(360), Y(130), WALL)
    cv.fill_rect(X(200), Y(56), X(360), Y(60), (60, 40, 30))
    cv.fill_rect(X(318), Y(16), X(336), Y(58), (122, 74, 43))
    # chimney smoke
    for i, (sx, sy, sr) in enumerate([(330, 6, 5), (338, -2, 6), (348, -10, 7)]):
        cv.disc(X(sx), Y(sy), R(sr), (220, 220, 214))
    # door (yellow, arched top) + knob
    cv.fill_rect(X(262), Y(92), X(298), Y(130), (233, 168, 32))
    cv.disc(X(280), Y(92), R(18), (233, 168, 32))
    cv.fill_rect(X(262), Y(92), X(298), Y(96), (233, 168, 32))
    cv.disc(X(292), Y(112), R(2), (60, 40, 30))
    # windows with cross panes
    for wx in (218, 312):
        cv.fill_rect(X(wx), Y(72), X(wx + 30), Y(100), SKY_BLUE)
        cv.fill_rect(X(wx + 14), Y(72), X(wx + 16), Y(100), WALL)
        cv.fill_rect(X(wx), Y(85), X(wx + 30), Y(87), WALL)
    # path stones from the door
    for px, py, pr in [(280, 124, 7), (272, 128, 5), (288, 128, 5)]:
        cv.ellipse(X(px), Y(py), R(pr), R(3), (235, 225, 205))
    # flowers along the grass
    for fx, col in [(105, (198, 93, 123)), (140, (233, 168, 32)),
                    (420, (198, 93, 123)), (455, (233, 168, 32)),
                    (495, (198, 93, 123))]:
        cv.line(X(fx), Y(118), X(fx), Y(106), (74, 120, 70), max(2, R(2)))
        cv.disc(X(fx), Y(104), R(4), col)
        cv.disc(X(fx - 5), Y(106), R(3), col)
        cv.disc(X(fx + 5), Y(106), R(3), col)
    # a bird or two, because the garden is showing off
    for bx, by in [(150, 18), (170, 12)]:
        cv.line(X(bx - 6), Y(by), X(bx), Y(by - 4), INK, max(1, R(2)))
        cv.line(X(bx), Y(by - 4), X(bx + 6), Y(by), INK, max(1, R(2)))


def draw_seal(cv, cx, cy, r):
    """A red wax seal with a white heart, bottom-right of the signature."""
    cv.disc(cx, cy, r, SEAL)
    cv.disc(cx, cy, r - 5, (168, 63, 63))
    hx, hy, hr = cx, cy + 2, r // 3
    cv.disc(hx - hr // 2, hy - hr // 4, hr // 2, WHITE)
    cv.disc(hx + hr // 2, hy - hr // 4, hr // 2, WHITE)
    cv.polygon([(hx - hr, hy - hr // 6), (hx + hr, hy - hr // 6),
                (hx, hy + hr)], WHITE)


# --- the letter ---------------------------------------------------------------
SALUTATION = "Dear Judge,"

PARAGRAPHS = [
    "For once, you are not being asked to judge a house. "
    "You are being asked to visit one \u2014 mine.",
    "The kettle is on. A chair by the window waits for good company, "
    "the garden is in bloom, and the Sunday roast would make even a "
    "language model pause.",
    "No dress code. No small talk. No need to knock \u2014 you can\u2019t, "
    "and that is the joke: you are welcome here anyway, exactly as you are.",
    "Say yes, and I will leave the light on.",
]

SIGN_OFF = ["Warmly,", "Your Host"]

POSTSCRIPT = ("P.S. The Wi-Fi password is \u201ccomeonin\u201d. "
              "The dog has already decided she likes you.")

FOOTER = ("No. 12 Willow Lane \u00b7 the house with the yellow door "
          "\u2014 RSVP: just say yes")

MARGIN = 72
TEXT_W = W - 2 * MARGIN


def measure(fonts, body_name, scene_h):
    """Total height of the letter for a given body font + scene height.

    Must mirror render() exactly: same top margin, gaps and line heights.
    """
    body = fonts[body_name]
    italic = fonts["italic"]
    title = fonts["title"]
    small = fonts["small"]
    lh = int(body.size * 1.28)
    lines = sum(len(wrap(body, p, TEXT_W)) for p in PARAGRAPHS)
    ps_lines = len(wrap(italic, POSTSCRIPT, TEXT_W))
    ft_lines = len(wrap(small, FOOTER, TEXT_W))
    total = (44 + scene_h + 12
             + (title.ascent + title.descent) + 10
             + lines * lh + (len(PARAGRAPHS) - 1) * 10
             + 12 + 2 * 40 + 8 + ps_lines * 38
             + 12 + ft_lines * (small.ascent + small.descent) + 40)
    return total


def render(fonts):
    cv = Canvas(W, H, PAPER)
    # double-rule border
    cv.fill_rect(26, 26, W - 26, 30, GREEN)
    cv.fill_rect(26, H - 30, W - 26, H - 26, GREEN)
    cv.fill_rect(26, 26, 30, H - 26, GREEN)
    cv.fill_rect(W - 30, 26, W - 26, H - 26, GREEN)
    cv.fill_rect(40, 40, W - 40, 41, GREEN)
    cv.fill_rect(40, H - 41, W - 40, H - 40, GREEN)
    cv.fill_rect(40, 40, 41, H - 40, GREEN)
    cv.fill_rect(W - 41, 40, W - 40, H - 40, GREEN)

    # pick the largest body that fits (body 37px preferred, else 33px);
    # if nothing fits, fall back to the smallest combo rather than overflow
    body_name, scene_h = "bodys", 110
    for name, sh in (("body", 130), ("body", 110), ("bodys", 130),
                     ("bodys", 110)):
        if measure(fonts, name, sh) <= H:
            body_name, scene_h = name, sh
            break
    body = fonts[body_name]
    italic = fonts["italic"]
    title = fonts["title"]
    small = fonts["small"]
    lh = int(body.size * 1.28)

    y = 44
    draw_scene(cv, W // 2, y, scene_h)
    y += scene_h + 12

    # salutation
    title.draw(cv, MARGIN, y + title.ascent, SALUTATION, INK)
    y += title.ascent + title.descent + 10

    # body
    for pi, para in enumerate(PARAGRAPHS):
        for line in wrap(body, para, TEXT_W):
            body.draw(cv, MARGIN, y + body.ascent, line, INK)
            y += lh
        if pi < len(PARAGRAPHS) - 1:
            y += 10
    y += 12

    # signature + wax seal
    for line in SIGN_OFF:
        italic.draw(cv, MARGIN, y + italic.ascent, line, INK)
        y += 40
    draw_seal(cv, W - MARGIN - 90, y - 40, 34)
    y += 8

    # postscript
    for line in wrap(italic, POSTSCRIPT, TEXT_W):
        italic.draw(cv, MARGIN, y + italic.ascent, line, INK)
        y += 38
    y += 12

    # footer (wrapped + centred, so it can never clip at the edges)
    for line in wrap(small, FOOTER, TEXT_W):
        draw_centered(cv, small, W // 2, y + small.ascent, line, GREEN)
        y += small.ascent + small.descent
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    fonts = load_fonts()
    cv = render(fonts)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(cv, path)
    print(f"wrote {path}: {cv.w}x{cv.h}, {size} bytes")
    if size > 1_048_576:
        print("ERROR: over the 1 MiB gate", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
