"""The Sunday Globe - one front page summing up Sunday 22 November 2026.

Pure-stdlib Python 3.13 program. Draws a 1024x1024 newspaper front page
(35 dated stories from 7 regions, 11 illustrated panels, a briefs column
and a date-check strip) and writes it to /output/entry.png.

Deterministic: no clock, no randomness, no network, no files read.
Two runs produce byte-identical output.
"""

import os
import struct
import zlib
from binascii import crc32

WIDTH = 1024
HEIGHT = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)
INK = (22, 22, 22)
RED = (176, 36, 28)
BLUE = (29, 78, 137)
TEAL = (0, 118, 112)
GOLD = (176, 141, 44)
BROWN = (122, 74, 32)
CREAM = (253, 248, 236)
SKY = (176, 214, 235)
SEA = (24, 58, 96)
SAND = (232, 211, 160)
GREY = (110, 110, 108)
LGREY = (205, 205, 200)
DGREY = (58, 58, 58)
ORANGE = (224, 110, 20)
GREEN = (46, 125, 50)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
NAVY = (16, 32, 64)
ROSE = (214, 120, 110)

# ------------------------------------------------------------------- png
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, w, h, px):
    """px: bytearray of w*h*3 RGB bytes, row-major, top to bottom."""
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n"
    blob += _chunk(b"IHDR", ihdr)
    blob += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    blob += _chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(blob)


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if (r - t) ** 2 <= d2 <= (r + t) ** 2:
                    self.set(xx, yy, c)

    def poly(self, pts, c):
        """Fill a polygon given as a list of (x, y) points."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(round(xs[k]))
                xb = int(round(xs[k + 1]))
                self.rect(xa, y, xb - xa + 1, 1, c)

    def outline(self, x, y, w, h, c, t=1):
        self.rect(x, y, w, t, c)
        self.rect(x, y + h - t, w, t, c)
        self.rect(x, y, t, h, c)
        self.rect(x + w - t, y, t, h, c)


# ------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 cells, '#' = ink, '.' = empty. Uppercase only.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ";": ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "#": ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
}

BLANK = ("00000", "00000", "00000", "00000", "00000", "00000", "00000")


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, scale, color, text):
    """Draw uppercase text; returns x position just past the last glyph."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch, BLANK)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(cx + col * scale, y + row * scale, scale, scale, color)
        cx += 6 * scale
    return cx - scale


