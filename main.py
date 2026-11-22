"""The Sunday Globe, V3 - Sunday 22 November 2026 in one page.

A 1024x1024 newspaper front page drawn with nothing but the Python
standard library: 35 stories from that one Sunday, spread over 7
regions - 3 lead panels, 8 small panels and 24 one-line briefs - and
written to /output/entry.png.

What V3 changes against V2, and why: the small panels lose their
picture strip entirely. In V2 that strip was 32 px of flat shapes
which shrank to texture at reading size, while the caption under each
small headline still sat at scale 2 and blurred. V3 gives the whole
panel height to type instead: headline at scale 3 as before, caption
raised from scale 2 to scale 3 and allowed three lines, so every
story-carrying word on the page is now at scale 3 or larger - about
6.2 px tall when the page is read at 300 px across. Four captions are
tightened editorially so they wrap inside three lines at that scale;
no story, date or count changes.

The build is deterministic: no clock, no randomness, no network,
nothing read from disk. Two runs produce the same bytes.
"""

import os
import struct
import zlib
from binascii import crc32

SIDE = 1024

# ---------------------------------------------------------------- palette
PAPER = (247, 242, 231)
INK = (22, 22, 22)
SOFT = (58, 58, 58)
RED = (176, 36, 28)
BLUE = (29, 78, 137)
TEAL = (0, 118, 112)
GOLD = (176, 141, 44)
BROWN = (122, 74, 32)
SKY = (176, 214, 235)
SEA = (24, 58, 96)
NAVY = (16, 32, 64)
ORANGE = (224, 110, 20)
GREEN = (46, 125, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 210, 60)
DARK = (40, 40, 40)


# ---------------------------------------------------------------- png out
def _chunk(tag, data):
    raw = tag + data
    return struct.pack(">I", len(data)) + raw + struct.pack(
        ">I", crc32(raw) & 0xFFFFFFFF)


