#!/usr/bin/env python3
"""The World Today - Monday 23 November 2026. One 1024x1024 news image.
Pure stdlib, deterministic, no network. Rendered at 2048 (2x) then averaged
down to 1024, so geometry and text rasterise in true device space.
Run: python3 main.py  ->  writes entry.png next to this file.
Format lessons (from studying the Nov 21 final + Nov 22 dev top 5):
fewer, bigger stories (44 total: 13 featured + 31 list), drawn scene panels
for the top stories, a day-in-numbers strip, a region count bar, a numbered
pin map, a certainty tag on every story, and a date-check box with press time.
"""
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024
S = 2                      # supersampling factor
DW, DH = W * S, H * S

CREAM = (247, 242, 231)
PAPER = (252, 249, 240)
INK = (17, 17, 17)
RED = (164, 31, 31)
DARKRED = (122, 18, 18)
TEAL = (18, 92, 96)
GOLD = (176, 132, 32)
BLUE = (28, 68, 128)
GREEN = (22, 110, 58)
GREY = (110, 104, 92)
LIGHT = (232, 226, 210)
SKY = (178, 210, 224)
SEA = (206, 224, 232)
LAND = (226, 205, 158)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.px = bytearray(DW * DH * 3)
        self.fill_rect(0, 0, DW, DH, CREAM)

    def _i(self, x, y):
        return (y * DW + x) * 3

    def set(self, x, y, c):
        if 0 <= x < DW and 0 <= y < DH:
            i = self._i(x, y)
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, int(x)); y0 = max(0, int(y))
        x1 = min(DW, int(x + w)); y1 = min(DH, int(y + h))
        for yy in range(y0, y1):
            base = (yy * DW + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c, t=2):
        self.fill_rect(x, y, w, t, c)
        self.fill_rect(x, y + h - t, w, t, c)
        self.fill_rect(x, y, t, h, c)
        self.fill_rect(x + w - t, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=2):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0); dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        r = t // 2
        while True:
            for a in range(-r, r + 1):
                for b in range(-r, r + 1):
                    self.set(x0 + a, y0 + b, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy; x0 += sx
            if e2 <= dx:
                err += dx; y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        cx, cy, r = int(cx), int(cy), int(r)
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d <= r * r:
                        self.set(xx, yy, c)
                else:
                    if abs(d - r * r) <= r:
                        self.set(xx, yy, c)

    def poly(self, pts, c):
        # scanline fill of a polygon given in device coords
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                for x in range(int(xs[k]), int(xs[k + 1]) + 1):
                    self.set(x, y, c)

    def downsample(self):
        out = bytearray(W * H * 3)
        for y in range(H):
            for x in range(W):
                acc = [0, 0, 0]
                for dy in range(S):
                    for dx in range(S):
                        i = ((y * S + dy) * DW + x * S + dx) * 3
                        acc[0] += self.px[i]
                        acc[1] += self.px[i + 1]
                        acc[2] += self.px[i + 2]
                o = (y * W + x) * 3
                out[o] = acc[0] // 4
                out[o + 1] = acc[1] // 4
                out[o + 2] = acc[2] // 4
        return out

def write_png(path, rgb):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + rgb[y * W * 3:(y + 1) * W * 3] for y in range(H))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# logical helpers: all layout coords are in 1024-space, scaled by S
def L(v):
    return v * S

# ---------------------------------------------------------------- 5x7 bitmap font
FONT5 = {
"A": ["01110","10001","10001","11111","10001","10001","10001"],
"B": ["11110","10001","10001","11110","10001","10001","11110"],
"C": ["01110","10001","10000","10000","10000","10001","01110"],
"D": ["11110","10001","10001","10001","10001","10001","11110"],
"E": ["11111","10000","10000","11110","10000","10000","11111"],
"F": ["11111","10000","10000","11110","10000","10000","10000"],
"G": ["01110","10001","10000","10111","10001","10001","01111"],
"H": ["10001","10001","10001","11111","10001","10001","10001"],
"I": ["01110","00100","00100","00100","00100","00100","01110"],
"J": ["00111","00010","00010","00010","00010","10010","01100"],
"K": ["10001","10010","10100","11000","10100","10010","10001"],
"L": ["10000","10000","10000","10000","10000","10000","11111"],
"M": ["10001","11011","10101","10101","10001","10001","10001"],
"N": ["10001","11001","10101","10011","10001","10001","10001"],
"O": ["01110","10001","10001","10001","10001","10001","01110"],
"P": ["11110","10001","10001","11110","10000","10000","10000"],
"Q": ["01110","10001","10001","10001","10101","10010","01101"],
"R": ["11110","10001","10001","11110","10100","10010","10001"],
"S": ["01111","10000","10000","01110","00001","00001","11110"],
"T": ["11111","00100","00100","00100","00100","00100","00100"],
"U": ["10001","10001","10001","10001","10001","10001","01110"],
"V": ["10001","10001","10001","10001","10001","01010","00100"],
"W": ["10001","10001","10001","10101","10101","10101","01010"],
"X": ["10001","10001","01010","00100","01010","10001","10001"],
"Y": ["10001","10001","01010","00100","00100","00100","00100"],
"Z": ["11111","00001","00010","00100","01000","10000","11111"],
"0": ["01110","10001","10011","10101","11001","10001","01110"],
"1": ["00100","01100","00100","00100","00100","00100","01110"],
"2": ["01110","10001","00001","00110","01000","10000","11111"],
"3": ["11110","00001","00001","01110","00001","00001","11110"],
"4": ["00010","00110","01010","10010","11111","00010","00010"],
"5": ["11111","10000","11110","00001","00001","10001","01110"],
"6": ["01110","10000","10000","11110","10001","10001","01110"],
"7": ["11111","00001","00010","00100","01000","01000","01000"],
"8": ["01110","10001","10001","01110","10001","10001","01110"],
"9": ["01110","10001","10001","01111","00001","00001","01110"],
" ": ["00000","00000","00000","00000","00000","00000","00000"],
"!": ["00100","00100","00100","00100","00100","00000","00100"],
".": ["00000","00000","00000","00000","00000","01100","01100"],
",": ["00000","00000","00000","00000","01100","00100","01000"],
"-": ["00000","00000","00000","01110","00000","00000","00000"],
"'": ["00100","00100","01000","00000","00000","00000","00000"],
"/": ["00001","00010","00010","00100","01000","01000","10000"],
":": ["00000","01100","01100","00000","01100","01100","00000"],
";": ["00000","01100","01100","00000","01100","00100","01000"],
"%": ["11001","11010","00010","00100","01000","01011","10011"],
"&": ["01100","10010","10100","01000","10101","10010","01101"],
"(": ["00010","00100","01000","01000","01000","00100","00010"],
")": ["01000","00100","00010","00010","00010","00100","01000"],
"+": ["00000","00100","00100","11111","00100","00100","00000"],
"=": ["00000","00000","11111","00000","11111","00000","00000"],
"?": ["01110","10001","00001","00110","00100","00000","00100"],
"$": ["00100","01111","10100","01110","00101","11110","00100"],
"*": ["00000","10101","01110","11111","01110","10101","00000"],
"<": ["00010","00100","01000","10000","01000","00100","00010"],
">": ["01000","00100","00010","00001","00010","00100","01000"],
"#": ["01010","01010","11111","01010","11111","01010","01010"],
}

