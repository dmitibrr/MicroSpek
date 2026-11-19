"""Generate neumorphic README artwork (hero banner + feature icons).

Everything is drawn with Pillow, so the images are reproducible and need no
external assets. Run:  python scripts/make_readme_art.py

Output: docs/images/hero.png, icon-sensors.png, icon-disks.png,
        icon-speed.png, icon-private.png
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"

BG = (226, 230, 236)
BG_DARK = (214, 219, 227)
DARK = (150, 163, 183)
LIGHT = (255, 255, 255)
INK = (84, 96, 115)
INK_SOFT = (124, 137, 157)
MINT = (94, 200, 170)
BLUE = (108, 152, 214)
AMBER = (232, 178, 96)

FONT_DIR = Path(r"C:\Windows\Fonts")


# --------------------------------------------------------------------------
# low-level helpers
# --------------------------------------------------------------------------
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def linear_gradient(size: tuple[int, int], top: tuple[int, ...], bottom: tuple[int, ...]) -> Image.Image:
    width, height = size
    strip = Image.new("RGB", (1, height))
    draw = ImageDraw.Draw(strip)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.point((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return strip.resize((width, height), Image.BILINEAR).convert("RGBA")


def shifted(mask: Image.Image, dx: int, dy: int) -> Image.Image:
    result = Image.new("L", mask.size, 0)
    result.paste(mask, (dx, dy))
    return result


def tinted(color: tuple[int, ...], alpha: int) -> Image.Image:
    return Image.new("RGBA", (1, 1), color + (alpha,))


def fill_mask(mask: Image.Image, color: tuple[int, ...], alpha: int = 255) -> Image.Image:
    layer = Image.new("RGBA", mask.size, color + (0,))
    layer.putalpha(mask.point(lambda v: v * alpha // 255))
    return layer


def raised(
    canvas: Image.Image,
    mask: Image.Image,
    *,
    distance: int = 10,
    blur: int = 18,
    dark_alpha: int = 70,
    light_alpha: int = 190,
    top: tuple[int, ...] = BG,
    bottom: tuple[int, ...] = BG_DARK,
) -> None:
    """Extrude a shape from the background with the classic dual shadow."""
    shadow = fill_mask(shifted(mask, distance, distance), DARK, dark_alpha).filter(
        ImageFilter.GaussianBlur(blur)
    )
    light = fill_mask(shifted(mask, -distance, -distance), LIGHT, light_alpha).filter(
        ImageFilter.GaussianBlur(blur)
    )
    canvas.alpha_composite(shadow)
    canvas.alpha_composite(light)
    body = linear_gradient(canvas.size, top, bottom)
    body.putalpha(mask)
    canvas.alpha_composite(body)


def inset(
    canvas: Image.Image,
    mask: Image.Image,
    *,
    distance: int = 8,
    blur: int = 10,
    dark_alpha: int = 95,
    light_alpha: int = 210,
) -> None:
    """Carve a groove: shadow inside the top-left edge, light inside bottom-right."""
    dark_band = ImageChops.subtract(mask, shifted(mask, distance, distance))
    dark_band = ImageChops.multiply(dark_band.filter(ImageFilter.GaussianBlur(blur)), mask)
    light_band = ImageChops.subtract(mask, shifted(mask, -distance, -distance))
    light_band = ImageChops.multiply(light_band.filter(ImageFilter.GaussianBlur(blur)), mask)
    canvas.alpha_composite(fill_mask(dark_band, DARK, dark_alpha))
    canvas.alpha_composite(fill_mask(light_band, LIGHT, light_alpha))


def shape_mask(size: tuple[int, int], draw_shape) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw_shape(ImageDraw.Draw(mask))
    return mask


def embossed_text(
    canvas: Image.Image,
    position: tuple[int, int],
    text: str,
    typeface: ImageFont.FreeTypeFont,
    color: tuple[int, ...] = INK,
    *,
    tracking: int = 0,
    depth: int = 4,
) -> None:
    width = _text_width(text, typeface, tracking)
    mask = Image.new("L", (width + 40, typeface.size * 2 + 40), 0)
    _draw_tracked(mask, (20, 20), text, typeface, tracking, 255)
    box = mask.getbbox()
    if box:
        mask = mask.crop(box)
    x, y = position

    layer = Image.new("L", canvas.size, 0)
    layer.paste(mask, (x, y))
    canvas.alpha_composite(fill_mask(layer.filter(ImageFilter.GaussianBlur(depth + 1)),
                                    (120, 134, 155), 120), (depth, depth + 2))
    canvas.alpha_composite(fill_mask(layer.filter(ImageFilter.GaussianBlur(depth + 1)),
                                    (255, 255, 255), 230), (-depth, -depth - 1))
    canvas.alpha_composite(fill_mask(layer, color))


def _text_width(text: str, typeface: ImageFont.FreeTypeFont, tracking: int) -> int:
    total = 0
    for char in text:
        total += typeface.getbbox(char)[2] + tracking
    return total


def _draw_tracked(
    image: Image.Image,
    position: tuple[int, int],
    text: str,
    typeface: ImageFont.FreeTypeFont,
    tracking: int,
    value: int,
) -> None:
    draw = ImageDraw.Draw(image)
    x, y = position
    for char in text:
        draw.text((x, y), char, font=typeface, fill=value)
        x += typeface.getbbox(char)[2] + tracking


# --------------------------------------------------------------------------
# hero banner
# --------------------------------------------------------------------------
def make_hero(lang: str = "en") -> Image.Image:
    width, height = 1600, 640
    texts = {
        "en": (
            "PC specifications without the fuss",
            ["TXT / JSON / MD", "Windows 10 · 11", "≈ 5 seconds"],
        ),
        "ru": (
            "Характеристики ПК без лишних движений",
            ["TXT / JSON / MD", "Windows 10 · 11", "≈ 5 секунд"],
        ),
    }
    subtitle, badge_specs = texts.get(lang, texts["en"])
    canvas = linear_gradient((width, height), (233, 237, 242), BG)

    # soft light from the top-left corner
    glow = Image.new("L", (width, height), 0)
    ImageDraw.Draw(glow).ellipse((-420, -520, 900, 620), fill=110)
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    canvas.alpha_composite(fill_mask(glow, (255, 255, 255), 150))

    # main raised panel
    panel_box = (860, 60, 1548, 580)
    panel = shape_mask((width, height),
                       lambda d: d.rounded_rectangle(panel_box, radius=56, fill=255))
    raised(canvas, panel, distance=14, blur=26, dark_alpha=80, light_alpha=210,
           top=(230, 234, 240), bottom=(218, 223, 231))
    inset(canvas, panel, distance=26, blur=26, dark_alpha=14, light_alpha=40)

    # --- chip pins (drawn first, so the chip body covers their roots) ------
    pins = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pins)
    pin_color = (201, 207, 217, 255)
    for index in range(7):
        x = 948 + index * 27
        pd.rounded_rectangle((x, 132, x + 12, 168), radius=5, fill=pin_color)
        pd.rounded_rectangle((x, 382, x + 12, 418), radius=5, fill=pin_color)
    for index in range(7):
        y = 186 + index * 27
        pd.rounded_rectangle((894, y, 928, y + 12), radius=5, fill=pin_color)
        pd.rounded_rectangle((1142, y, 1176, y + 12), radius=5, fill=pin_color)
    canvas.alpha_composite(pins.filter(ImageFilter.GaussianBlur(0.8)))

    # --- chip -------------------------------------------------------------
    chip = shape_mask((width, height),
                      lambda d: d.rounded_rectangle((920, 160, 1150, 390), radius=36, fill=255))
    raised(canvas, chip, distance=9, blur=15, dark_alpha=95, light_alpha=220,
           top=(235, 239, 244), bottom=(209, 214, 223))

    # chip die
    die = shape_mask((width, height),
                     lambda d: d.rounded_rectangle((962, 202, 1108, 348), radius=26, fill=255))
    inset(canvas, die, distance=9, blur=12, dark_alpha=80, light_alpha=190)
    inner = shape_mask((width, height),
                       lambda d: d.rounded_rectangle((996, 236, 1074, 314), radius=16, fill=255))
    raised(canvas, inner, distance=4, blur=8, dark_alpha=90, light_alpha=180,
           top=(214, 238, 232), bottom=(186, 216, 208))

    # --- graphics card ----------------------------------------------------
    card = shape_mask((width, height),
                      lambda d: d.rounded_rectangle((1190, 130, 1500, 320), radius=30, fill=255))
    raised(canvas, card, distance=9, blur=16, dark_alpha=95, light_alpha=220,
           top=(234, 238, 244), bottom=(207, 212, 222))

    for cx in (1258, 1432):
        fan_outer = shape_mask((width, height), lambda d, cx=cx: d.ellipse(
            (cx - 54, 225 - 54, cx + 54, 225 + 54), fill=255))
        inset(canvas, fan_outer, distance=8, blur=10, dark_alpha=80, light_alpha=190)
        ring = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((cx - 48, 225 - 48, cx + 48, 225 + 48),
                                     outline=(178, 186, 199, 120), width=2)
        canvas.alpha_composite(ring)
        blades = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        bd = ImageDraw.Draw(blades)
        for step in range(8):
            angle = step * 45
            bd.arc((cx - 40, 225 - 40, cx + 40, 225 + 40), angle, angle + 26,
                   fill=(196, 202, 213, 220), width=7)
        canvas.alpha_composite(blades.filter(ImageFilter.GaussianBlur(0.7)))
        hub = shape_mask((width, height), lambda d, cx=cx: d.ellipse(
            (cx - 18, 225 - 18, cx + 18, 225 + 18), fill=255))
        raised(canvas, hub, distance=3, blur=6, dark_alpha=70, light_alpha=170,
               top=(232, 236, 242), bottom=(211, 216, 225))

    # --- SSD ---------------------------------------------------------------
    ssd = shape_mask((width, height),
                     lambda d: d.rounded_rectangle((1210, 350, 1440, 480), radius=24, fill=255))
    raised(canvas, ssd, distance=8, blur=14, dark_alpha=95, light_alpha=220,
           top=(234, 238, 244), bottom=(209, 214, 223))
    slot = shape_mask((width, height),
                      lambda d: d.rounded_rectangle((1230, 368, 1420, 462), radius=18, fill=255))
    inset(canvas, slot, distance=6, blur=9, dark_alpha=60, light_alpha=130)
    bars = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bars)
    for index, color in enumerate((BLUE, AMBER, (176, 184, 197))):
        top_y = 382 + index * 24
        bd.rounded_rectangle((1250, top_y, 1250 + (146 - index * 26), top_y + 14),
                             radius=7, fill=color + (235,))
    canvas.alpha_composite(bars)

    # --- wordmark ----------------------------------------------------------
    embossed_text(canvas, (92, 172), "MicroSpek", font("seguisb.ttf", 118), INK,
                  tracking=2, depth=5)
    embossed_text(canvas, (102, 328), subtitle,
                  font("segoeuil.ttf", 38), INK_SOFT, tracking=0, depth=3)

    small = font("segoeuil.ttf", 24)
    x = 96
    for label in badge_specs:
        text_width = _text_width(label, small, 0)
        box = (x, 438, x + text_width + 48, 496)
        mask = shape_mask((width, height),
                          lambda d, box=box: d.rounded_rectangle(box, radius=29, fill=255))
        raised(canvas, mask, distance=5, blur=11, dark_alpha=65, light_alpha=200,
               top=(229, 233, 239), bottom=(218, 223, 231))
        layer = Image.new("L", (width, height), 0)
        _draw_tracked(layer, (box[0] + 25, box[1] + 15), label, small, 0, 255)
        canvas.alpha_composite(fill_mask(layer, (108, 120, 140), 255))
        x = box[2] + 20

    return canvas.convert("RGB")


# --------------------------------------------------------------------------
# icons
# --------------------------------------------------------------------------
def icon_canvas(size: int = 512) -> Image.Image:
    canvas = linear_gradient((size, size), (233, 237, 242), BG)
    glow = Image.new("L", (size, size), 0)
    ImageDraw.Draw(glow).ellipse((-160, -180, 300, 280), fill=110)
    canvas.alpha_composite(fill_mask(glow.filter(ImageFilter.GaussianBlur(90)),
                                    (255, 255, 255), 140))
    plate = shape_mask((size, size),
                       lambda d: d.rounded_rectangle((56, 56, 456, 456), radius=108, fill=255))
    raised(canvas, plate, distance=12, blur=22, dark_alpha=70, light_alpha=200,
           top=(230, 234, 240), bottom=(217, 222, 230))
    inset(canvas, plate, distance=20, blur=24, dark_alpha=12, light_alpha=36)
    return canvas


def icon_sensors() -> Image.Image:
    size = 512
    canvas = icon_canvas(size)

    # thermometer
    tube = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (150, 118, 232, 330), radius=41, fill=255))
    raised(canvas, tube, distance=7, blur=12, dark_alpha=90, light_alpha=210,
           top=(235, 239, 244), bottom=(208, 213, 222))
    channel = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (172, 140, 210, 300), radius=19, fill=255))
    inset(canvas, channel, distance=5, blur=7, dark_alpha=80, light_alpha=170)
    mercury = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (172, 226, 210, 306), radius=19, fill=255))
    canvas.alpha_composite(fill_mask(mercury, MINT, 235))
    bulb = shape_mask((size, size), lambda d: d.ellipse((146, 300, 236, 390), fill=255))
    raised(canvas, bulb, distance=6, blur=11, dark_alpha=90, light_alpha=210,
           top=(235, 239, 244), bottom=(208, 213, 222))
    core = shape_mask((size, size), lambda d: d.ellipse((170, 324, 212, 366), fill=255))
    canvas.alpha_composite(fill_mask(core, MINT, 240))
    shine = shape_mask((size, size), lambda d: d.ellipse((178, 330, 196, 348), fill=255))
    canvas.alpha_composite(fill_mask(shine, (255, 255, 255), 190))

    # gauge
    dial = shape_mask((size, size), lambda d: d.ellipse((272, 150, 440, 318), fill=255))
    raised(canvas, dial, distance=8, blur=14, dark_alpha=85, light_alpha=210,
           top=(234, 238, 244), bottom=(210, 215, 224))
    face = shape_mask((size, size), lambda d: d.ellipse((296, 174, 416, 294), fill=255))
    inset(canvas, face, distance=7, blur=10, dark_alpha=75, light_alpha=180)

    ticks = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    td = ImageDraw.Draw(ticks)
    for step in range(9):
        angle = math.radians(150 + step * 30)
        cx, cy, r1, r2 = 356, 234, 50, 58
        td.line((cx + r1 * math.cos(angle), cy + r1 * math.sin(angle),
                 cx + r2 * math.cos(angle), cy + r2 * math.sin(angle)),
                fill=(168, 177, 192, 220), width=4)
    canvas.alpha_composite(ticks)

    needle = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    nd = ImageDraw.Draw(needle)
    nd.line((356, 234, 390, 204), fill=MINT + (255,), width=7)
    nd.ellipse((346, 224, 366, 244), fill=(126, 138, 156, 255))
    canvas.alpha_composite(needle.filter(ImageFilter.GaussianBlur(0.6)))

    return canvas.convert("RGB")


def icon_disks() -> Image.Image:
    size = 512
    canvas = icon_canvas(size)

    drive = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (120, 140, 392, 392), radius=44, fill=255))
    raised(canvas, drive, distance=9, blur=16, dark_alpha=95, light_alpha=215,
           top=(235, 239, 244), bottom=(207, 212, 221))
    # bevel rim
    rim = ImageChops.subtract(drive, drive.filter(ImageFilter.MinFilter(7)))
    inset(canvas, rim, distance=4, blur=7, dark_alpha=45, light_alpha=120)

    # partition grooves
    for index, color in enumerate((BLUE, AMBER, (176, 184, 197))):
        top = 176 + index * 58
        groove = shape_mask((size, size), lambda d, top=top: d.rounded_rectangle(
            (150, top, 362, top + 44), radius=22, fill=255))
        inset(canvas, groove, distance=6, blur=9, dark_alpha=75, light_alpha=150)
        bar = shape_mask((size, size), lambda d, top=top, index=index: d.rounded_rectangle(
            (168, top + 13, 168 + (160 - index * 32), top + 31), radius=9, fill=255))
        canvas.alpha_composite(fill_mask(bar, color, 240))

    # screws
    for cx in (162, 350):
        screw = shape_mask((size, size), lambda d, cx=cx: d.ellipse(
            (cx - 10, 354, cx + 10, 374), fill=255))
        inset(canvas, screw, distance=3, blur=4, dark_alpha=95, light_alpha=175)
        slot = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(slot).line((cx - 6, 364, cx + 6, 364),
                                  fill=(150, 160, 176, 210), width=3)
        canvas.alpha_composite(slot)

    return canvas.convert("RGB")


def icon_speed() -> Image.Image:
    size = 512
    canvas = icon_canvas(size)

    body = shape_mask((size, size), lambda d: d.ellipse((132, 156, 388, 412), fill=255))
    raised(canvas, body, distance=9, blur=16, dark_alpha=95, light_alpha=215,
           top=(235, 239, 244), bottom=(208, 213, 222))
    face = shape_mask((size, size), lambda d: d.ellipse((162, 186, 358, 382), fill=255))
    inset(canvas, face, distance=8, blur=12, dark_alpha=70, light_alpha=175)

    ticks = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    td = ImageDraw.Draw(ticks)
    for step in range(12):
        angle = math.radians(step * 30)
        cx, cy, r1, r2 = 260, 284, 74, 84
        width = 5 if step % 3 == 0 else 3
        td.line((cx + r1 * math.cos(angle), cy + r1 * math.sin(angle),
                 cx + r2 * math.cos(angle), cy + r2 * math.sin(angle)),
                fill=(170, 179, 194, 225), width=width)
    canvas.alpha_composite(ticks)

    # lightning bolt
    bolt = [(268, 214), (216, 292), (254, 292), (238, 356), (302, 268), (262, 268),
            (286, 214)]
    bolt_shape = shape_mask((size, size), lambda d: d.polygon(bolt, fill=255))
    raised(canvas, bolt_shape, distance=4, blur=7, dark_alpha=80, light_alpha=170,
           top=(126, 214, 190), bottom=(84, 186, 158))

    # crown button and stem
    crown = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (238, 118, 282, 158), radius=14, fill=255))
    raised(canvas, crown, distance=5, blur=9, dark_alpha=85, light_alpha=200,
           top=(233, 237, 243), bottom=(210, 215, 224))
    stem = shape_mask((size, size), lambda d: d.rounded_rectangle(
        (250, 152, 270, 172), radius=8, fill=255))
    inset(canvas, stem, distance=3, blur=5, dark_alpha=70, light_alpha=150)

    return canvas.convert("RGB")


def icon_private() -> Image.Image:
    size = 512
    canvas = icon_canvas(size)

    shield = [(256, 100), (404, 148), (404, 272), (256, 420), (108, 272), (108, 148)]
    raw = shape_mask((size, size), lambda d: d.polygon(shield, fill=255))
    smooth = raw.filter(ImageFilter.GaussianBlur(9)).point(lambda v: 255 if v > 128 else 0)
    shield_mask = smooth.filter(ImageFilter.GaussianBlur(1)).point(lambda v: 255 if v > 150 else 0)
    raised(canvas, shield_mask, distance=9, blur=16, dark_alpha=95, light_alpha=215,
           top=(235, 239, 244), bottom=(208, 213, 222))

    # beveled rim so the shield reads as a solid object, not a flat patch
    rim = ImageChops.subtract(shield_mask, shield_mask.filter(ImageFilter.MinFilter(23)))
    inset(canvas, rim, distance=7, blur=10, dark_alpha=28, light_alpha=110)

    # carved keyhole
    def keyhole(shrink: int) -> Image.Image:
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((232 - 10 + shrink, 196 - 10 + shrink,
                      284 + 10 - shrink, 248 + 10 - shrink), fill=255)
        draw.polygon([(244 + shrink, 236), (272 - shrink, 236),
                      (282 - shrink, 322 - shrink), (234 + shrink, 322 - shrink)], fill=255)
        return mask

    groove = keyhole(4)
    canvas.alpha_composite(fill_mask(groove, (206, 210, 219), 255))
    inset(canvas, groove, distance=6, blur=9, dark_alpha=130, light_alpha=120)

    core = keyhole(8)
    canvas.alpha_composite(fill_mask(core, BLUE, 240))
    shade = ImageChops.subtract(core, shifted(core, 5, 5))
    canvas.alpha_composite(fill_mask(shade.filter(ImageFilter.GaussianBlur(4)),
                                    (58, 88, 140), 70))

    return canvas.convert("RGB")


# --------------------------------------------------------------------------
# framed screenshot
# --------------------------------------------------------------------------
def make_gui_preview(source: Path, target: Path) -> Image.Image | None:
    if not source.is_file():
        return None
    shot = Image.open(source).convert("RGB")
    # drop the OS title bar and the resize border captured by PrintWindow
    shot = shot.crop((9, 39, shot.width - 9, shot.height - 9))

    pad = 64
    radius = 16
    canvas = linear_gradient((shot.width + pad * 2, shot.height + pad * 2),
                             (233, 237, 242), BG)
    glow = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(glow).ellipse((-200, -240, 700, 480), fill=110)
    canvas.alpha_composite(fill_mask(glow.filter(ImageFilter.GaussianBlur(120)),
                                    (255, 255, 255), 130))

    rounded = Image.new("L", shot.size, 0)
    ImageDraw.Draw(rounded).rounded_rectangle((0, 0, shot.width - 1, shot.height - 1),
                                              radius=radius, fill=255)

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow.alpha_composite(fill_mask(rounded, (120, 134, 155), 120), (pad, pad + 16))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(26)))

    body = shot.copy()
    body.putalpha(rounded)
    canvas.alpha_composite(body, (pad, pad))

    rim = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(rim).rounded_rectangle(
        (pad - 1, pad - 1, pad + shot.width, pad + shot.height),
        radius=radius + 1, outline=(255, 255, 255, 190), width=2)
    canvas.alpha_composite(rim)

    result = canvas.convert("RGB")
    result.save(target, optimize=True)
    return result


# --------------------------------------------------------------------------
def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    images = {
        "hero.png": make_hero("en"),
        "hero-ru.png": make_hero("ru"),
        "icon-sensors.png": icon_sensors(),
        "icon-disks.png": icon_disks(),
        "icon-speed.png": icon_speed(),
        "icon-private.png": icon_private(),
    }
    for name, image in images.items():
        path = OUT / name
        image.save(path, optimize=True)
        print(f"{name:22} {image.size[0]}x{image.size[1]}  {path.stat().st_size // 1024} KB")

    for source, target in (
        ("gui-window.png", "gui-preview.png"),
        ("gui-window-ru.png", "gui-preview-ru.png"),
    ):
        preview = make_gui_preview(OUT / source, OUT / target)
        if preview is not None:
            path = OUT / target
            print(f"{path.name:22} {preview.size[0]}x{preview.size[1]}  "
                  f"{path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
