"""Download the authorized PC transaction register and its receipt evidence."""

import base64
import re
from html import escape
from io import BytesIO
from pathlib import Path

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, today
from frappe.utils.pdf import get_pdf
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.errors import PyPdfError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from requests import RequestException

from .pc_archive import _download_source
from .pc_funding import get_funding_cycles
from .pc_journal import archived_receipt_media, transaction_status_report


STATUS_COLORS = {
    "Posted": "#086553", "Pending Finance": "#37668d", "Rejected": "#a33139",
    "Pending Review": "#9a691a",
}
OTHER_STATUS_COLOR = "#596c7d"


def _rounded_footer_path(x, y, width, height, radius):
    right, top = x + width, y + height
    curve = radius * 0.55228475
    return (
        f"{x + radius} {y} m {right - radius} {y} l "
        f"{right - radius + curve} {y} {right} {y + radius - curve} {right} {y + radius} c "
        f"{right} {top - radius} l "
        f"{right} {top - radius + curve} {right - radius + curve} {top} {right - radius} {top} c "
        f"{x + radius} {top} l "
        f"{x + radius - curve} {top} {x} {top - radius + curve} {x} {top - radius} c "
        f"{x} {y + radius} l "
        f"{x} {y + radius - curve} {x + radius - curve} {y} {x + radius} {y} c h"
    )


def _status_dot(row):
    color = STATUS_COLORS.get(row["finance_status"], OTHER_STATUS_COLOR)
    return f'<span class="dot" style="background:{color}"></span>{escape(_status(row))}'


def _attachment_page(page):
    """Keep the attachment's visible bounds and add a strip below it for numbering."""
    if page.rotation:
        page.transfer_rotation_to_content()
    left, bottom, right, top = map(float, page.cropbox)
    wrapped = PageObject.create_blank_page(width=right - left, height=top - bottom + 24)
    wrapped.merge_transformed_page(page, Transformation().translate(-left, 24 - bottom))
    return wrapped


def _number_pages(writer):
    """Stamp the final page order after receipts and exception tables are assembled."""
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    total = len(writer.pages)
    for index, page in enumerate(writer.pages):
        if page.rotation:
            page.transfer_rotation_to_content()
        left, bottom, right, _ = map(float, page.cropbox)
        width = right - left
        overlay = PageObject.create_blank_page(width=width, height=24)
        overlay[NameObject("/Resources")] = DictionaryObject({
            NameObject("/Font"): DictionaryObject({NameObject("/PCFooter"): font}),
        })
        label = f"{index + 1} / {total}"
        stream = DecodedStreamObject()
        # Mirror the SIG letter footer in the assembled PDF, where the final page count is known.
        font_size = min(8, width / (len(label) + 12))
        number_width = sum(0.556 if char.isdigit() else 0.278 for char in label) * font_size
        label_width = 2.28 * font_size
        padding = font_size * 0.85
        badge_width = label_width + number_width + 4 * padding
        badge_left = (width - badge_width) / 2
        split = badge_left + label_width + 2 * padding
        badge = _rounded_footer_path(badge_left, 4, badge_width, 14, 7)
        inset = min(36, width * 0.06)
        stream.set_data(
            (
                f"q 0.88 0.92 0.95 RG 0.5 w {inset} 21 m {width - inset} 21 l S "
                f"{badge} W n "
                f"0.93 0.96 0.98 rg {badge_left} 4 {badge_width} 14 re f "
                f"0.09 0.19 0.33 rg {split} 4 {number_width + 2 * padding} 14 re f "
                f"BT /PCFooter {font_size} Tf 0.28 0.37 0.45 rg "
                f"{badge_left + padding} 8.2 Td (Page) Tj ET "
                f"BT /PCFooter {font_size} Tf 1 1 1 rg {split + padding} 8.2 Td ({label}) Tj ET Q"
            ).encode("ascii")
        )
        overlay[NameObject("/Contents")] = stream
        page.merge_transformed_page(overlay, Transformation().translate(left, bottom), over=True)


def _filename(employee, period):
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", f"Petty Cash - {employee} - {period}")
    return f"{stem[:180].rstrip(' .')}.pdf"


def _status(row):
    return _({
        "Pending Review": "Pending Manager",
        "Pending Finance": "Finance",
        "Posted": "Approved",
        "Journal link mismatch": "Needs review",
        "Journal Cancelled": "Needs review",
        "No linked Journal Entry": "Needs review",
    }.get(row["finance_status"], row["finance_status"]))