def text_w(s, scale):
    return len(s) * 6 * scale

def draw_text(cv, x, y, s, c, scale=2):
    """Bitmap 5x7 text. x,y,scale in device px. Returns width used."""
    s = s.upper()
    cx = x
    for ch in s:
        g = FONT5.get(ch, FONT5[" "])
        for r in range(7):
            row = g[r]
            for col in range(5):
                if row[col] == "1":
                    cv.fill_rect(cx + col * scale, y + r * scale, scale, scale, c)
        cx += 6 * scale
    return cx - x

def wrap_text(s, max_chars):
    words = s.split(" ")
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ---------------------------------------------------------------- stroke display font (12x16 grid)
STROKE = {
"A": [[(0,16),(6,0),(12,16)],[(3,10),(9,10)]],
"B": [[(0,0),(0,16)],[(0,0),(8,0),(11,3),(11,6),(8,8),(0,8)],[(0,8),(8,8),(11,11),(11,13),(8,16),(0,16)]],
"C": [[(11,3),(8,0),(3,0),(0,3),(0,13),(3,16),(8,16),(11,13)]],
"D": [[(0,0),(0,16)],[(0,0),(8,0),(12,4),(12,12),(8,16),(0,16)]],
"E": [[(0,0),(0,16)],[(0,0),(11,0)],[(0,8),(8,8)],[(0,16),(11,16)]],
"F": [[(0,0),(0,16)],[(0,0),(11,0)],[(0,8),(8,8)]],
"G": [[(11,3),(8,0),(3,0),(0,3),(0,13),(3,16),(8,16),(11,13),(11,8),(6,8)]],
"H": [[(0,0),(0,16)],[(12,0),(12,16)],[(0,8),(12,8)]],
"I": [[(6,0),(6,16)],[(2,0),(10,0)],[(2,16),(10,16)]],
"J": [[(12,0),(12,13),(9,16),(4,16),(2,14)]],
"K": [[(0,0),(0,16)],[(11,0),(0,8)],[(3,7),(11,16)]],
"L": [[(0,0),(0,16)],[(0,16),(11,16)]],
"M": [[(0,16),(0,0),(6,8),(12,0),(12,16)]],
"N": [[(0,16),(0,0),(12,16),(12,0)]],
"O": [[(3,0),(9,0),(12,3),(12,13),(9,16),(3,16),(0,13),(0,3),(3,0)]],
"P": [[(0,16),(0,0)],[(0,0),(8,0),(12,4),(12,8),(8,12),(0,12)]],
"Q": [[(3,0),(9,0),(12,3),(12,13),(9,16),(3,16),(0,13),(0,3),(3,0)],[(8,11),(12,16)]],
"R": [[(0,16),(0,0)],[(0,0),(8,0),(12,4),(12,8),(8,12),(0,12)],[(4,8),(12,16)]],
"S": [[(11,3),(8,0),(3,0),(0,3),(0,6),(3,8),(9,8),(12,10),(12,13),(9,16),(3,16),(0,13)]],
"T": [[(0,0),(12,0)],[(6,0),(6,16)]],
"U": [[(0,0),(0,12),(3,16),(9,16),(12,12),(12,0)]],
"V": [[(0,0),(6,16),(12,0)]],
"W": [[(0,0),(3,16),(6,8),(9,16),(12,0)]],
"X": [[(0,0),(12,16)],[(12,0),(0,16)]],
"Y": [[(0,0),(6,8)],[(12,0),(6,8)],[(6,8),(6,16)]],
"Z": [[(0,0),(12,0),(0,16),(12,16)]],
"0": [[(3,0),(9,0),(12,3),(12,13),(9,16),(3,16),(0,13),(0,3),(3,0)]],
"1": [[(6,0),(6,16)],[(3,3),(6,0)],[(2,16),(10,16)]],
"2": [[(0,3),(3,0),(9,0),(12,3),(12,7),(0,16),(12,16)]],
"3": [[(2,0),(9,0),(12,3),(12,6),(9,8),(2,8)],[(2,8),(9,8),(12,11),(12,13),(9,16),(2,16),(0,14)]],
"4": [[(8,0),(8,16)],[(0,11),(10,11)],[(8,0),(0,11)]],
"5": [[(11,0),(0,0),(0,7),(9,7),(12,10),(12,13),(9,16),(0,16)]],
"6": [[(11,2),(8,0),(3,0),(0,3),(0,13),(3,16),(9,16),(12,13),(12,10),(9,7),(3,7),(0,10)]],
"7": [[(0,0),(12,0),(4,16)]],
"8": [[(3,0),(9,0),(12,3),(12,6),(9,8),(3,8),(0,6),(0,3),(3,0)],[(3,8),(9,8),(12,11),(12,13),(9,16),(3,16),(0,13),(0,11),(3,8)]],
"9": [[(2,0),(10,0),(12,2),(12,8),(10,10),(2,10),(0,8),(0,2),(2,0)],[(12,8),(12,16)]],
" ": [],
"-": [[(1,8),(11,8)]],
":": [],
".": [],
"'": [[(6,0),(4,5)]],
"/": [[(2,16),(10,0)]],
"%": [[(3,3),(5,3),(5,5),(3,5),(3,3)],[(8,11),(10,11),(10,13),(8,13),(8,11)],[(11,1),(1,15)]],
}

