from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np
import random

random.seed(42)
np.random.seed(42)

NAMES = [
    "AJ DYBANTSA", "DARRYN PETERSON", "CALEB WILSON", "CAM BOOZER",
    "KEATON WAGLER", "KINGSTON FLEMINGS", "YAXEL LENDOBORG", "BRAYDEN BURRIES",
    "EBUKA OKORIE", "MOREZ JOHNSON", "ADAY MARA", "DARIUS ACUFF",
    "JAYDEN QUAINTANCE", "CAMERON CARR", "KOA PEAT", "ALLEN GRAVES",
    "MELEEK THOMAS", "MIKEL BROWN JR", "AMARI ALLEN", "NATE AMENT",
    "HANNES STEINBACH", "LABARON PHILON", "TOUNDE YESSOUFOU", "BENNETT STIRTZ",
    "CHRIS CENAC", "CHRISTIAN ANDERSON", "MOTIEJUS KRIVAS", "DASH DANIELS",
    "RICHIE SAUNDERS", "DAILYN SWAIN", "PATRICK NGONGBA", "ALEX KARABAN",
    "DAVID MIRKOVIC", "BRAYLON MULLINS", "THOMAS HAUGH", "BILLY RICHMOND",
    "SHELTON HENDERSON", "KARIM LOPEZ", "FLORY BIDUNGA", "OTEGA OWEH",
    "TARRIS REED", "NIKOLAS KHAMENIA", "JOSHUA JEFFERSON", "JEREMY FEARS JR",
    "TYLER TANNER", "MILES BYRD", "MALACHI MORENO", "HENRI VEESAAR",
    "LUIGI SUIGO", "DAME SARR", "PJ HAGGERTY", "MILAN MOMCILOVIC",
    "NICK MARTINELLI", "ISAIAH EVANS", "JT TOPPIN", "DONNIE FREEMAN",
    "MATT ABLE", "ZUBY EJIOFOR", "JAYDEN ROSS", "BRADEN SMITH",
    "DILLON MITCHELL", "MALIQUE BROWN", "TOMISLAV IVISIC", "JOJO TUGLER",
    "EMMANUEL SHARP", "MILOS UZAN", "RUBEN CHINLEYU", "IVAN KHARCHENKOV",
    "QUADIR COPELAND", "BABA MILLER", "NEOKLIS AVDALAS", "ALIJAH ARENAS",
    "RILEY KUGEL", "JOHANN GRUNLOH", "ELYJAH FREEMAN", "DERRION REID",
    "TUCKER DEVRIES", "MARIO SAINT-SUPERY", "BAYE NDONGO", "SERGIO DE LARREA",
    "COEN CARR", "XAVIAN LEE", "JUKE HARRIS", "BRYSON TILLER",
    "OMER MAYER", "ANDREJ STOJAKOVIC", "COLE ROSARIO", "CAM MANYAWU",
    "TREY MCKENNEY", "RYAN CONWELL", "KEYSHAWN HALL", "AIDEN SHERRELL",
    "FELIX OKPARA", "BEN HUMRICHOUS", "PAUL MCNEIL JR", "BOOGIE FLAND",
    "KANON CATCHINGS", "MAGOON GWATH", "KARTER KNOX", "JOSON SANON",
]

W, H = 1200, 1900

BG       = (18, 38, 72)         # medium-dark navy blue
NEON     = (80, 255, 120)
BLUE     = (120, 200, 255)
DIM_NEON = (50, 180, 80)
WHITE    = (240, 245, 255)
YELLOW   = (240, 200, 20)
RED      = (210, 50, 50)
GREY     = (140, 155, 180)
PURPLE   = (180, 140, 255)

FONT_MONO  = "/System/Library/Fonts/Monaco.ttf"
FONT_TITLE = "/System/Library/Fonts/SFNSMono.ttf"

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

# ── DISTORTION HELPERS ──────────────────────────────────────────────────────

def heavy_noise(img, intensity=22):
    arr = np.array(img).astype(np.int16)
    # Per-channel independent noise for color fringing
    for c in range(3):
        noise = np.random.randint(-intensity, intensity + 1, arr.shape[:2])
        arr[:, :, c] = np.clip(arr[:, :, c] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))