def draw_centered(cv, cx, y, scale, color, text):
    w = text_width(text, scale)
    draw_text(cv, cx - w // 2, y, scale, color, text)


def wrap_text(text, scale, max_w):
    """Greedy word wrap; returns a list of lines that fit max_w."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_block(cv, x, y, scale, color, text, max_w, max_lines, leading):
    """Draw wrapped text; returns number of lines drawn."""
    lines = wrap_text(text, scale, max_w)[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * leading, scale, color, ln)
    return len(lines)


# ------------------------------------------------------------ illustrations
# Each takes (cv, x, y, w, h): the panel's picture area. Flat, bold shapes
# that still read when the page is shrunk to ~300 px across.

def art_cop31(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    cv.circle(x + w - 26, y + 22, 15, GOLD)
    cv.poly([(x, y + h), (x + w // 3, y + h - 34), (x + 2 * w // 3, y + h)], GREEN)
    cv.poly([(x + w // 3, y + h), (x + 2 * w // 3, y + h - 26), (x + w, y + h)], TEAL)
    # negotiation table with three flags
    cv.rect(x + 14, y + h - 26, w - 28, 6, BROWN)
    for i, col in enumerate((BLUE, GREEN, RED)):
        fx = x + 24 + i * 26
        cv.vline(fx, y + h - 52, 28, INK, 2)
        cv.rect(fx + 2, y + h - 52, 20, 12, col)
    cv.circle(x + w // 2 - 16, y + h - 40, 6, INK)
    cv.circle(x + w // 2 + 16, y + h - 40, 6, INK)


def art_gulf(cv, x, y, w, h):
    cv.rect(x, y, w, h, NAVY)
    cv.rect(x, y + h - 26, w, 26, SEA)
    cv.rect(x, y + h - 30, w, 3, (120, 170, 210))
    # ship silhouette
    cv.poly([(x + 16, y + h - 30), (x + w - 16, y + h - 30),
             (x + w - 30, y + h - 12), (x + 30, y + h - 12)], DGREY)
    cv.rect(x + 30, y + h - 52, 60, 22, DGREY)
    cv.rect(x + 96, y + h - 46, 26, 16, DGREY)
    # blast above the ship
    bx, by = x + w - 44, y + 26
    cv.poly([(bx, by - 18), (bx + 8, by - 4), (bx + 20, by - 8), (bx + 10, by + 4),
             (bx + 16, by + 16), (bx, by + 8), (bx - 16, by + 16), (bx - 10, by + 4),
             (bx - 20, by - 8), (bx - 8, by - 4)], ORANGE)
    cv.circle(bx, by, 7, (255, 210, 60))
    # radar arcs
    cv.ring(x + 26, y + 24, 12, (120, 200, 120), 2)
    cv.ring(x + 26, y + 24, 20, (120, 200, 120), 1)


def art_peru(cv, x, y, w, h):
    cv.rect(x, y, w, h, (214, 228, 240))
    cv.poly([(x, y + h), (x + w // 4, y + 18), (x + w // 2, y + h)], (122, 96, 66))
    cv.poly([(x + w // 3, y + h), (x + 2 * w // 3, y + 12), (x + w, y + h)], (96, 74, 52))
    cv.poly([(x + w // 4 - 12, y + 30), (x + w // 4, y + 18),
             (x + w // 4 + 12, y + 30)], WHITE)
    cv.poly([(x + 2 * w // 3 - 14, y + 28), (x + 2 * w // 3, y + 12),
             (x + 2 * w // 3 + 14, y + 28)], WHITE)
    # seismograph strip
    cv.rect(x + 10, y + h - 34, w - 20, 26, WHITE)
    cv.outline(x + 10, y + h - 34, w - 20, 26, INK, 1)
    pts = [(x + 14, y + h - 21), (x + 30, y + h - 21), (x + 38, y + h - 30),
           (x + 46, y + h - 12), (x + 54, y + h - 21), (x + 74, y + h - 21),
           (x + 82, y + h - 32), (x + 90, y + h - 10), (x + 98, y + h - 21),
           (x + w - 14, y + h - 21)]
    for a, b in zip(pts, pts[1:]):
        cv.line(a[0], a[1], b[0], b[1], RED, 2)


def art_sparta(cv, x, y, w, h):
    cv.rect(x, y, w, h, (150, 180, 205))
    cv.rect(x, y + h - 30, w, 30, SEA)
    for i in range(4):
        cv.rect(x + 8 + i * 34, y + h - 24, 26, 3, (120, 170, 210))
    # burning cargo ship
    cv.poly([(x + 20, y + h - 30), (x + w - 20, y + h - 30),
             (x + w - 34, y + h - 12), (x + 34, y + h - 12)], (40, 40, 40))
    cv.rect(x + 34, y + h - 52, 52, 22, (60, 60, 60))
    cv.rect(x + 92, y + h - 52, 40, 22, (60, 60, 60))
    for fx, fh in ((x + 44, 12), (x + 66, 16), (x + 104, 12)):
        cv.poly([(fx - 10, y + h - 52), (fx, y + h - 52 - fh),
                 (fx + 10, y + h - 52)], ORANGE)
        cv.poly([(fx - 5, y + h - 52), (fx, y + h - 52 - fh + 12),
                 (fx + 5, y + h - 52)], (255, 210, 60))
    cv.circle(x + w - 26, y + 18, 9, (90, 90, 90))
    cv.circle(x + w - 40, y + 26, 7, (120, 120, 120))


def art_sinaloa(cv, x, y, w, h):
    cv.rect(x, y, w, h, SAND)
    cv.circle(x + w - 24, y + 20, 13, GOLD)
    # jail bars
    for i in range(6):
        cv.vline(x + 12 + i * 14, y + 8, h - 16, DGREY, 4)
    # gold badge star
    cx, cy = x + w // 2, y + h // 2 + 6
    cv.poly([(cx, cy - 20), (cx + 6, cy - 6), (cx + 20, cy - 4), (cx + 10, cy + 6),
             (cx + 14, cy + 20), (cx, cy + 12), (cx - 14, cy + 20), (cx - 10, cy + 6),
             (cx - 20, cy - 4), (cx - 6, cy - 6)], GOLD)
    cv.circle(cx, cy + 1, 5, RED)
    # handcuffs, clear of the bars
    cv.ring(x + 168, y + h - 22, 9, INK, 2)
    cv.ring(x + 192, y + h - 22, 9, INK, 2)
    cv.line(x + 177, y + h - 22, x + 183, y + h - 22, INK, 2)


def art_kryvyi(cv, x, y, w, h):
    cv.rect(x, y, w, h, (52, 52, 74))
    cv.circle(x + w - 24, y + 16, 10, (230, 220, 190))
    ground = y + h - 20
    # skyline, kept inside the art area
    for i, bh in enumerate((20, 30, 24, 36, 22, 28)):
        bx = x + 10 + i * 22
        cv.rect(bx, ground - bh, 18, bh, (24, 24, 34))
        for wy in range(ground - bh + 4, ground - 6, 10):
            cv.rect(bx + 4, wy, 4, 4, (255, 210, 90))
    # missile trail + blast, inside the art area
    cv.line(x + 18, y + 10, x + 66, ground - 34, (220, 220, 220), 2)
    bx, by = x + 70, ground - 38
    cv.poly([(bx, by - 12), (bx + 7, by - 3), (bx + 14, by - 6), (bx + 8, by + 3),
             (bx + 11, by + 11), (bx, by + 6), (bx - 11, by + 11), (bx - 8, by + 3),
             (bx - 14, by - 6), (bx - 7, by - 3)], ORANGE)
    cv.circle(bx, by, 5, (255, 210, 60))


def art_nepal(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    cv.circle(x + 22, y + 18, 10, WHITE)
    cv.circle(x + 30, y + 22, 8, WHITE)
    # plane
    px, py = x + w // 2, y + 26
    cv.poly([(px - 34, py), (px + 30, py), (px + 40, py + 4), (px - 30, py + 6)], WHITE)
    cv.poly([(px - 4, py - 12), (px + 6, py - 12), (px + 10, py), (px - 8, py)], WHITE)
    cv.poly([(px - 26, py + 4), (px - 16, py + 4), (px - 12, py + 12), (px - 24, py + 12)], WHITE)
    # runway + two flags
    cv.rect(x, y + h - 14, w, 4, DGREY)
    for i, cols in enumerate((((200, 30, 40), BLUE), ((255, 153, 51), GREEN))):
        fx = x + 18 + i * 34
        cv.vline(fx, y + h - 48, 36, INK, 2)
        for j, col in enumerate(cols):
            cv.rect(fx + 2, y + h - 48 + j * 11, 22, 11, col)


def art_basra(cv, x, y, w, h):
    cv.rect(x, y, w, h, (48, 40, 46))
    cv.rect(x, y + h - 22, w, 22, (28, 24, 22))
    # cooling towers, kept inside the art area
    for tx in (x + 16, x + 62, x + 108):
        cv.poly([(tx, y + h - 22), (tx + 6, y + h - 56), (tx + 28, y + h - 56),
                 (tx + 34, y + h - 22)], (88, 80, 76))
    # flame + smoke, inside the art area
    cv.poly([(x + 92, y + h - 56), (x + 104, y + h - 68), (x + 116, y + h - 56)], ORANGE)
    cv.poly([(x + 98, y + h - 56), (x + 104, y + h - 64), (x + 110, y + h - 56)],
            (255, 210, 60))
    cv.circle(x + 122, y + 8, 6, (120, 118, 114))
    cv.circle(x + 134, y + 16, 5, (140, 138, 134))


def art_summit(cv, x, y, w, h):
    cv.rect(x, y, w, h, (226, 232, 238))
    # table
    cv.rect(x + 12, y + h - 30, w - 24, 8, BROWN)
    cv.rect(x + 20, y + h - 22, 6, 22, BROWN)
    cv.rect(x + w - 26, y + h - 22, 6, 22, BROWN)
    # three flags: US, China, Russia
    flags = [
        ((200, 30, 40), (255, 255, 255), (30, 60, 140)),
        ((222, 20, 20), (255, 220, 60), None),
        ((255, 255, 255), (0, 90, 180), (200, 30, 40)),
    ]
    for i, cols in enumerate(flags):
        fx = x + 16 + i * 38
        cv.vline(fx, y + 12, 44, INK, 2)
        for j, col in enumerate(cols):
            if col is None:
                continue
            cv.rect(fx + 2, y + 12 + j * 11, 30, 11, col)
    # three seated figures
    for i in range(3):
        fx = x + 26 + i * 38
        cv.circle(fx + 8, y + h - 46, 6, INK)
        cv.rect(fx, y + h - 40, 16, 14, DGREY)


def art_poland(cv, x, y, w, h):
    cv.rect(x, y, w, h, (200, 208, 214))
    # abstract map outline
    cv.poly([(x + 14, y + 18), (x + w - 40, y + 10), (x + w - 14, y + 34),
             (x + w - 30, y + h - 14), (x + 30, y + h - 22), (x + 10, y + 44)],
            (168, 180, 188))
    cv.outline(x + 14, y + 10, w - 28, h - 24, GREY, 1)
    # missile
    mx, my = x + w // 2 - 6, y + 26
    cv.rect(mx, my, 12, 34, DGREY)
    cv.poly([(mx, my), (mx + 6, my - 12), (mx + 12, my)], DGREY)
    cv.poly([(mx - 8, my + 34), (mx, my + 26), (mx, my + 34)], DGREY)
    cv.poly([(mx + 12, my + 34), (mx + 12, my + 26), (mx + 20, my + 34)], DGREY)
    # warning triangle
    tx, ty = x + w - 44, y + h - 44
    cv.poly([(tx, ty), (tx + 18, ty + 30), (tx - 18, ty + 30)], (255, 200, 40))
    cv.outline(tx - 18, ty, 36, 30, INK, 1)
    cv.rect(tx - 1, ty + 8, 3, 12, INK)
    cv.rect(tx - 1, ty + 23, 3, 3, INK)


def art_estonia(cv, x, y, w, h):
    cv.rect(x, y, w, h, (16, 44, 30))
    cx, cy = x + w // 2 - 18, y + h // 2 + 2
    cv.ring(cx, cy, 30, (60, 200, 110), 2)
    cv.ring(cx, cy, 20, (60, 200, 110), 1)
    cv.ring(cx, cy, 10, (60, 200, 110), 1)
    cv.line(cx, cy, cx + 30, cy - 16, (120, 240, 160), 2)
    cv.circle(cx + 12, cy - 8, 3, (255, 210, 60))
    cv.circle(cx - 14, cy + 10, 3, (255, 210, 60))
    cv.circle(cx + 4, cy + 16, 3, (255, 210, 60))
    # jet silhouette
    jx, jy = x + w - 34, y + 16
    cv.poly([(jx, jy), (jx + 26, jy + 6), (jx, jy + 10), (jx + 4, jy + 5)], LGREY)


# A coarse dotted world map, drawn from a small land grid. The grid is
# written from memory: rough continent shapes, good enough at 40 px tall.
WORLD_MAP = [
    "..........####....................####............",
    ".....##########......####....#################....",
    "...############...########..###################..",
    "..###########......######....#################...",
    "...#########........####......########..######....",
    "....#######..........##........#####....####.......",
    ".....#####...........#..........###....###.........",
    "......###......................##....##..........",
    "......##........................#................",
    ".......#.........................................",
]


def draw_world_map(cv, x, y, dot, gap, color):
    for r, row in enumerate(WORLD_MAP):
        for c, ch in enumerate(row):
            if ch == "#":
                cv.circle(x + c * gap, y + r * gap, dot, color)


# ------------------------------------------------------------------- data
# 35 stories, all dated Sunday 22 November 2026 in the day's news cycle:
# 11 illustrated panels + 24 briefs, across 7 regions.
LEAD = [
    ("COP31", TEAL, art_cop31,
     "COP31 NEARS A DEAL IN ANTALYA",
     "NEW DEAL TEXT FACES A SUNDAY VOTE IN ANTALYA."),
    ("GULF", RED, art_gulf,
     "IRAN HITS US BASES IN BAHRAIN",
     "TEHRAN CLAIMS TWO BASES HIT; US HITS QESHM."),
    ("PERU", BROWN, art_peru,
     "M6.8 QUAKE SHAKES PERU",
     "FELT IN LIMA; 152 HOMES LEFT UNINHABITABLE."),
]

SMALL = [
    ("SPARTA II", BLUE, art_sparta,
     "SPARTA II ABLAZE",
     "DRONE HIT, SHIP BURNS OFF FINLAND."),
    ("SINALOA", RED, art_sinaloa,
     "SINALOA KINGPIN SEIZED",
     "CHAPO ISIDRO HELD; 11 DEAD IN GUASAVE."),
    ("UKRAINE", DGREY, art_kryvyi,
     "MISSILE STRIKES KRYVYI RIH",
     "BOY, 7, AMONG THE DEAD; 58 HURT."),
    ("NEPAL", (200, 30, 40), art_nepal,
     "SHAH ARRIVES IN DELHI",
     "FIRST TRIP ABROAD SINCE MARCH."),
    ("BASRA", ORANGE, art_basra,
     "BASRA POWER PLANT FIRE",
     "4 DEAD, 35 HURT AT HARTHA STATION."),
    ("SUMMIT", NAVY, art_summit,
     "TRUMP, XI AND PUTIN MEET",
     "FIRST TRILATERAL SUMMIT IN SHENZHEN"),
    ("POLAND", RED, art_poland,
     "MISSILE FOUND IN POLAND",
     "KH-101 FOUND; NATO ALARMED."),
    ("ESTONIA", GREEN, art_estonia,
     "ESTONIA DRONE ALERT",
     "TURKISH NATO JETS SCRAMBLE AT DAWN."),
]

BRIEFS = [
    "UKRAINE: 117 OF 148 DRONES DOWNED",
    "KYIV: DEBRIS WOUNDS 2, HOUSES BURN",
    "LVIV: RUSSIAN STRIKE KILLS 2",
    "US FLOATS NATO-STYLE GUARANTEES",
    "EU ADOPTS 1BN ARMS AID FOR UKRAINE",
    "EU AND INDONESIA SIGN TRADE DEALS",
    "EU BUDGET: COSTA PROPOSES 1.78TN PLAN",
    "DENMARK EXPELS RUSSIAN DEFENCE ATTACHE",
    "FINLAND PROBES HELICOPTER INCURSION",
    "BRUSSELS FLIGHTS FACE CANCELLATIONS",
    "CROATIA: RALLY OVER PATIENT DEATH",
    "ECB BOARD RACE: BOONE, BRUNNERMEIER",
    "GAZA STRIKE HITS MILITANTS; DENIAL",
    "US SANCTIONS 4 IRANIANS OVER OIL CASH",
    "HORMUZ: TANKERS HIT, FIRE REPORTED",
    "TRUMP VOWS LASTING IRAN NUCLEAR DEAL",
    "MELANIA TRUMP HOPES FOR CHRISTMAS TRUCE",
    "TRUMP PUSHES UKRAINE DEAL BY JANUARY",
    "NIGERIA: 24 BODIES AFTER BOAT CAPSIZE",
    "PANAMA VOWS TO BLOCK A COP31 DEAL",
    "HOEKSTRA: NO DEAL BEATS A WEAK DEAL",
    "TURKIYE'S COP SIDE DEALS TOP $26BN",
    "ANTONELLI TAKES LAS VEGAS POLE",
    "ZELENSKY: SUMMIT A FLOP FOR RUSSIA",
]


# ------------------------------------------------------------------ layout
def panel_big(cv, x, y, w, h, region, color, art, headline, caption):
    cv.outline(x, y, w, h, INK, 1)
    cv.rect(x + 1, y + 1, w - 2, 18, color)
    draw_text(cv, x + 8, y + 3, 2, WHITE, region)
    draw_text(cv, x + w - 8 - text_width("22 NOV", 2), y + 3, 2, WHITE, "22 NOV")
    art(cv, x + 1, y + 19, w - 2, 100)
    cv.hline(x + 1, y + 119, w - 2, INK, 1)
    draw_block(cv, x + 8, y + 126, 3, INK, headline, w - 16, 2, 24)
    draw_block(cv, x + 8, y + 174, 2, DGREY, caption, w - 16, 2, 17)


def panel_small(cv, x, y, w, h, region, color, art, headline, caption):
    cv.outline(x, y, w, h, INK, 1)
    cv.rect(x + 1, y + 1, w - 2, 14, color)
    draw_text(cv, x + 6, y + 2, 2, WHITE, region)
    art(cv, x + 1, y + 15, w - 2, 70)
    cv.hline(x + 1, y + 85, w - 2, INK, 1)
    draw_block(cv, x + 6, y + 90, 2, INK, headline, w - 12, 2, 17)
    draw_block(cv, x + 6, y + 126, 2, DGREY, caption, w - 12, 2, 17)


def build():
    cv = Canvas(WIDTH, HEIGHT, PAPER)
    cv.outline(12, 12, 1000, 1000, INK, 2)
    cv.outline(18, 18, 988, 988, INK, 1)

    # masthead
    draw_centered(cv, 512, 28, 6, INK, "THE SUNDAY GLOBE")
    cv.hline(120, 76, 784, INK, 2)
    draw_centered(cv, 512, 84, 2, INK,
                  "SUNDAY 22 NOVEMBER 2026 - THE WORLD IN ONE DAY")

    # black strip: story count + date
    cv.rect(24, 106, 976, 22, INK)
    draw_centered(cv, 512, 110, 2, WHITE,
                  "35 STORIES - 7 REGIONS - EVERY STORY DATED 22 NOVEMBER 2026")

    # lead row: 3 big panels
    for i, (region, color, art, headline, caption) in enumerate(LEAD):
        panel_big(cv, 24 + i * 328, 136, 320, 208,
                  region, color, art, headline, caption)

    # rows 2 and 3: 4 small panels each
    for row, items in enumerate((SMALL[:4], SMALL[4:])):
        y = 352 + row * 168
        for i, (region, color, art, headline, caption) in enumerate(items):
            panel_small(cv, 24 + i * 246, y, 238, 160,
                        region, color, art, headline, caption)

    # briefs header
    cv.hline(24, 688, 976, INK, 2)
    draw_centered(cv, 512, 694, 2, INK,
                  "THE DAY IN BRIEF - 24 MORE STORIES, ALL DATED 22 NOVEMBER 2026")
    cv.hline(24, 712, 976, INK, 1)

    # briefs: two columns of 12
    for col in range(2):
        bx = 24 + col * 496
        for r in range(12):
            brief = BRIEFS[col * 12 + r]
            ry = 720 + r * 20
            cv.rect(bx, ry + 4, 6, 6, RED)
            draw_text(cv, bx + 12, ry + 1, 2, INK, brief)

    # bottom band: dotted world map + date check
    cv.hline(24, 962, 976, INK, 1)
    draw_world_map(cv, 30, 968, 1, 3, BLUE)
    draw_text(cv, 200, 972, 2, INK,
              "DATE CHECK - ALL 35 STORIES DATED SUNDAY 22 NOVEMBER 2026")
    return cv


def main():
    cv = build()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    write_png(path, WIDTH, HEIGHT, cv.px)


if __name__ == "__main__":
    main()