def draw_stroke(cv, x, y, s, c, scale=5, thick=4, adv=15):
    """Stroke display text. x,y,scale in device px. scale = px per grid unit."""
    s = s.upper()
    cx = x
    for ch in s:
        if ch == ":":
            cv.fill_rect(cx + 5 * scale, y + 5 * scale, 2 * scale, 2 * scale, c)
            cv.fill_rect(cx + 5 * scale, y + 11 * scale, 2 * scale, 2 * scale, c)
        elif ch == ".":
            cv.fill_rect(cx + 5 * scale, y + 14 * scale, 2 * scale, 2 * scale, c)
        else:
            for stroke in STROKE.get(ch, []):
                for a, b in zip(stroke, stroke[1:]):
                    cv.line(cx + a[0] * scale, y + a[1] * scale,
                            cx + b[0] * scale, y + b[1] * scale, c, thick)
        cx += adv * scale
    return cx - x

def stroke_w(s, scale=5, adv=15):
    return len(s) * adv * scale

# ---------------------------------------------------------------- data
# Every story happened or was first reported on Mon 23 Nov 2026 (UTC) unless
# its card carries a date in brackets. Sources are named per story.
# tag: CONFIRMED = 2+ outlets / official record; OFFICIAL = on the record;
# REPORTED = one outlet; CLAIM = one side's claim, labelled as such.

FEATURED = [
 dict(n=1, region="WORLD", place="ANTALYA, TURKIYE", tag="CONFIRMED",
      scene="hall", big="44H",
      head="COP31 COLLAPSES WITH NO DEAL",
      deck="After 44 hours of overtime, president Kurum says there is no agreement on the text. A just-transition deal passes; the rest goes to COP32 in Addis Ababa in 2027.",
      src="REUTERS - AP - AFP", lat=36.9, lon=30.7),
 dict(n=2, region="EUROPE", place="DYMER, KYIV REGION", tag="CONFIRMED",
      scene="building", big="11",
      head="DYMER TOLL RISES TO 11 AS RESCUERS DIG ON",
      deck="Russian drone hits a five-storey block on Sunday night. A boy of seven is pulled out alive after 14 hours; the region marks a day of mourning on Monday.",
      src="REUTERS - AFP - DPA", lat=50.8, lon=30.3),
 dict(n=3, region="ASIA", place="CIKANDE, INDONESIA", tag="CONFIRMED",
      scene="factory", big="24",
      head="FACTORY FIRE TOLL NOW 24; ABOUT 30 STILL MISSING",
      deck="Blaze at the PT Fonusa Agung Mulia candy plant on Saturday evening. 29 people are safe, five in hospital; the cause is still being probed.",
      src="REUTERS", lat=-6.2, lon=106.3),
 dict(n=4, region="MIDDLE EAST", place="TEHRAN - WASHINGTON", tag="CONFIRMED",
      scene="ship", big="14+",
      head="IRAN VOWS TO FIGHT US BLOCKADE WITH ALL TOOLS",
      deck="Baghaei speaks on Monday as Trump dares Tehran to test the blockade. 14-plus tankers wait off Kharg Island; 43m barrels of oil are stranded.",
      src="REUTERS", lat=35.7, lon=51.4),
 dict(n=5, region="AMERICAS", place="WASHINGTON, USA", tag="CONFIRMED",
      scene="capitol", big="258",
      head="DEMOCRATS REACH 258 HOUSE SEATS",
      deck="Hubbard beats Foxx in North Carolina by about 330 votes after a recount: the biggest Democratic House majority since 1992. [Called Sun 22 Nov]",
      src="REUTERS - AP", lat=38.9, lon=-77.0),
 dict(n=6, region="ASIA", place="TOKYO, JAPAN", tag="CONFIRMED",
      scene="market", big="-5.1%",
      head="NIKKEI DIVES 5.06% AS AI SELL-OFF SPREADS",
      deck="Tokyo leads the Asia rout on Monday. US futures bounce after last week's wipeout; policymakers in Seoul and Taipei watch the slide closely.",
      src="REUTERS", lat=35.7, lon=139.7),
 dict(n=7, region="ASIA", place="SEOUL, SOUTH KOREA", tag="CONFIRMED",
      scene="desk", big="QUIT",
      head="SOUTH KOREA MINISTER QUITS OVER AI EXAM CHAOS",
      deck="Choi Kyo-jin resigns, taking blame for last-minute anti-cheating rules before the college entrance exam held last week.",
      src="REUTERS", lat=37.6, lon=127.0),
 dict(n=8, region="EUROPE", place="BERLIN, GERMANY", tag="REPORTED",
      scene="school", big="450",
      head="BOMB THREATS HIT ABOUT 450 GERMAN SCHOOLS",
      deck="Threat emails reach schools on Monday morning, Bild reports, citing police in Freiburg. No explosives are reported found.",
      src="REUTERS - BILD", lat=52.5, lon=13.4),
 dict(n=9, region="ASIA", place="DHAKA, BANGLADESH", tag="CONFIRMED",
      scene="court", big="DEC",
      head="BANGLADESH VOWS TO ARREST HASINA IF SHE RETURNS",
      deck="Minister tells Reuters Dhaka seeks her extradition from India as her planned December return fuels tension and street violence.",
      src="REUTERS", lat=23.8, lon=90.4),
 dict(n=10, region="MIDDLE EAST", place="WEST BANK", tag="CONFIRMED",
      scene="fire", big="4",
      head="EISENKOT CALLS SETTLER ARSON JEWISH TERRORISM",
      deck="Settlers burn cars in four towns overnight on Saturday. The prime minister-elect says the attacks damage Israel's security.",
      src="REUTERS - WASHINGTON POST", lat=31.9, lon=35.2),
 dict(n=11, region="AFRICA", place="KHARTOUM, SUDAN", tag="REPORTED",
      scene="drone", big="5",
      head="DRONE ATTACKS KILL FIVE CHILDREN IN SUDAN",
      deck="Strikes hit Khartoum and Omdurman as the war grinds on, with children paying the heaviest price in the capital's fighting.",
      src="ONE TURN", lat=15.6, lon=32.5),
 dict(n=12, region="OCEANIA", place="WELLINGTON, NZ", tag="CONFIRMED",
      scene="cricket", big="720/9",
      head="INDIA 720/9, BUT NEW ZEALAND HOLD ON FOR DRAW",
      deck="Mitchell 49 not out and Phillips 26 not out bat out day five. The first Test is drawn at the Basin Reserve.",
      src="AFP - IANS", lat=-41.3, lon=174.8),
 dict(n=13, region="MIDDLE EAST", place="GAZA CITY, GAZA", tag="REPORTED",
      scene="truck", big="3",
      head="ISRAELI FIRE KILLS THREE AT GAZA TRUCK",
      deck="Witnesses say the truck carried food and World Central Kitchen papers; the charity says the vehicle was not its own. [Sat 21 Nov]",
      src="REUTERS", lat=31.5, lon=34.5),
]