def scanlines(img, gap=2, alpha=70):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for y in range(0, img.height, gap):
        d.line([(0, y), (img.width, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def phosphor_bleed(img, strength=1.6):
    # Slight horizontal blur to mimic phosphor spread
    arr = np.array(img).astype(np.float32)
    kernel = np.array([0.08, 0.18, 0.48, 0.18, 0.08])
    for c in range(3):
        arr[:, :, c] = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode='same'), 1, arr[:, :, c])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def chromatic_aberration(img, shift=2):
    # Offset red channel left, blue channel right
    arr = np.array(img)
    out = arr.copy()
    out[:, shift:, 0] = arr[:, :-shift, 0]   # red shifts right
    out[:, :-shift, 2] = arr[:, shift:, 2]   # blue shifts left
    return Image.fromarray(out)

def vhs_tracking_lines(img, n=6):
    arr = np.array(img).astype(np.int16)
    h, w = arr.shape[:2]
    for _ in range(n):
        y = random.randint(0, h - 1)
        thickness = random.randint(1, 3)
        brightness = random.choice([-60, -40, 30, 50])
        shift = random.randint(-8, 8)
        for dy in range(thickness):
            row = min(y + dy, h - 1)
            rolled = np.roll(arr[row], shift, axis=0)
            arr[row] = np.clip(rolled + brightness, 0, 255)
    return Image.fromarray(arr.astype(np.uint8))

def vignette(img, strength=0.72):
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt(((X - w/2) / (w/2))**2 + ((Y - h/2) / (h/2))**2)
    mask = np.clip(1 - dist * strength, 0.22, 1.0)
    for c in range(3):
        arr[:, :, c] *= mask
    return Image.fromarray(arr.astype(np.uint8))

def burn_in_glow(draw, x, y, text, font, color, spread=3):
    # Dim halo — simulate phosphor burn
    for r in range(spread, 0, -1):
        alpha = int(35 * (1 - r / spread))
        for dx in range(-r, r+1, max(1, r//2)):
            for dy in range(-r, r+1, max(1, r//2)):
                draw.text((x+dx, y+dy), text, font=font, fill=(*color, alpha))
    draw.text((x, y), text, font=font, fill=color)

def draw_racing_stripes(draw, x, y, w, h, angle=20):
    colors = [YELLOW, RED, YELLOW, RED, YELLOW, RED]
    sw = 24
    for i, col in enumerate(colors):
        sx = x + i * sw
        pts = [(sx, y), (sx+sw, y), (sx+sw-angle, y+h), (sx-angle, y+h)]
        draw.polygon(pts, fill=col)

def draw_checkered(draw, x, y, cols, rows, cell=13):
    for r in range(rows):
        for c in range(cols):
            fill = (220, 220, 215) if (r+c) % 2 == 0 else (8, 8, 12)
            draw.rectangle([x+c*cell, y+r*cell, x+c*cell+cell-1, y+r*cell+cell-1], fill=fill)

def dirty_line(draw, x1, y1, x2, y2, color, width=1):
    # Slightly wobbly line
    pts = []
    steps = max(abs(x2-x1), abs(y2-y1)) // 4 or 1
    for t in range(steps+1):
        fx = x1 + (x2-x1)*t/steps + random.randint(-1, 1)
        fy = y1 + (y2-y1)*t/steps + random.randint(-1, 1)
        pts.append((fx, fy))
    for i in range(len(pts)-1):
        draw.line([pts[i], pts[i+1]], fill=color, width=width)

# ── BUILD ────────────────────────────────────────────────────────────────────

img  = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img, "RGBA")

# Faint phosphor grain in background — subtle green tint blotches
for _ in range(900):
    bx = random.randint(0, W)
    by = random.randint(0, H)
    br = random.randint(1, 5)
    ba = random.randint(4, 18)
    draw.ellipse([bx-br, by-br, bx+br, by+br], fill=(0, random.randint(30, 70), 10, ba))

# Background scan-grid — dirtier, uneven spacing
for x in range(0, W, random.randint(38, 44)):
    draw.line([(x, 0), (x, H)], fill=(20, 28, 42), width=1)
for y in range(0, H, random.randint(38, 44)):
    draw.line([(0, y), (W, y)], fill=(18, 25, 38), width=1)

# ── HEADER ──────────────────────────────────────────────────────────────────
HEADER_H = 158
draw.rectangle([0, 0, W, HEADER_H], fill=(10, 25, 55))

# Slightly imperfect rule lines
dirty_line(draw, 0, 3, W, 3, (*NEON, 180), 2)
dirty_line(draw, 0, HEADER_H-4, W, HEADER_H-4, (*NEON, 130), 1)
dirty_line(draw, 0, HEADER_H+1, W, HEADER_H+1, (*BLUE, 200), 3)

title_font = load_font(FONT_TITLE, 44)
sub_font   = load_font(FONT_TITLE, 21)

# Title with chromatic-style offset (manual RGB split)
tx, ty = 28, 22
draw.text((tx+3, ty+2), "2026 NBA Draft Big Board", font=title_font, fill=(180, 0, 0, 90))
draw.text((tx-2, ty-1), "2026 NBA Draft Big Board", font=title_font, fill=(0, 60, 200, 70))
burn_in_glow(draw, tx, ty, "2026 NBA Draft Big Board", title_font, NEON, spread=4)

draw.text((tx+1, ty+56), "(With Returners)  //  TOP 100", font=sub_font, fill=(*BLUE, 210))

# ── COLUMNS ─────────────────────────────────────────────────────────────────
COLS    = 4
ROWS    = 25
TOP_PAD = HEADER_H + 28
COL_W   = W // COLS
ROW_H   = (H - TOP_PAD - 55) // ROWS

name_font = load_font(FONT_MONO, 17)
num_font  = load_font(FONT_MONO, 17)

for i, name in enumerate(NAMES):
    rank = i + 1
    col  = i // ROWS
    row  = i % ROWS
    x    = col * COL_W + 10
    y    = TOP_PAD + row * ROW_H

    # Row tint — not perfectly aligned, slight y jitter
    jitter = random.randint(-1, 1)
    if row % 2 == 0:
        draw.rectangle(
            [col*COL_W+1, y+jitter, (col+1)*COL_W-3, y+ROW_H-2+jitter],
            fill=(25, 52, 95)
        )

    # Tier color
    if rank <= 14:
        tier_col = NEON
    elif rank <= 30:
        tier_col = BLUE
    elif rank <= 58:
        tier_col = PURPLE
    else:
        tier_col = GREY

    # Left accent bar — slightly rough edges
    bx = col * COL_W + random.randint(0, 1)
    draw.rectangle([bx, y+1, bx+3, y+ROW_H-3], fill=tier_col)

    # Rank number
    num_str = f"{rank:>3}."
    # Slight per-character x drift for "worn" feel
    draw.text((x+7 + random.randint(-1,1), y+3), num_str, font=num_font, fill=tier_col)

    # Name text with occasional dim ghost offset (phosphor persistence)
    nx = x + 50
    ny = y + 3
    if rank <= 5:
        draw.text((nx, ny), name, font=name_font, fill=(160, 255, 180))
    elif rank <= 14:
        draw.text((nx, ny), name, font=name_font, fill=(240, 248, 255))
    elif rank <= 30:
        draw.text((nx, ny), name, font=name_font, fill=(210, 228, 255))
    elif rank <= 58:
        draw.text((nx, ny), name, font=name_font, fill=(195, 210, 240))
    else:
        draw.text((nx, ny), name, font=name_font, fill=(175, 190, 220))

# Column dividers — wobbly
for c in range(1, COLS):
    cx = c * COL_W
    dirty_line(draw, cx, HEADER_H+2, cx, H-45, (35, 45, 65), 1)

# ── FOOTER ───────────────────────────────────────────────────────────────────
footer_y = H - 46
dirty_line(draw, 0, footer_y, W, footer_y, (*BLUE, 180), 2)
draw.rectangle([0, footer_y+2, W, H], fill=(10, 25, 55))

footer_font = load_font(FONT_TITLE, 15)
draw.text((14, footer_y+12), "// 2026 CLASS  //  PRE-DRAFT  //", font=footer_font, fill=(*DIM_NEON, 200))
draw.text((W-215, footer_y+12), "@ludicspace", font=footer_font, fill=(*BLUE, 220))

# ── POST-PROCESS: gritty pipeline ────────────────────────────────────────────
img = heavy_noise(img, intensity=10)
img = vhs_tracking_lines(img, n=3)
img = chromatic_aberration(img, shift=1)
img = vignette(img, strength=0.35)
img = scanlines(img, gap=3, alpha=35)

out = "public/bigboard_2026.png"
img.save(out, quality=95)
print(f"Saved → {out}  ({W}×{H})")