def _cells(values):
    return "".join(f"<td>{escape(str(value))}</td>" for value in values)


def _media(row):
    if row["archive_status"] == "Archived":
        payload = archived_receipt_media(row["name"])
        return base64.b64decode(payload["data"], validate=True), payload["mime_type"]
    return _download_source(row["source_media_url"])


def _receipt_content(rows):
    sections, pdfs, unavailable, non_receipts = [], [], [], []
    for number, row in enumerate(rows, 1):
        title = f"#{number}"
        if row.get("is_non_receipt"):
            non_receipts.append((number, row))
            continue
        body = None
        narrow = False
        if row["source_media_url"] or row["archive_status"] == "Archived":
            try:
                raw, mime = _media(row)
                if mime == "application/pdf":
                    reader = PdfReader(BytesIO(raw))
                    if reader.is_encrypted or not len(reader.pages):
                        raise ValueError("Receipt PDF is encrypted or empty")
                    validated = PdfWriter()
                    for page in reader.pages:
                        validated.add_page(page, excluded_keys=("/Annots", "/AA", "/A"))
                    checked = BytesIO()
                    validated.write(checked)
                    checked.seek(0)
                    pdfs.append((title, PdfReader(checked), number, row))
                    body = f"<p>{escape(_('Original PDF is included at the end.'))}</p>"
                elif mime in {"image/jpeg", "image/png"}:
                    with Image.open(BytesIO(raw)) as original:
                        image = ImageOps.exif_transpose(original)
                        image.load()
                        narrow = image.width / image.height <= 0.57
                        normalized = BytesIO()
                        if mime == "image/jpeg":
                            image.convert("RGB").save(normalized, format="JPEG", quality=95)
                        else:
                            image.save(normalized, format="PNG")
                    encoded = base64.b64encode(normalized.getvalue()).decode("ascii")
                    body = f'<img src="data:{mime};base64,{encoded}" alt="{escape(title)}">'
            except (frappe.ValidationError, frappe.PermissionError, RequestException, PyPdfError,
                    ValueError, OSError, UnidentifiedImageError):
                pass
        if body is None:
            unavailable.append((number, row))
            continue
        date = escape(formatdate(row["transaction_date"]))
        amount = f'{row["amount"] or 0:,.2f}'
        category = escape(row["transaction_category"] or "—")
        details = (
            f'<div class="receipt-heading"><h2>{escape(title)}</h2>'
            f'<strong class="amount">{amount} <small>SAR</small></strong></div>'
            f'<div class="receipt-facts"><span class="date">{date}</span>'
            f'<span class="category">{category}</span>'
            f'<span class="status">{_status_dot(row)}</span></div>'
        )
        sections.append(
            f'<section class="receipt {"narrow" if narrow else "wide"}">'
            f'<div class="receipt-layout"><div class="details"><div class="receipt-card">{details}</div></div>'
            f'<div class="photo">{body}</div></div></section>'
        )
    return "".join(sections), pdfs, unavailable, non_receipts


def _register(rows):
    return "".join(
        "<tr>" + _cells((
            number, formatdate(row["transaction_date"]), row["transaction_category"] or "—",
            f'{row["amount"] or 0:,.2f}',
        )) + f"<td>{_status_dot(row)}</td></tr>"
        for number, row in enumerate(rows, 1)
    )


def _status_summary(rows):
    statuses = (
        ("Posted", "Approved"), ("Pending Finance", "Finance"),
        ("Rejected", "Rejected"), ("Pending Review", "Pending Manager"),
    )
    counts = dict.fromkeys(STATUS_COLORS, 0)
    other = 0
    for row in rows:
        status = row["finance_status"]
        if status in counts:
            counts[status] += 1
        else:
            other += 1
    groups = [(label, counts[key], STATUS_COLORS[key]) for key, label in statuses]
    if other:
        groups.append(("Needs review", other, OTHER_STATUS_COLOR))
    total = len(rows) or 1
    bars = "".join(
        f'<i style="width:{count / total * 100:.3f}%;background:{color}"></i>'
        for _, count, color in groups if count
    )
    cards = "".join(
        f'<div class="metric" style="color:{color}"><strong>{count}</strong>'
        f'<span>{escape(_(label))}</span></div>'
        for label, count, color in groups
    )
    return f'<div class="summary">{cards}</div><div class="bar">{bars}</div>'