LISTED = [
 (14, "France: private sector PMI 46.2; factory output weakest since Feb 2025", "REUTERS"),
 (15, "Russia's sports comeback hits a European wall", "REUTERS"),
 (16, "Armenia launches US-backed transport project on Iran border", "FDD"),
 (17, "Crimea bridge superstructure listing after drone and missile barrage", "WSJ"),
 (18, "Ukraine confirms it hit a Russian warship at a Libyan port", "JUST SECURITY"),
 (19, "Russian cargo ship hit in Baltic [Sat]; Finland PM: war spills over", "JUST SECURITY"),
 (20, "Houthis claim strike on Saudi refinery; Saudi hits Hodeida", "ONE TURN"),
 (21, "Saudi downs drone to Riyadh and missile to west; Sanaa fuel station hit, six hurt [Sun]", "360LIVE"),
 (22, "South Sudan paramilitary attack kills at least 24 civilians", "ONE TURN"),
 (23, "Five EU states accept deportation centres in Rwanda", "ONE TURN"),
 (24, "Thousands rally in Istanbul against media takeover", "ONE TURN"),
 (25, "Colombia asks X to suspend ex-president Petro's account", "ONE TURN"),
 (26, "Lewis Pugh swims the length of the Strait of Hormuz in three days", "ONE TURN"),
 (27, "Nigeria moves to end jail for attempted suicide", "ONE TURN"),
 (28, "Robot submarine finds volcanic activity in the Mariana Trench", "ONE TURN"),
 (29, "Nepal set for first payout from UN Loss and Damage Fund", "ONE TURN"),
 (30, "Otters return to a once-polluted Kuala Lumpur river", "ONE TURN"),
 (31, "Zipline hires Uber executive to lead Africa expansion", "ONE TURN"),
 (32, "Miley Cyrus weds drummer Maxx Morando in California", "REUTERS"),
 (33, "Trump hosts gala for meme-coin investors as token hits record low", "REUTERS"),
 (34, "US Army uses emergency powers to detonate lead in Iowa, bypassing court", "REUTERS"),
 (35, "Bahrain demands UN action after Iran attacks civilian facility", "ARAB NEWS"),
 (36, "Lebanon army arrests three with 264 kg of explosives", "ARAB NEWS"),
 (37, "Syria and EU in talks to normalise ties after 15-year break", "360LIVE"),
 (38, "Australia sanctions settlers over West Bank expansion", "360LIVE"),
 (39, "Vyshneve supermarket strike kills three, wounds 15, incl. three children", "AFP - REUTERS"),
 (40, "Bila Tserkva strike kills one, sets home ablaze; power station hit in Dnipropetrovsk", "REUTERS"),
 (41, "Moscow signals new trilateral talks with Kyiv and US soon", "SANA"),
 (42, "Alcaraz wins first ATP Finals, beating Zverev 6-2, 7-6 [Sun 22 Nov]", "GUARDIAN"),
 (43, "Pakistan A beat India A by 48 runs; Tilak Varma 100 off 49 [Sun]", "IANS"),
 (44, "Afghanistan A beat Hong Kong by seven wickets in Doha", "THE WORLD OPINION"),
]

NUMBERS = [
 ("44H", "COP31 OVERTIME"),
 ("24", "CIKANDE FIRE DEAD"),
 ("11", "DYMER, KYIV REGION"),
 ("258", "DEMOCRATIC HOUSE SEATS"),
 ("-5.06%", "NIKKEI ON MONDAY"),
 ("720/9", "INDIA TEST TOTAL IN NZ"),
]

TIMELINE = [
 ("00:20", "Seoul minister quits"),
 ("02:03", "Dymer toll rises to nine"),
 ("07:20", "Dymer toll reaches 11"),
 ("08:18", "France PMI 46.2"),
 ("10:43", "German school threats"),
 ("13:30", "Wires read to here"),
]

REGIONS = ["EUROPE", "MIDDLE EAST", "ASIA", "AMERICAS", "AFRICA", "OCEANIA", "WORLD"]
REGION_COLORS = {"EUROPE": BLUE, "MIDDLE EAST": RED, "ASIA": GOLD,
                 "AMERICAS": TEAL, "AFRICA": (150, 90, 20), "OCEANIA": GREEN,
                 "WORLD": (90, 90, 90)}

