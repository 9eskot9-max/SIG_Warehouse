"""Download the authorized PC transaction register and its receipt evidence."""

import base64
import re
from html import escape
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, today
from frappe.utils.pdf import get_pdf
from PIL import Image, ImageOps, UnidentifiedImageError
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from requests import RequestException

from .pc_archive import _download_source
from .pc_funding import get_funding_cycles
from .pc_journal import archived_receipt_media, transaction_status_report


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
        title = _("Receipt {0}").format(number)
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
        status = escape(_status(row))
        status_color = {
            "Posted": "#086553", "Pending Finance": "#37668d", "Rejected": "#a33139",
            "Pending Review": "#9a691a",
        }.get(row["finance_status"], "#596c7d")
        details = (
            f'<h2>{escape(title)}</h2><strong class="amount">{amount} SAR</strong>'
            f'<p><b class="date">{date}</b></p>'
            f'<p>{category}</p><p><span class="dot" style="background:{status_color}"></span>{status}</p>'
        )
        sections.append(
            f'<section class="receipt {"narrow" if narrow else "wide"}">'
            f'<div class="details">{details}</div><div class="photo">{body}</div></section>'
        )
    return "".join(sections), pdfs, unavailable, non_receipts


def _register(rows):
    return "".join(
        "<tr>" + _cells((
            number, formatdate(row["transaction_date"]), row["transaction_category"] or "—",
            f'{row["amount"] or 0:,.2f}', _status(row),
        )) + "</tr>"
        for number, row in enumerate(rows, 1)
    )


def _status_summary(rows):
    names = ("Approved", "Finance", "Rejected", "Pending Manager")
    counts = {name: 0 for name in names}
    unknown = 0
    for row in rows:
        key = {
            "Posted": "Approved", "Pending Finance": "Finance",
            "Rejected": "Rejected", "Pending Review": "Pending Manager",
        }.get(row["finance_status"])
        if key:
            counts[key] += 1
        else:
            unknown += 1
    colors = ("#086553", "#37668d", "#a33139", "#9a691a")
    total = len(rows) or 1
    bars = "".join(
        f'<i style="width:{counts[name] / total * 100:.3f}%;background:{color}"></i>'
        for name, color in zip(names, colors) if counts[name]
    )
    if unknown:
        bars += f'<i style="width:{unknown / total * 100:.3f}%;background:#9aa9b5"></i>'
    parts = [f'<span><b>{escape(_(name))}</b> {counts[name]}</span>' for name in names]
    if unknown:
        parts.append(f'<span><b>{escape(_("Needs review"))}</b> {unknown}</span>')
    return '<div class="bar">' + bars + '</div><div class="summary">' + "".join(parts) + "</div>"


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
    columns = ("#", _("Date"), _("Category"), _("Amount (SAR)"), _("Status"))
    html = f"""<!doctype html><html dir="{'rtl' if (frappe.local.lang or '').startswith('ar') else 'ltr'}">
    <head><meta charset="utf-8"><style>
    body {{ font-family: sans-serif; font-size: 10pt; color: #173153; }}
    h1 {{ border-bottom: 2px solid #173153; padding-bottom: 8px; }}
    table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 10pt; }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; }}
    td, th {{ border-bottom: 1px solid #dce5ef; text-align: start; padding: 4px; overflow-wrap: break-word; }}
    th {{ background: #edf4fa; }}
    .bar {{ width: 100%; height: 7px; margin-top: 16px; font-size: 0; white-space: nowrap; }}
    .bar i {{ display: inline-block; height: 7px; }}
    .summary {{ display: table; width: 100%; margin: 16px 0; background: #edf4fa; }}
    .summary span {{ display: table-cell; padding: 8px; }}
    .summary b {{ display: block; }}
    .receipt {{ page-break-before: always; }}
    .receipt {{ min-height: 245mm; position: relative; }}
    .receipt h2 {{ margin: 0; font-size: 17pt; }}
    .receipt p {{ margin: 5px 0; font-size: 11pt; }}
    .receipt .amount {{ font-size: 16pt; }}
    .receipt .date {{ background: #e7f2f9; padding: 3px 6px; }}
    .receipt .dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 5px; }}
    .receipt .details {{ overflow-wrap: break-word; }}
    .receipt .photo {{ text-align: center; }}
    .receipt img {{ width: auto; max-width: 100%; max-height: 100%; }}
    .receipt.narrow .details {{ float: left; width: 24%; }}
    .receipt.narrow .photo {{ float: right; width: 75%; height: 250mm; }}
    .receipt.wide .details {{ min-height: 28mm; }}
    .receipt.wide .details h2 {{ display: inline-block; margin-right: 12px; }}
    .receipt.wide .details .amount {{ float: right; }}
    .receipt.wide .details p {{ display: inline-block; margin-right: 10px; }}
    .receipt.wide .photo {{ height: 230mm; }}
    </style></head><body>
    <h1>SIG · {escape(_('Petty Cash Transaction Status'))}</h1>
    <p><strong>{escape(employee_name)}</strong> · {escape(period)} · {escape(formatdate(today()))}</p>
    {_status_summary(rows)}
    <table><thead><tr>{''.join(f'<th>{escape(col)}</th>' for col in columns)}</tr></thead>
    <tbody>{_register(rows)}</tbody></table>
    <p><strong>{escape(_('Receipt total (SAR)'))} {sum(row["amount"] or 0 for row in rows):,.2f}</strong></p>
    {receipts}</body></html>"""
    writer = PdfWriter()
    get_pdf(html, options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    for title, reader, number, row in pdfs:
        first_page = len(writer.pages)
        try:
            for page in reader.pages:
                writer.add_page(page, excluded_keys=("/Annots", "/AA", "/A"))
            writer.add_outline_item(title, first_page)
        except (PyPdfError, ValueError, OSError, KeyError, IndexError):
            while len(writer.pages) > first_page:
                del writer.pages[-1]
            unavailable.append((number, row))
    if unavailable:
        get_pdf(f"<html><head><style>body {{ font-family: sans-serif; color: #173153; }} "
                f"table {{ width: 100%; border-collapse: collapse; font-size: 10pt; }} "
                f"td, th {{ border-bottom: 1px solid #dce5ef; padding: 7px; text-align: left; }} "
                f"th {{ background: #edf4fa; }}</style></head><body>{_unavailable_page(unavailable)}</body></html>",
                options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    if non_receipts:
        get_pdf(f"<html><head><style>body {{ font-family: sans-serif; }} "
                f"table {{ width: 100%; border-collapse: collapse; }} "
                f"td, th {{ border-bottom: 1px solid #dce5ef; padding: 7px; text-align: left; }}"
                f"</style></head><body>{_unavailable_page(non_receipts, _('Non-receipt transactions'))}</body></html>",
                options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    output = BytesIO()
    writer.write(output)
    frappe.local.response.update(filename=_filename(employee_name, filename_period),
                                 filecontent=output.getvalue(), type="download", content_type="application/pdf")
