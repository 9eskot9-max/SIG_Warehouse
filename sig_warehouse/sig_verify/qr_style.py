"""SIG signature-style QR renderer (the approved design).

Ported from ERPNext/docs/invoice_qr_signature_renderer.py so the app is self-contained:
    * liquid data field - adjacent dark modules fuse into continuous ribbons with concave fillets;
    * diagonal gradient - a calm navy sweep, even contrast for print and low light;
    * engineered finder eyes - squircle frames with one chamfered corner, a squircle ball;
    * 4x supersampling for true antialiasing;
    * centre mark (the SIG emblem) in a rectangular clear-space snapped to whole modules.

The payload is encoded before any styling runs and styling never touches it. Verification links are
short (about 55 characters), so error correction M keeps modules large and the symbol easy to scan.

Matrix source: ``qrcode`` when installed, otherwise ``pyqrcode`` (shipped with Frappe).
Only Pillow is needed to draw. Pure Python (no frappe import).
"""

import io
import math

from PIL import Image, ImageChops, ImageDraw

from .emblem import render_emblem_image

QR_BOX_SIZE = 16
QR_BORDER_MODULES = 4
SUPERSAMPLE = 4

MODULE_SHRINK = 0.06
MODULE_RADIUS = 0.50
FILLET_RADIUS = 0.20          # above 0.25 decoders stop reading

GRADIENT_START = (37, 106, 163)
GRADIENT_END = (7, 34, 58)
QR_BACKGROUND = (255, 255, 255)
FINDER_FRAME_COLOR = (10, 42, 69)
FINDER_BALL_COLOR = (46, 125, 190)

EYE_OUTER_RADIUS = 1.85
EYE_CHAMFER = 1.55
EYE_STROKE = 1.0
EYE_BALL_RADIUS = 0.62

LOGO_FRACTION_DEFAULT = 0.24
LOGO_CLEARSPACE_FRACTION = 0.055


def render_png(payload, centre_mark=True):
    """Render ``payload`` in the signature style and return PNG bytes."""
    image = render_image(payload, centre_mark=centre_mark)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True)
    return out.getvalue()


def render_image(payload, centre_mark=True, logo_fraction=LOGO_FRACTION_DEFAULT):
    if centre_mark and logo_fraction > 0.26:
        raise ValueError("logo_fraction above 0.26 is not recommended for scanning")

    matrix = _matrix(payload)
    n = len(matrix)
    s = QR_BOX_SIZE * SUPERSAMPLE
    size = (n * s, n * s)
    border = QR_BORDER_MODULES

    mask = Image.new("L", size, 0)
    _draw_liquid_field(ImageDraw.Draw(mask), matrix, _finder_cells(n, border), s)
    eyes = _finder_eye_frame(size, n, border, s)
    balls = Image.new("L", size, 0)
    _draw_finder_balls(ImageDraw.Draw(balls), n, border, s)

    image = Image.new("RGB", size, QR_BACKGROUND)
    image.paste(_linear_gradient(size, GRADIENT_START, GRADIENT_END), (0, 0), mask)
    image.paste(Image.new("RGB", size, FINDER_FRAME_COLOR), (0, 0), eyes)
    image.paste(Image.new("RGB", size, FINDER_BALL_COLOR), (0, 0), balls)

    image = image.resize((n * QR_BOX_SIZE, n * QR_BOX_SIZE), Image.Resampling.LANCZOS)
    if centre_mark:
        _paste_logo(image, render_emblem_image(), logo_fraction)
    return image


def _matrix(payload):
    """Module matrix including the quiet zone."""
    try:
        import qrcode
    except ImportError:
        qrcode = None
    if qrcode is not None:
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                           box_size=1, border=QR_BORDER_MODULES)
        qr.add_data(payload)
        qr.make(fit=True)
        return [[bool(c) for c in row] for row in qr.get_matrix()]

    import pyqrcode

    code = pyqrcode.create(payload, error="M").code
    b = QR_BORDER_MODULES
    width = len(code) + 2 * b
    blank = [False] * width
    rows = [blank[:] for _ in range(b)]
    for row in code:
        rows.append([False] * b + [bool(c) for c in row] + [False] * b)
    rows.extend(blank[:] for _ in range(b))
    return rows


def _draw_liquid_field(draw, matrix, finder_cells, s):
    n = len(matrix)

    def dark(r, c):
        return 0 <= r < n and 0 <= c < n and matrix[r][c] and (r, c) not in finder_cells

    inset = MODULE_SHRINK * s
    radius = MODULE_RADIUS * s
    for row in range(n):
        for col in range(n):
            if not dark(row, col):
                continue
            x0, y0 = col * s, row * s
            up, down = dark(row - 1, col), dark(row + 1, col)
            left, right = dark(row, col - 1), dark(row, col + 1)
            lft = x0 - 1 if left else x0 + inset
            rgt = x0 + s if right else x0 + s - inset
            top = y0 - 1 if up else y0 + inset
            bot = y0 + s if down else y0 + s - inset
            corners = (not (up or left), not (up or right), not (down or right), not (down or left))
            rad = max(0, min(radius, (rgt - lft) / 2 - 1, (bot - top) / 2 - 1))
            draw.rounded_rectangle((lft, top, rgt, bot), radius=rad, fill=255, corners=corners)

    fr = FILLET_RADIUS * s
    for row in range(n):
        for col in range(n):
            if dark(row, col):
                continue
            x0, y0 = col * s, row * s
            for dr, dc in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
                if not (dark(row + dr, col) and dark(row, col + dc) and dark(row + dr, col + dc)):
                    continue
                cx = x0 + (0 if dc < 0 else s)
                cy = y0 + (0 if dr < 0 else s)
                draw.polygon(_fillet_wedge(cx, cy, dc, dr, fr), fill=255)