DATECHECK = ("LEFT OUT ON PURPOSE - HAPPENED ON ANOTHER DAY: GTA VI $3.79BN DAY-ONE RETAIL SALES, "
             "32.5M PRE-SOLD (ROCKSTAR / TAKE-TWO, FRI 20 NOV) - THE $1.84BN FIGURE WAS ONLY A SENSOR "
             "TOWER MORNING ESTIMATE; 'EL CHAPO ISIDRO' CAPTURED (FRI 21 NOV); COP31 FINAL TEXT LANDS AT "
             "DAWN (SUN 22 NOV); HONG KONG POLLS, 98.37% TURNOUT (SUN); VERSTAPPEN WINS LAS VEGAS GP (SUN); "
             "BEPICOLOMBO ENTERS MERCURY ORBIT (SAT 21 NOV). NOT YET: COP32 IN ADDIS ABABA, NOV 2027; "
             "US PCE INFLATION INDEX, WED 25 NOV.")

FOOTER = ("SOURCES: REUTERS, AP, AFP, BBC, AL JAZEERA, GUARDIAN, DPA, SCMP, ARAB NEWS, JUST SECURITY, FDD. "
          "EVERY STORY HAPPENED OR WAS FIRST REPORTED ON MON 23 NOV 2026 (UTC) UNLESS DATED IN ITS CARD. "
          "SCENES DRAWN IN CODE; NO PHOTOGRAPHS.")

# simplified continent outlines (lon, lat), equirectangular
CONTINENTS = [
 # North America
 [(-168,66),(-158,58),(-140,60),(-130,54),(-125,49),(-124,42),(-120,34),(-114,29),
  (-110,24),(-105,20),(-97,16),(-94,17),(-87,13),(-83,9),(-79,9),(-81,13),(-84,16),
  (-87,21),(-90,21),(-91,19),(-97,26),(-93,30),(-89,30),(-84,30),(-81,25),(-80,32),
  (-76,35),(-74,40),(-70,42),(-68,44),(-65,44),(-60,46),(-65,50),(-60,52),(-64,58),
  (-68,58),(-78,62),(-85,66),(-92,66),(-95,69),(-110,68),(-125,70),(-140,70),
  (-155,71),(-165,68)],
 # Greenland
 [(-58,64),(-52,60),(-43,60),(-40,64),(-32,68),(-22,70),(-25,76),(-35,77),(-50,76),
  (-58,74),(-62,70)],
 # South America
 [(-79,9),(-77,4),(-80,-3),(-81,-6),(-77,-12),(-72,-18),(-70,-23),(-70,-30),
  (-72,-37),(-73,-44),(-74,-50),(-70,-54),(-66,-55),(-68,-50),(-65,-45),(-62,-40),
  (-58,-35),(-52,-32),(-48,-28),(-41,-23),(-39,-17),(-35,-9),(-35,-6),(-40,-3),
  (-44,-2),(-50,0),(-52,4),(-55,6),(-60,8),(-62,10),(-68,11),(-72,12),(-76,10)],
 # Africa
 [(-17,15),(-17,21),(-15,27),(-10,31),(-5,35),(0,36),(10,37),(11,34),(20,32),
  (30,31),(32,31),(35,28),(37,22),(39,18),(41,11),(43,11),(48,11),(51,12),
  (44,5),(41,-2),(40,-10),(36,-18),(33,-26),(28,-33),(20,-35),(17,-32),(14,-22),
  (12,-18),(13,-12),(12,-6),(9,4),(4,6),(-8,5),(-13,8),(-17,12)],
 # Eurasia
 [(-10,36),(-9,38),(-9,43),(-2,44),(-2,48),(-5,48),(-1,50),(2,51),(5,53),(8,55),
  (8,57),(11,58),(18,56),(21,55),(24,58),(21,60),(25,62),(30,65),(35,66),(40,68),
  (45,68),(55,69),(65,69),(75,72),(85,74),(95,76),(105,77),(115,73),(125,72),
  (135,72),(145,72),(158,69),(170,66),(178,65),(178,62),(170,60),(162,56),
  (158,52),(150,59),(142,54),(141,45),(140,40),(135,35),(130,33),(127,35),
  (122,38),(120,32),(122,28),(118,25),(110,20),(108,12),(105,9),(103,2),
  (100,6),(98,10),(95,16),(92,21),(89,22),(86,20),(80,13),(77,8),(75,15),
  (73,20),(70,23),(66,25),(62,25),(58,26),(56,27),(52,28),(50,29),(48,30),
  (44,29),(40,28),(36,36),(33,36),(30,36),(27,37),(23,36),(20,40),(19,42),
  (15,44),(12,44),(8,44),(3,42),(0,39),(-2,37),(-6,36)],
 # Australia
 [(114,-22),(114,-30),(115,-35),(118,-35),(124,-33),(129,-32),(132,-32),(135,-35),
  (138,-35),(140,-38),(145,-38),(150,-37),(153,-32),(153,-27),(150,-23),(146,-19),
  (142,-15),(142,-11),(137,-12),(135,-15),(132,-12),(130,-13),(126,-14),(122,-17),
  (118,-20)],
 # SE Asia islands (rough)
 [(95,5),(98,8),(100,7),(102,2),(104,-2),(106,-6),(110,-7),(114,-8),(118,-9),
  (120,-10),(119,-5),(117,-2),(114,2),(110,1),(106,2),(103,1),(100,5)],
 [(131,-1),(136,-2),(138,-4),(141,-6),(141,-8),(136,-8),(132,-4),(130,-2)],
 [(120,18),(122,18),(122,14),(121,14),(120,16),(119,18)],
 [(126,7),(126,10),(124,12),(122,16),(121,18),(122,18)],
]