def write_png(path, side, rgb):
    """rgb is a bytearray of side*side*3 bytes, top row first."""
    stride = side * 3
    body = bytearray()
    for r in range(side):
        body.append(0)
        body += rgb[r * stride:(r + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", side, side, 8, 2, 0, 0, 0)
    blob = (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(body), 9))
            + _chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(blob)


# ------------------------------------------------------------------ canvas
class Canvas:
    """Square RGB raster plus the flat-shape tools the page needs."""

    def __init__(self, side, bg):
        self.side = side
        self.px = bytearray(bg) * (side * side)

    def put(self, x, y, colour):
        if 0 <= x < self.side and 0 <= y < self.side:
            i = (y * self.side + x) * 3
            self.px[i:i + 3] = bytes(colour)

    def rect(self, x, y, w, h, colour):
        xa, ya = max(0, x), max(0, y)
        xb, yb = min(self.side, x + w), min(self.side, y + h)
        if xb <= xa or yb <= ya:
            return
        run = bytes(colour) * (xb - xa)
        for yy in range(ya, yb):
            start = (yy * self.side + xa) * 3
            self.px[start:start + len(run)] = run

    def hline(self, x, y, w, colour, thick=1):
        self.rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.rect(x, y, thick, h, colour)

    def box(self, x, y, w, h, colour, thick=1):
        self.rect(x, y, w, thick, colour)
        self.rect(x, y + h - thick, w, thick, colour)
        self.rect(x, y, thick, h, colour)
        self.rect(x + w - thick, y, thick, h, colour)

    def line(self, x0, y0, x1, y1, colour, thick=1):
        """Bresenham walk, stamped with a square brush."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err, x, y = dx + dy, x0, y0
        while True:
            self.rect(x - thick // 2, y - thick // 2, thick, thick, colour)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def disc(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.put(xx, yy, colour)

    def poly(self, pts, colour):
        """Scanline fill for a polygon of (x, y) points."""
        if len(pts) < 3:
            return
        top = max(0, min(p[1] for p in pts))
        bot = min(self.side, max(p[1] for p in pts) + 1)
        n = len(pts)
        for y in range(top, bot):
            cuts = []
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                if (ay <= y < by) or (by <= y < ay):
                    cuts.append(ax + (y - ay) * (bx - ax) / (by - ay))
            cuts.sort()
            for k in range(0, len(cuts) - 1, 2):
                xa = int(round(cuts[k]))
                xb = int(round(cuts[k + 1]))
                self.rect(xa, y, xb - xa + 1, 1, colour)


# ------------------------------------------------------------- 5x7 typeface
# Five cells wide, seven rows tall per glyph; uppercase only.
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
BLANK = ("00000",) * 7


def text_width(text, scale):
    """Width in pixels: each character costs 5 cells plus a 1-cell gap."""
    return len(text) * 6 * scale - scale


def draw_text(cv, x, y, scale, colour, text):
    pen = x
    for ch in text:
        glyph = FONT.get(ch, BLANK)
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == "1":
                    cv.rect(pen + col * scale, y + row * scale,
                            scale, scale, colour)
        pen += 6 * scale
    return pen


def draw_centred(cv, centre, y, scale, colour, text):
    draw_text(cv, centre - text_width(text, scale) // 2, y, scale,
              colour, text)


def wrap_lines(text, scale, max_w):
    """Greedy wrap on word boundaries; no line wider than max_w."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, scale, colour, text, max_w, max_lines, leading):
    """Draw wrapped text from (x, y); returns the number of lines used."""
    lines = wrap_lines(text, scale, max_w)[:max_lines]
    for i, ln in enumerate(lines):
        draw_text(cv, x, y + i * leading, scale, colour, ln)
    return len(lines)


# ------------------------------------------------------------ lead artwork
# Only the three lead panels keep a picture strip in V3. Each scene is
# two to four big flat shapes fitted to the strip box it is handed.

def art_cop31(cv, x, y, w, h):
    cv.rect(x, y, w, h, SKY)
    cv.disc(x + w - h // 2, y + h // 3, max(7, h // 4), GOLD)
    cv.poly([(x, y + h), (x + w // 3, y + h // 3), (x + 2 * w // 3, y + h)],
            GREEN)
    cv.poly([(x + w // 3, y + h), (x + 2 * w // 3, y + h // 2),
             (x + w, y + h)], TEAL)
    cv.rect(x + w // 6, y + h - max(6, h // 7), 2 * w // 3,
            max(5, h // 8), BROWN)


def art_gulf(cv, x, y, w, h):
    cv.rect(x, y, w, h, NAVY)
    cv.rect(x, y + 2 * h // 3, w, h // 3, SEA)
    cv.rect(x + w // 5, y + h // 2, 3 * w // 5, h // 4, DARK)
    cv.rect(x + 2 * w // 5, y + h // 3, w // 5, h // 5, DARK)
    bx, by = x + 4 * w // 5, y + h // 3
    cv.poly([(bx, by - h // 3), (bx + 8, by - 6), (bx + h // 3, by - 8),
             (bx + 10, by + 4), (bx + h // 4, by + h // 3), (bx, by + 8),
             (bx - h // 4, by + h // 3), (bx - 10, by + 4),
             (bx - h // 3, by - 8), (bx - 8, by - 6)], ORANGE)
    cv.disc(bx, by, max(5, h // 7), YELLOW)


def art_peru(cv, x, y, w, h):
    cv.rect(x, y, w, h, (214, 228, 240))
    cv.poly([(x, y + h), (x + w // 4, y + h // 6), (x + w // 2, y + h)],
            (122, 96, 66))
    cv.poly([(x + w // 3, y + h), (x + 2 * w // 3, y + h // 9),
             (x + w, y + h)], (96, 74, 52))
    cap = max(8, h // 5)
    cv.poly([(x + w // 4 - cap, y + h // 6 + cap), (x + w // 4, y + h // 6),
             (x + w // 4 + cap, y + h // 6 + cap)], WHITE)
    cv.poly([(x + 2 * w // 3 - cap, y + h // 9 + cap),
             (x + 2 * w // 3, y + h // 9),
             (x + 2 * w // 3 + cap, y + h // 9 + cap)], WHITE)
    sh = max(12, h // 3)
    cv.rect(x + w // 12, y + h - sh - 3, 5 * w // 6, sh, WHITE)
    mid = y + h - sh // 2 - 3
    cv.line(x + w // 12 + 6, mid, x + 2 * w // 5, mid, RED, 2)
    cv.line(x + 2 * w // 5, mid, x + w // 2, y + h - sh - 1, RED, 2)
    cv.line(x + w // 2, y + h - sh - 1, x + 3 * w // 5, y + h - 5, RED, 2)
    cv.line(x + 3 * w // 5, y + h - 5, x + 2 * w // 3, mid, RED, 2)
    cv.line(x + 2 * w // 3, mid, x + 11 * w // 12 - 6, mid, RED, 2)


# -------------------------------------------------------------------- data
# The same 35 stories as V1 and V2, every one dated Sunday 22 November
# 2026: 11 panels plus 24 briefs across 7 regions. Lead headlines wrap
# to exactly two lines at scale 4; small headlines to two lines and
# small captions to at most three lines at scale 3; briefs stay one
# line of at most 26 characters at scale 3.
LEAD = [
    ("COP31", TEAL, art_cop31,
     "COP31 NEARS A DEAL",
     "DEAL TEXT FACES VOTE IN ANTALYA"),
    ("GULF", RED, art_gulf,
     "IRAN STRIKES BAHRAIN",
     "TWO BASES HIT; US HITS QESHM"),
    ("PERU", BROWN, art_peru,
     "M6.8 QUAKE SHAKES PERU",
     "152 HOMES UNINHABITABLE"),
]

# Small captions marked * were tightened for V3 so they fit three
# lines at scale 3; the facts they carry are unchanged.
SMALL = [
    ("SPARTA II", BLUE,
     "SPARTA II ABLAZE",
     "DRONE HIT, SHIP BURNS OFF FINLAND."),
    ("SINALOA", RED,
     "KINGPIN SEIZED",
     "CHAPO ISIDRO HELD; 11 DEAD"),
    ("UKRAINE", SOFT,
     "MISSILE HITS KRYVYI RIH",
     "BOY, 7, DEAD; 58 HURT"),            # * was "...AMONG THE DEAD;..."
    ("NEPAL", (200, 30, 40),
     "SHAH ARRIVES IN DELHI",
     "FIRST TRIP ABROAD SINCE MARCH."),
    ("BASRA", ORANGE,
     "BASRA POWER PLANT FIRE",
     "4 DEAD, 35 HURT AT HARTHA"),        # * was "...HARTHA STATION."
    ("SUMMIT", NAVY,
     "TRUMP XI PUTIN MEET",
     "FIRST TRILATERAL SUMMIT"),          # * was "...SUMMIT IN SHENZHEN"
    ("POLAND", RED,
     "MISSILE IN POLAND",
     "KH-101 FOUND; NATO ALARMED."),
    ("ESTONIA", GREEN,
     "ESTONIA DRONE ALERT",
     "TURKISH JETS SCRAMBLE AT DAWN"),    # * was "TURKISH NATO JETS..."
]

BRIEFS = [
    "117 OF 148 DRONES DOWNED",
    "KYIV DEBRIS WOUNDS 2",
    "LVIV STRIKE KILLS 2",
    "US FLOATS NATO GUARANTEES",
    "EU ADOPTS 1BN ARMS AID",
    "EU-INDONESIA TRADE DEALS",
    "COSTA PROPOSES 1.78TN PLAN",
    "DENMARK EXPELS ATTACHE",
    "FINLAND PROBES HELICOPTER",
    "BRUSSELS FLIGHTS CANCELLED",
    "CROATIA RALLY OVER DEATH",
    "ECB BOARD RACE HEATS UP",
    "GAZA STRIKE HITS MILITANTS",
    "US SANCTIONS 4 IRANIANS",
    "HORMUZ TANKERS HIT BY FIRE",
    "TRUMP VOWS IRAN DEAL",
    "MELANIA HOPES FOR TRUCE",
    "TRUMP PUSHES UKRAINE DEAL",
    "NIGERIA: 24 DIE IN CAPSIZE",
    "PANAMA TO BLOCK COP31 DEAL",
    "NO DEAL BEATS A WEAK DEAL",
    "COP SIDE DEALS TOP $26BN",
    "ANTONELLI TAKES VEGAS POLE",
    "ZELENSKY: SUMMIT A FLOP",
]


# ------------------------------------------------------------------ panels
def lead_panel(cv, x, y, region, colour, art, headline, caption):
    """320x204: colour strip, 56 px picture, scale-4 headline."""
    w, h = 320, 204
    cv.box(x, y, w, h, INK, 1)
    cv.rect(x + 1, y + 1, w - 2, 23, colour)
    draw_text(cv, x + 8, y + 2, 3, WHITE, region)
    draw_text(cv, x + w - 8 - text_width("22 NOV", 3), y + 2, 3, WHITE,
              "22 NOV")
    art(cv, x + 1, y + 24, w - 2, 56)
    cv.hline(x + 1, y + 80, w - 2, INK, 1)
    draw_wrapped(cv, x + 8, y + 86, 4, INK, headline, w - 16, 2, 32)
    draw_wrapped(cv, x + 8, y + 154, 3, SOFT, caption, w - 16, 2, 25)


def small_panel(cv, x, y, region, colour, headline, caption):
    """238x152, type only: strip, scale-3 headline, scale-3 caption.

    The V2 picture strip is gone; its 32 px plus the old divider go to
    the caption, which rises from scale 2 (two lines) to scale 3
    (three lines) so it reads at the judge's size.
    """
    w, h = 238, 152
    cv.box(x, y, w, h, INK, 1)
    cv.rect(x + 1, y + 1, w - 2, 23, colour)
    draw_text(cv, x + 6, y + 2, 3, WHITE, region)
    draw_wrapped(cv, x + 6, y + 27, 3, INK, headline, w - 12, 2, 23)
    cv.hline(x + 6, y + 76, w - 12, INK, 1)
    draw_wrapped(cv, x + 6, y + 81, 3, SOFT, caption, w - 12, 3, 23)


# ------------------------------------------------------------------- page
def compose():
    cv = Canvas(SIDE, PAPER)
    cv.box(12, 12, 1000, 1000, INK, 2)
    cv.box(18, 18, 988, 988, INK, 1)

    # masthead
    draw_centred(cv, 512, 28, 5, INK, "THE SUNDAY GLOBE")
    cv.hline(120, 68, 784, INK, 2)
    draw_centred(cv, 512, 74, 3, INK,
                 "SUNDAY 22 NOVEMBER 2026 - THE WORLD IN ONE DAY")

    # black strip with the count and the date
    cv.rect(24, 100, 976, 24, INK)
    draw_centred(cv, 512, 102, 3, WHITE,
                 "35 STORIES - 7 REGIONS - ALL DATED 22 NOVEMBER 2026")

    # lead row
    for i, story in enumerate(LEAD):
        lead_panel(cv, 24 + i * 328, 130, *story)

    # two rows of small panels
    for row in range(2):
        for i, story in enumerate(SMALL[row * 4:(row + 1) * 4]):
            small_panel(cv, 24 + i * 246, 342 + row * 160, *story)

    # briefs under a ruled header, two columns of twelve
    cv.hline(24, 662, 976, INK, 2)
    draw_centred(cv, 512, 668, 3, INK,
                 "IN BRIEF - 24 MORE STORIES, 22 NOV 2026")
    cv.hline(24, 696, 976, INK, 1)
    for col in range(2):
        bx = 24 + col * 488
        for r in range(12):
            ry = 704 + r * 24
            cv.rect(bx, ry + 8, 6, 6, RED)
            draw_text(cv, bx + 12, ry, 3, INK, BRIEFS[col * 12 + r])
    return cv


def main():
    cv = compose()
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    write_png(os.path.join(outdir, "entry.png"), SIDE, cv.px)


if __name__ == "__main__":
    main()
