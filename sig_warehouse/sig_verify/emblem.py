"""The SIG stylised palm-and-swords mark, drawn from geometry (no bitmap asset needed).

Ported from ERPNext/docs/saudi_emblem.py. An eight-armed green star whose lower arm runs on as
the palm trunk, over a black saltire for the crossed swords. Deliberately blunt: at QR-centre
size any fine detail disappears, so the mark survives on outline alone.
"""

import math

from PIL import Image, ImageDraw

# Reference canvas; all geometry is expressed in these units and scaled.
REF_W, REF_H = 1024, 1536
SUPERSAMPLE = 3

GREEN = (11, 91, 52, 255)
BLACK = (35, 31, 32, 255)

STAR_CENTER = (512, 430)
ARM_WIDTH = 140
ARM_ORTHOGONAL = 384
ARM_DIAGONAL = 424
TRUNK_BOTTOM = 930
TRUNK_TIP = 975

CROSS_CENTER = (512, 1180)
CROSS_ARM = 430
CROSS_WIDTH = 150


def _bar(draw, center, angle_deg, half_length, width):
    cx, cy = center
    a = math.radians(angle_deg)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy * width / 2, ux * width / 2
    ex, ey = ux * half_length, uy * half_length
    draw.polygon([(cx + ex + px, cy + ey + py), (cx + ex - px, cy + ey - py),
                  (cx - ex - px, cy - ey - py), (cx - ex + px, cy - ey + py)], fill=255)


def _star(draw, scale):
    cx, cy = STAR_CENTER[0] * scale, STAR_CENTER[1] * scale
    width = ARM_WIDTH * scale
    for angle in (0, 90):
        _bar(draw, (cx, cy), angle, ARM_ORTHOGONAL * scale, width)
    for angle in (45, 135):
        _bar(draw, (cx, cy), angle, ARM_DIAGONAL * scale, width)
    half = width / 2
    draw.rectangle((cx - half, cy, cx + half, TRUNK_BOTTOM * scale), fill=255)
    draw.polygon([(cx - half, TRUNK_BOTTOM * scale), (cx + half, TRUNK_BOTTOM * scale),
                  (cx, TRUNK_TIP * scale)], fill=255)


def _saltire(draw, scale):
    center = (CROSS_CENTER[0] * scale, CROSS_CENTER[1] * scale)
    for angle in (45, 135):
        _bar(draw, center, angle, CROSS_ARM * scale, CROSS_WIDTH * scale)


def render_emblem_image(height=1536, green=GREEN, black=BLACK):
    """Return the mark as a transparent RGBA image ``height`` pixels tall."""
    scale = height / REF_H
    s = SUPERSAMPLE
    big = (int(REF_W * scale * s), int(height * s))

    star_mask = Image.new("L", big, 0)
    _star(ImageDraw.Draw(star_mask), scale * s)
    cross_mask = Image.new("L", big, 0)
    _saltire(ImageDraw.Draw(cross_mask), scale * s)

    out_size = (int(REF_W * scale), height)
    star_mask = star_mask.resize(out_size, Image.Resampling.LANCZOS)
    cross_mask = cross_mask.resize(out_size, Image.Resampling.LANCZOS)

    emblem = Image.new("RGBA", out_size, (0, 0, 0, 0))
    emblem.paste(Image.new("RGBA", out_size, black), (0, 0), cross_mask)   # saltire first
    emblem.paste(Image.new("RGBA", out_size, green), (0, 0), star_mask)    # trunk reads in front
    return emblem