# ---------------------------------------------------------------- scenes
def draw_scene(cv, x, y, w, h, kind, big):
    """Small drawn illustration inside a featured card. Device coords."""
    cv.fill_rect(x, y, w, h, SKY)
    cx, cy = x + w // 2, y + h // 2
    if kind == "hall":
        cv.fill_rect(x, y + h * 3 // 5, w, h * 2 // 5, (120, 90, 60))
        cv.fill_rect(x + w // 6, y + h // 5, w * 2 // 3, h // 2, (200, 180, 140))
        for i in range(5):
            px = x + w // 8 + i * w // 6
            cv.circle(px, y + h // 2, h // 10, (60, 60, 80))
        cv.circle(x + w * 4 // 5, y + h // 4, h // 8, GOLD)
    elif kind == "building":
        cv.fill_rect(x + w // 4, y + h // 6, w // 2, h * 2 // 3, (90, 85, 95))
        cv.fill_rect(x + w // 4, y + h // 6, w // 2, h // 8, (60, 55, 60))
        for r in range(3):
            for c in range(4):
                cv.fill_rect(x + w // 4 + 8 + c * w // 6, y + h // 3 + r * h // 5,
                             w // 12, h // 10, (240, 210, 120))
        cv.circle(x + w * 3 // 4, y + h // 5, h // 7, (150, 150, 150))
        cv.line(x + w // 2, y + h // 8, x + w * 3 // 4, y + h // 3, (200, 60, 40), 3)
    elif kind == "factory":
        cv.fill_rect(x, y + h // 2, w, h // 2, (70, 60, 70))
        cv.fill_rect(x + w // 6, y + h // 4, w // 5, h // 2, (150, 60, 50))
        cv.fill_rect(x + w // 2, y + h // 3, w // 3, h // 3, (110, 110, 110))
        for i, fx in enumerate((w // 4, w // 2, w * 3 // 4)):
            cv.poly([(x + fx - 8, y + h // 3), (x + fx, y + h // 8 - i * 6),
                     (x + fx + 8, y + h // 3)], (240, 140, 30))
        cv.circle(x + w // 5, y + h // 4, h // 8, (120, 120, 120))
    elif kind == "ship":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (30, 70, 110))
        cv.fill_rect(x + w // 5, y + h // 3, w * 3 // 5, h // 4, (120, 60, 40))
        cv.fill_rect(x + w // 3, y + h // 6, w // 8, h // 4, (80, 80, 80))
        cv.fill_rect(x + w * 3 // 5, y + h // 4, w // 8, h // 5, (80, 80, 80))
        cv.circle(x + w // 4, y + h // 5, h // 10, (230, 220, 180))
    elif kind == "capitol":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (100, 110, 90))
        cv.fill_rect(x + w // 4, y + h // 3, w // 2, h // 3, (235, 235, 225))
        cv.circle(x + w // 2, y + h // 3, w // 11, (235, 235, 225))
        for i in range(4):
            cv.fill_rect(x + w // 4 + i * w // 9, y + h // 2, w // 18, h // 4, (180, 180, 170))
    elif kind == "market":
        pts = [(x + w // 8, y + h * 4 // 5), (x + w // 4, y + h // 3),
               (x + w // 2, y + h // 2), (x + w * 3 // 4, y + h // 4),
               (x + w * 7 // 8, y + h * 3 // 5)]
        for a, b in zip(pts, pts[1:]):
            cv.line(a[0], a[1], b[0], b[1], RED, 4)
        for p in pts[1:]:
            cv.circle(p[0], p[1], 5, RED)
        cv.fill_rect(x, y + h * 4 // 5, w, 3, INK)
    elif kind == "desk":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (90, 70, 50))
        cv.fill_rect(x + w // 6, y + h // 4, w * 2 // 3, h // 3, (250, 250, 245))
        cv.line(x + w // 4, y + h // 3, x + w * 3 // 4, y + h // 3, INK, 2)
        cv.line(x + w // 4, y + h // 2, x + w * 2 // 3, y + h // 2, INK, 2)
        cv.circle(x + w * 5 // 6, y + h // 5, h // 9, RED)
    elif kind == "school":
        cv.fill_rect(x + w // 5, y + h // 3, w * 3 // 5, h // 2, (200, 170, 120))
        cv.poly([(x + w // 6, y + h // 3), (x + w // 2, y + h // 8),
                 (x + w * 5 // 6, y + h // 3)], DARKRED)
        cv.fill_rect(x + w // 2 - 6, y + h // 2, 12, h // 3, (90, 60, 40))
        cv.circle(x + w * 4 // 5, y + h // 5, h // 9, GOLD)
    elif kind == "court":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (110, 100, 80))
        for i in range(3):
            cv.fill_rect(x + w // 6 + i * w // 4, y + h // 4, w // 14, h // 2, (240, 240, 230))
        cv.fill_rect(x + w // 8, y + h // 6, w * 3 // 4, h // 10, (240, 240, 230))
    elif kind == "fire":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (60, 55, 60))
        for i, fx in enumerate((w // 3, w // 2, w * 2 // 3)):
            cv.poly([(x + fx - 10, y + h * 2 // 3), (x + fx, y + h // 4 - i * 8),
                     (x + fx + 10, y + h * 2 // 3)], (240, 120, 20))
        cv.fill_rect(x + w // 5, y + h // 2, w // 6, h // 5, (30, 30, 30))
        cv.fill_rect(x + w * 3 // 5, y + h // 2, w // 6, h // 5, (30, 30, 30))
    elif kind == "drone":
        cv.fill_rect(x, y + h // 2, w, h // 2, (140, 130, 100))
        cv.fill_rect(x + w // 3, y + h // 4, w // 3, h // 6, (60, 60, 70))
        for dx in (-w // 4, w // 4):
            cv.line(x + w // 2 + dx, y + h // 4, x + w // 2 + dx - 14, y + h // 6, INK, 3)
            cv.line(x + w // 2 + dx, y + h // 4, x + w // 2 + dx + 14, y + h // 6, INK, 3)
        cv.circle(x + w // 2, y + h // 3, 5, RED)
    elif kind == "cricket":
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (60, 140, 70))
        cv.fill_rect(x + w // 6, y + h // 5, w * 2 // 3, h // 2, (210, 190, 150))
        cv.line(x + w // 4, y + h // 3, x + w * 3 // 4, y + h // 3, (150, 100, 50), 6)
        cv.circle(x + w * 3 // 4, y + h // 4, 7, RED)
        cv.fill_rect(x + w // 2, y + h // 2, 4, h // 4, (180, 140, 80))
    else:  # truck
        cv.fill_rect(x, y + h * 2 // 3, w, h // 3, (90, 90, 90))
        cv.fill_rect(x + w // 6, y + h // 3, w // 2, h // 3, (240, 240, 235))
        cv.fill_rect(x + w * 2 // 3, y + h // 2, w // 5, h // 5, (180, 60, 50))
        cv.circle(x + w // 3, y + h * 3 // 4, h // 9, INK)
        cv.circle(x + w * 3 // 4, y + h * 3 // 4, h // 9, INK)
    # big-number badge, bottom-right of the scene
    bw = (len(big) + 1) * 6 * 2 + 8
    bx, by = x + w - bw - 6, y + h - 20
    cv.fill_rect(bx, by, bw, 18, RED)
    draw_text(cv, bx + 5, by + 2, big, WHITE, 2)

# ---------------------------------------------------------------- layout
TAG_COLORS = {"CONFIRMED": GREEN, "OFFICIAL": BLUE, "REPORTED": GOLD, "CLAIM": RED}
LISTED_REGIONS = ["EUROPE", "EUROPE", "ASIA", "EUROPE", "EUROPE", "EUROPE",
                  "MIDDLE EAST", "MIDDLE EAST", "AFRICA", "AFRICA", "EUROPE",
                  "AMERICAS", "MIDDLE EAST", "AFRICA", "WORLD", "ASIA", "ASIA",
                  "AFRICA", "AMERICAS", "AMERICAS", "AMERICAS", "MIDDLE EAST",
                  "MIDDLE EAST", "MIDDLE EAST", "OCEANIA", "EUROPE", "EUROPE",
                  "EUROPE", "EUROPE", "ASIA", "ASIA"]

def region_counts():
    counts = {r: 0 for r in REGIONS}
    for f in FEATURED:
        counts[f["region"]] += 1
    for r in LISTED_REGIONS:
        counts[r] += 1
    return counts

def tag_chip(cv, x, y, tag):
    # x,y logical; chip height 11 logical, text scale 2 (device)
    w = len(tag) * 6 + 8
    cv.fill_rect(L(x), L(y), L(w), L(11), TAG_COLORS[tag])
    draw_text(cv, L(x) + 8, L(y) + 2, tag, WHITE, 2)
    return w

def head_lines(head, max_chars, max_lines):
    lines = wrap_text(head, max_chars)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max_chars - 3].rstrip() + "..."
    return lines

def featured_card(cv, f, x, y, w, h, big):
    cv.fill_rect(L(x), L(y), L(w), L(h), PAPER)
    cv.rect(L(x), L(y), L(w), L(h), INK, 2)
    if big:
        scene_h, head_scale, head_mc, deck_mc = 76, 3, 34, 50
        head_lh, deck_lh = 24, 9
        place_y, head_y = y + 84, y + 100
        deck_y = head_y + 2 * head_lh
        src_y = y + h - 11
        max_head, max_deck = 2, 4
    else:
        scene_h, head_scale, head_mc, deck_mc = 40, 2, 30, 32
        head_lh, deck_lh = 9, 9
        place_y, head_y = y + 46, y + 58
        deck_y = head_y + 2 * head_lh
        src_y = y + h - 11
        max_head, max_deck = 2, 3
    draw_scene(cv, L(x) + 8, L(y) + 8, L(w) - 16, L(scene_h), f["scene"], f["big"])
    # place + tag row
    draw_text(cv, L(x) + 8, L(place_y) + 2, f["place"], RED, 2)
    tag_chip(cv, x + w - (len(f["tag"]) * 6 + 8) - 8, place_y, f["tag"])
    # headline
    lines = head_lines(f["head"], head_mc, max_head)
    yy = head_y
    for ln in lines:
        draw_text(cv, L(x) + 8, L(yy), ln, INK, head_scale)
        yy += head_lh
    # deck
    dlines = wrap_text(f["deck"], deck_mc)
    if len(dlines) > max_deck:
        dlines = dlines[:max_deck]
        dlines[-1] = dlines[-1][: deck_mc - 3].rstrip() + "..."
    yy = deck_y
    for ln in dlines:
        draw_text(cv, L(x) + 8, L(yy), ln, INK, 2)
        yy += deck_lh
    draw_text(cv, L(x) + 8, L(src_y), f["src"], GREY, 2)
    # number badge, top-left over the scene
    bw = 22 if f["n"] < 10 else 28
    cv.fill_rect(L(x) + 8, L(y) + 8, L(bw), L(14), INK)
    draw_text(cv, L(x) + 12, L(y) + 11, str(f["n"]), WHITE, 2)

def draw_map(cv, x, y, w, h):
    cv.fill_rect(L(x), L(y), L(w), L(h), SEA)
    cv.rect(L(x), L(y), L(w), L(h), INK, 2)
    px, py, pw, ph = x + 4, y + 4, w - 8, h - 8
    def proj(lon, lat):
        return (L(px + (lon + 180) / 360.0 * pw),
                L(py + (84 - lat) / 140.0 * ph))
    for cont in CONTINENTS:
        cv.poly([proj(lon, lat) for lon, lat in cont], LAND)
    # pins for the 13 featured stories
    offsets = {13: (4, -4)}
    for f in FEATURED:
        dlat, dlon = offsets.get(f["n"], (0, 0))
        cx, cy = proj(f["lon"] + dlon, f["lat"] + dlat)
        if (f["n"], dlat, dlon) != (f["n"], 0, 0):
            tx, ty = proj(f["lon"], f["lat"])
            cv.line(cx, cy, tx, ty, INK, 2)
            cv.circle(tx, ty, 4, RED)
        cv.circle(cx, cy, 11, RED)
        cv.circle(cx, cy, 11, WHITE, fill=False)
        num = str(f["n"])
        draw_text(cv, cx - len(num) * 3, cy - 4, num, WHITE, 1)

def render():
    cv = Canvas()
    cv.rect(L(6), L(6), L(1012), L(1012), INK, 4)
    # kicker
    draw_text(cv, L(16), L(14), "THE WORLD IN ONE DAY", RED, 2)
    right = "44 STORIES - 7 REGIONS - EVERY ONE DATED"
    draw_text(cv, L(1008) - text_w(right, 2), L(14), right, INK, 2)
    # masthead
    title = "MONDAY 23 NOVEMBER 2026"
    tw = stroke_w(title, 5, 15)
    draw_stroke(cv, (DW - tw) // 2, L(30), title, INK, 5, 4, 15)
    cv.fill_rect(L(16), L(76), L(992), 4, INK)
    sub = "COP31 COLLAPSES WITH NO DEAL - DYMER TOLL 11 - CIKANDE FIRE 24 - DEMOCRATS 258"
    draw_text(cv, (DW - text_w(sub, 2)) // 2, L(82), sub, DARKRED, 2)
    # day in numbers
    cell = 992 // 6
    for i, (num, label) in enumerate(NUMBERS):
        cx = 16 + i * cell
        if i:
            cv.fill_rect(L(cx), L(96), 2, L(34), GREY)
        nw = stroke_w(num, 3, 15)
        draw_stroke(cv, L(cx) + (L(cell) - nw) // 2, L(94), num, RED, 3, 3, 15)
        lab = wrap_text(label, 26)
        ly = 124
        for ln in lab:
            draw_text(cv, L(cx) + (L(cell) - text_w(ln, 2)) // 2, L(ly), ln, INK, 2)
            ly += 9
    cv.fill_rect(L(16), L(134), L(992), 3, INK)
    # region bar
    counts = region_counts()
    assert sum(counts.values()) == 44
    rx = 16.0
    for r in REGIONS:
        seg = 992.0 * counts[r] / 44.0
        cv.fill_rect(L(int(rx)), L(139), L(int(seg)) - 2, L(14), REGION_COLORS[r])
        lab = "%s %d" % (r, counts[r]) if seg > 110 else str(counts[r])
        draw_text(cv, L(int(rx)) + (L(int(seg)) - text_w(lab, 2)) // 2, L(141), lab, WHITE, 2)
        rx += seg
    # timeline
    cv.fill_rect(L(16), L(158), L(86), L(13), INK)
    draw_text(cv, L(16), L(160), "THE DAY IN UTC", WHITE, 2)
    tl_x0, tl_x1 = 132, 1000
    cv.line(L(tl_x0), L(170), L(tl_x1), L(170), INK, 2)
    for i, (tm, lab) in enumerate(TIMELINE):
        tx = tl_x0 + i * (tl_x1 - tl_x0 - 60) // 5
        cv.circle(L(tx), L(170), 6, RED)
        draw_text(cv, L(tx) - text_w(tm, 2) // 2, L(158), tm, RED, 2)
        draw_text(cv, L(tx) - text_w(lab, 2) // 2, L(174), lab, INK, 2)
    # featured: top 3, then two rows of 5
    top_y, top_h = 184, 196
    tw3 = (992 - 16) // 3
    for i, f in enumerate(FEATURED[:3]):
        featured_card(cv, f, 16 + i * (tw3 + 8), top_y, tw3, top_h, True)
    row_w = (992 - 32) // 5
    for r in range(2):
        for c in range(5):
            f = FEATURED[3 + r * 5 + c]
            featured_card(cv, f, 16 + c * (row_w + 8), 386 + r * 142, row_w, 138, False)
    # also-on header
    draw_text(cv, L(16), L(674), "ALSO ON MONDAY 23 NOVEMBER - 31 MORE STORIES", RED, 2)
    legend = "HOW SURE: CONFIRMED 2+ OUTLETS - OFFICIAL ON RECORD - REPORTED ONE OUTLET"
    draw_text(cv, L(1008) - text_w(legend, 2), L(674), legend, GREY, 2)
    cv.fill_rect(L(16), L(686), L(992), 3, INK)
    # listed stories, two columns, one line each
    for col in range(2):
        items = LISTED[col * 16:(col + 1) * 16]
        lx = 16 + col * 496
        for i, (n, txt, src) in enumerate(items):
            yy = 694 + i * 10
            draw_text(cv, L(lx), L(yy), "%d" % n, RED, 2)
            sw = text_w(src, 2)
            max_txt = (478 - 26 - sw // 2) // 6
            if len(txt) > max_txt:
                txt = txt[: max_txt - 3].rstrip() + "..."
            draw_text(cv, L(lx) + L(22), L(yy), txt, INK, 2)
            draw_text(cv, L(lx) + L(478) - sw, L(yy), src, GREY, 2)
    # map + date check
    draw_text(cv, L(16), L(846), "WHERE IT HAPPENED", RED, 2)
    draw_map(cv, 16, 858, 330, 142)
    dx, dy, dw, dh = 354, 858, 654, 142
    cv.fill_rect(L(dx), L(dy), L(dw), L(dh), PAPER)
    cv.rect(L(dx), L(dy), L(dw), L(dh), RED, 4)
    draw_text(cv, L(dx) + 16, L(dy) + 10, "DATE CHECK", WHITE, 2)
    cv.fill_rect(L(dx) + 8, L(dy) + 6, L(86), L(15), RED)
    draw_text(cv, L(dx) + 16, L(dy) + 10, "DATE CHECK", WHITE, 2)
    dlines = wrap_text(DATECHECK, 102)
    yy = dy + 28
    for ln in dlines:
        draw_text(cv, L(dx) + 16, L(yy), ln, INK, 2)
        yy += 9
    yy += 4
    draw_text(cv, L(dx) + 16, L(yy), "PRESS TIME: WIRES READ TO 13:30 UTC, MON 23 NOV 2026.", DARKRED, 2)
    yy += 11
    draw_text(cv, L(dx) + 16, L(yy), "PINS MATCH STORY NUMBERS 1-13. NO. 13 PIN IS OFFSET FROM GAZA CITY.", GREY, 2)
    # footer
    foot = "SOURCES: REUTERS, AP, AFP, BBC, AL JAZEERA, GUARDIAN, DPA, ARAB NEWS, JUST SECURITY, FDD."
    draw_text(cv, (DW - text_w(foot, 2)) // 2, L(1006), foot, GREY, 2)
    return cv

def main():
    cv = render()
    rgb = cv.downsample()
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "")
    path = os.path.join(out, "entry.png") if out else "entry.png"
    size = write_png(path, rgb)
    print("entry.png %d bytes, %dx%d" % (size, W, H))

if __name__ == "__main__":
    main()