def _unavailable_page(unavailable, title=None):
    if not unavailable:
        return ""
    columns = ("#", _("Date"), _("Category"), _("Amount (SAR)"), _("Status"))
    header = "".join(f"<th>{escape(col)}</th>" for col in columns)
    rows = "".join(
        "<tr>" + _cells((number, formatdate(row["transaction_date"]),
                         row["transaction_category"] or "—",
                         f'{row["amount"] or 0:,.2f}', _status(row))) + "</tr>"
        for number, row in unavailable
    )
    return (f'<section class="unavailable"><h2>{escape(title or _("Unavailable receipt files"))}</h2>'
            f'<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table></section>')


@frappe.whitelist(methods=["POST"])
def download_status_pdf(employee, scope="all", from_date=None, to_date=None, cycle_key=None):
    if not employee or scope not in {"all", "range", "cycle"}:
        frappe.throw(_("Choose an employee and a report period."))
    args = {"employee": employee}
    if scope == "range":
        if not from_date or not to_date or getdate(from_date) > getdate(to_date):
            frappe.throw(_("Choose a valid start and end date."))
        args.update(from_date=getdate(from_date).isoformat(), to_date=getdate(to_date).isoformat())
    elif scope == "cycle":
        if not cycle_key:
            frappe.throw(_("Select a petty cash cycle."))
        args["cycle_key"] = cycle_key

    rows = transaction_status_report(**args)
    if not rows:
        frappe.throw(_("No transactions match this selection."))
    employee_name = rows[0]["employee_name"]
    cycles = get_funding_cycles(employee) if rows[0]["employee_id"] else []
    if scope == "cycle":
        cycles = [cycle for cycle in cycles if cycle["cycle_key"] == cycle_key]
        if not cycles:
            frappe.throw(_("The funding cycle is no longer available."))
        cycle = cycles[0]
        funding_date, end_date = cycle["funding_date"], cycle["end_date"]
        period = _("Cycle {0} to {1}").format(formatdate(funding_date), formatdate(end_date) if end_date else _("Current"))
        filename_period = f"Cycle {funding_date} to {end_date or _('Current')} - {cycle_key[:8]}"
    elif scope == "range":
        period = f'{formatdate(args["from_date"])} – {formatdate(args["to_date"])}'
        filename_period = f'{args["from_date"]} to {args["to_date"]}'
    else:
        period = filename_period = _("All dates")

    receipts, pdfs, unavailable, non_receipts = _receipt_content(rows)
    logo_path = Path(__file__).resolve().parents[1] / "public" / "images" / "pc-report-logo.png"
    logo = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    columns = ("#", _("Date"), _("Category"), _("Amount (SAR)"), _("Status"))
    document_start = f"""<!doctype html><html dir="{'rtl' if (frappe.local.lang or '').startswith('ar') else 'ltr'}">
    <head><meta charset="utf-8"><style>
    body {{ font-family: sans-serif; font-size: 10pt; color: #173153; }}
    .cover {{ display: table; width: 100%; }}
    .cover > div {{ display: table-cell; vertical-align: middle; }}
    .cover img {{ width: 45mm; vertical-align: middle; }}
    .cover .report-title {{ font-size: 15pt; font-weight: bold; text-align: end; }}
    .brand-rule {{ margin: 3mm 0; height: 1mm; background: #1682b6;
        background: -webkit-linear-gradient(left, #135b94, #39c4de); }}
    .employee {{ margin: 3mm 0 1.5mm; font-size: 24pt; line-height: 1.15; }}
    .report-meta {{ display: table; table-layout: fixed; width: 100%; background: #f3f7fb; }}
    .report-meta > div {{ display: table-cell; padding: 2mm 3mm; border-right: 1px solid #fff; }}
    .report-meta > div:first-child {{ width: 38%; }}
    .report-meta > div:last-child {{ width: 28%; }}
    .report-meta small {{ display: block; color: #465c70; }}
    table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 10pt; }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; }}
    td, th {{ border-bottom: 1px solid #dce5ef; text-align: start; padding: 4px; overflow-wrap: break-word; }}
    th {{ background: #e5eff7; }}
    tbody tr:nth-child(even) {{ background: #f6f9fc; }}
    .section-title {{ margin: 4mm 0 1.8mm; font-size: 12pt; }}
    .bar {{ width: 100%; height: 2.5mm; margin: 1mm 0 3mm; font-size: 0; white-space: nowrap; }}
    .bar i {{ display: inline-block; height: 2.5mm; }}
    .summary {{ display: table; table-layout: fixed; width: 100%; border-spacing: 1mm 0; }}
    .metric {{ display: table-cell; padding: 1mm 2mm 1.8mm; border-top: 0.7mm solid currentColor;
        background: #f3f7fb; text-align: center; vertical-align: top; }}
    .metric strong {{ display: block; font-size: 23pt; line-height: 1.15; }}
    .metric span {{ display: block; font-size: 9pt; font-weight: bold; }}
    .receipt {{ page-break-before: always; page-break-inside: avoid; }}
    .receipt h2 {{ margin: 0; font-size: 19pt; }}
    .amount {{ font-size: 20pt; white-space: nowrap; }}
    .amount small {{ font-size: 10pt; }}
    .date {{ color: #18587b; font-weight: bold; }}
    .dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin: 0 5px; }}
    .receipt-card {{ background: #edf4fa; border-top: 1mm solid #1682b6; padding: 3mm; overflow-wrap: break-word; }}
    .receipt-heading, .receipt-facts {{ display: table; width: 100%; }}
    .receipt-heading > *, .receipt-facts > * {{ display: table-cell; vertical-align: baseline; }}
    .receipt-facts {{ margin-top: 2mm; font-size: 11pt; }}
    .receipt.wide .amount, .receipt.wide .status {{ text-align: end; }}
    .receipt.wide .category {{ text-align: center; }}
    .receipt .photo {{ text-align: center; background: #f4f8fb; }}
    .receipt img {{ vertical-align: top; width: auto; max-width: 100%; max-height: 100%; }}
    .receipt.narrow .receipt-layout {{ display: table; table-layout: fixed; width: 100%; }}
    .receipt.narrow .details, .receipt.narrow .photo {{ display: table-cell; vertical-align: top; }}
    .receipt.narrow .details {{ width: 23%; box-sizing: border-box; }}
    .receipt.narrow .photo {{ padding: 0 2mm; }}
    .receipt.narrow img {{ max-height: 247mm; }}
    .receipt.narrow .receipt-heading > *, .receipt.narrow .receipt-facts > * {{ display: block; margin-bottom: 2mm; }}
    .receipt.narrow .receipt-facts > :last-child {{ margin-bottom: 0; }}
    .receipt.wide .photo {{ margin-top: 3mm; height: 226mm; }}
    .unavailable h2 {{ border-bottom: 1mm solid #1682b6; padding-bottom: 2mm; }}
    .unavailable + .unavailable {{ page-break-before: always; }}
    </style></head><body>"""
    html = document_start + f"""
    <header class="cover"><div><img src="data:image/png;base64,{logo}" alt="SIG"></div>
    <div class="report-title">{escape(_('Petty Cash Report'))}</div></header>
    <div class="brand-rule"></div>
    <h1 class="employee">{escape(employee_name)}</h1>
    <div class="report-meta">
      <div><small>{escape(_('Period'))}</small><strong>{escape(period)}</strong></div>
      <div><small>{escape(_('Generated'))}</small><strong>{escape(formatdate(today()))}</strong></div>
      <div><small>{escape(_('Recorded total (SAR)'))}</small>
      <strong>{sum(row["amount"] or 0 for row in rows):,.2f}</strong></div>
    </div>
    <h2 class="section-title">{escape(_('Status overview'))} · {len(rows)}</h2>
    {_status_summary(rows)}
    <h2 class="section-title">{escape(_('Transaction register'))}</h2>
    <table><thead><tr>{''.join(f'<th>{escape(col)}</th>' for col in columns)}</tr></thead>
    <tbody>{_register(rows)}</tbody></table>
    {receipts}</body></html>"""
    writer = PdfWriter()
    get_pdf(html, options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    for title, reader, number, row in pdfs:
        first_page = len(writer.pages)
        try:
            for page in reader.pages:
                writer.add_page(_attachment_page(page))
            writer.add_outline_item(title, first_page)
        except (PyPdfError, ValueError, OSError, KeyError, IndexError):
            while len(writer.pages) > first_page:
                del writer.pages[-1]
            unavailable.append((number, row))
    appendix = _unavailable_page(unavailable) + _unavailable_page(non_receipts, _("Non-receipt transactions"))
    if appendix:
        get_pdf(document_start + appendix + "</body></html>",
                options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    output = BytesIO()
    _number_pages(writer)
    writer.write(output)
    frappe.local.response.update(filename=_filename(employee_name, filename_period),
                                 filecontent=output.getvalue(), type="download", content_type="application/pdf")