def _fillet_wedge(cx, cy, dc, dr, fr, steps=10):
    ax, ay = cx + dc * fr, cy
    bx, by = cx, cy + dr * fr
    hx, hy = cx + dc * fr, cy + dr * fr
    points = [(cx, cy), (ax, ay)]
    start = math.atan2(ay - hy, ax - hx)
    stop = math.atan2(by - hy, bx - hx)
    if dc * dr > 0:
        start, stop = stop, start
    sweep = (stop - start) % (2 * math.pi)
    if sweep > math.pi:
        sweep -= 2 * math.pi
    for i in range(1, steps + 1):
        a = start + sweep * i / steps
        points.append((hx + fr * math.cos(a), hy + fr * math.sin(a)))
    return points


def _finder_origins(n, border):
    far = n - border - 7
    return ((border, border), (border, far), (far, border))


def _finder_cells(n, border):
    cells = set()
    for row, col in _finder_origins(n, border):
        for dr in range(7):
            for dc in range(7):
                cells.add((row + dr, col + dc))
    return cells


def _finder_eye_frame(size, n, border, s):
    """Squircle frame with the outward corner chamfered, as a mask image."""
    stroke = EYE_STROKE * s
    outer = Image.new("L", size, 0)
    inner = Image.new("L", size, 0)
    d_out, d_in = ImageDraw.Draw(outer), ImageDraw.Draw(inner)
    for row, col in _finder_origins(n, border):
        x0, y0 = col * s, row * s
        x1, y1 = x0 + 7 * s, y0 + 7 * s
        outward = _outward_corner(row, col, border)
        _chamfered_square(d_out, (x0, y0, x1, y1), EYE_OUTER_RADIUS * s, outward, EYE_CHAMFER * s)
        _chamfered_square(d_in, (x0 + stroke, y0 + stroke, x1 - stroke, y1 - stroke),
                          EYE_OUTER_RADIUS * s - stroke, outward, EYE_CHAMFER * s - stroke)
    return ImageChops.subtract(outer, inner)


def _chamfered_square(draw, box, radius, chamfer, cut):
    x0, y0, x1, y1 = box
    radius = max(0.0, min(radius, (x1 - x0) / 2 - 1, (y1 - y0) / 2 - 1))
    draw.rounded_rectangle((x0, y0, x1, y1), radius=radius, fill=255)
    cut = max(0.0, min(cut, (x1 - x0) / 2))
    if cut <= 0:
        return
    corner_box = {"nw": (x0, y0, x0 + cut, y0 + cut), "ne": (x1 - cut, y0, x1, y0 + cut),
                  "se": (x1 - cut, y1 - cut, x1, y1), "sw": (x0, y1 - cut, x0 + cut, y1)}[chamfer]
    draw.rectangle(corner_box, fill=255)
    triangle = {"nw": ((x0, y0), (x0 + cut, y0), (x0, y0 + cut)),
                "ne": ((x1, y0), (x1 - cut, y0), (x1, y0 + cut)),
                "se": ((x1, y1), (x1 - cut, y1), (x1, y1 - cut)),
                "sw": ((x0, y1), (x0 + cut, y1), (x0, y1 - cut))}[chamfer]
    draw.polygon(triangle, fill=0)


def _draw_finder_balls(draw, n, border, s):
    for row, col in _finder_origins(n, border):
        draw.rounded_rectangle(((col + 2) * s, (row + 2) * s, (col + 5) * s, (row + 5) * s),
                               radius=EYE_BALL_RADIUS * s, fill=255)


def _outward_corner(row, col, border):
    top = row == border
    lefthand = col == border
    return "nw" if top and lefthand else "ne" if top else "sw"


def _linear_gradient(size, start, end):
    small = Image.new("RGB", (64, 64))
    px = small.load()
    for y in range(64):
        for x in range(64):
            t = (x + y) / 126.0
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(start, end))
    return small.resize(size, Image.Resampling.BICUBIC)


def _trim_logo(mark):
    """Crop transparent / near-white canvas around the logo."""
    rgba = mark.convert("RGBA")
    px = rgba.load()
    keep = Image.new("L", rgba.size, 0)
    mask_px = keep.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a > 12 and (r < 245 or g < 245 or b < 245):
                mask_px[x, y] = 255
    bbox = keep.getbbox()
    return rgba.crop(bbox) if bbox else rgba


def _paste_logo(image, mark_image, logo_fraction):
    """Centre mark in a plain rectangular clear-space snapped to whole modules."""
    mark = _trim_logo(mark_image)
    side = max(1, int(image.width * logo_fraction))
    mark.thumbnail((side, side), Image.Resampling.LANCZOS)
    pad = max(3, int(max(mark.size) * LOGO_CLEARSPACE_FRACTION))

    box = QR_BOX_SIZE
    left = ((image.width - mark.width) // 2 - pad) // box * box
    top = ((image.height - mark.height) // 2 - pad) // box * box
    right = -(-((image.width + mark.width) // 2 + pad) // box) * box
    bottom = -(-((image.height + mark.height) // 2 + pad) // box) * box

    image.paste(Image.new("RGB", (right - left, bottom - top), QR_BACKGROUND), (left, top))
    image.paste(mark, ((image.width - mark.width) // 2, (image.height - mark.height) // 2), mark)
