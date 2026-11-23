"""Download the authorized PC transaction register and its receipt evidence."""

import base64
import re
from html import escape
from io import BytesIO

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, today
from frappe.utils.pdf import get_pdf
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
    return _("Pending Manager") if row["finance_status"] == "Pending Review" else _(row["finance_status"])


def _cells(values):
    return "".join(f"<td>{escape(str(value))}</td>" for value in values)


def _media(row):
    if row["archive_status"] == "Archived":
        payload = archived_receipt_media(row["name"])
        return base64.b64decode(payload["data"], validate=True), payload["mime_type"]
    return _download_source(row["source_media_url"])


def _receipts(rows):
    sections, pdfs = [], []
    for number, row in enumerate(rows, 1):
        title = _("Receipt {0}").format(number)
        details = " · ".join((formatdate(row["transaction_date"]), f'{row["amount"] or 0:,.2f} SAR', _status(row)))
        body = f"<p>{escape(_('Receipt file unavailable.'))}</p>"
        if row["source_media_url"] or row["archive_status"] == "Archived":
            try:
                raw, mime = _media(row)
                if mime == "application/pdf":
                    reader = PdfReader(BytesIO(raw))
                    if reader.is_encrypted or not len(reader.pages):
                        raise ValueError("Receipt PDF is encrypted or empty")
                    pdfs.append((title, reader))
                    body = f"<p>{escape(_('The original PDF pages are included at the end of this report.'))}</p>"
                elif mime in {"image/jpeg", "image/png"}:
                    encoded = base64.b64encode(raw).decode("ascii")
                    body = f'<img src="data:{mime};base64,{encoded}" alt="{escape(title)}">'
            except (frappe.ValidationError, frappe.PermissionError, RequestException, PyPdfError, ValueError):
                pass
        sections.append(f'<section class="receipt"><h2>{escape(title)}</h2><p>{escape(details)}</p>{body}</section>')
    return "".join(sections), pdfs


def _register(rows, cycles, scope):
    parts = []
    groups = {cycle["cycle_key"]: [] for cycle in cycles}
    for number, row in enumerate(rows, 1):
        parts.append("<tr>" + _cells((
            number, formatdate(row["transaction_date"]), row["transaction_category"] or "—",
            f'{row["amount"] or 0:,.2f}', _status(row), row["reviewed_by"] or "—",
            _(row["journal_status"]), _(row["cycle_label"]),
        )) + "</tr>")
        if row["cycle_key"] in groups:
            groups[row["cycle_key"]].append(row)
    for cycle in cycles:
        members = groups[cycle["cycle_key"]]
        if not members and scope != "cycle":
            continue
        principal = float(cycle["principal"] or 0)
        approved = sum(float(row["amount"] or 0) for row in members if row["review_status"] == "Closed")
        parts.append('<tr class="cycle">' + _cells((
            "—", formatdate(cycle["funding_date"]), _("PC Top-up"), f"{principal:,.2f}",
            _("Approved in report: {0} SAR").format(f"{approved:,.2f}"), "—", _(cycle["journal_status"]),
            _("Balance after included approvals: {0} SAR").format(f"{principal - approved:,.2f}"),
        )) + "</tr>")
    return "".join(parts)


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

    receipts, pdfs = _receipts(rows)
    columns = ("#", _("Date"), _("Category"), _("Amount (SAR)"), _("Status"),
               _("Approved by"), _("Journal Entry status"), _("Petty Cash cycle"))
    html = f"""<!doctype html><html dir="{'rtl' if (frappe.local.lang or '').startswith('ar') else 'ltr'}">
    <head><meta charset="utf-8"><style>
    body {{ font-family: sans-serif; font-size: 10pt; color: #173153; }}
    h1 {{ border-bottom: 2px solid #173153; padding-bottom: 8px; }}
    table {{ width: 100%; table-layout: fixed; border-collapse: collapse; font-size: 7pt; }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; }}
    td, th {{ border-bottom: 1px solid #dce5ef; text-align: start; padding: 4px; overflow-wrap: break-word; }}
    th, .cycle {{ background: #edf4fa; }}
    .receipt {{ page-break-before: always; }}
    .receipt img {{ display: block; max-width: 100%; max-height: 210mm; margin: auto; }}
    </style></head><body>
    <h1>SIG · {escape(_('Petty Cash Transaction Status'))}</h1>
    <p><strong>{escape(employee_name)}</strong> · {escape(period)} · {escape(formatdate(today()))}</p>
    <table><thead><tr>{''.join(f'<th>{escape(col)}</th>' for col in columns)}</tr></thead>
    <tbody>{_register(rows, cycles, scope)}</tbody></table>
    <p><strong>{escape(_('Receipt total (SAR)'))} {sum(row["amount"] or 0 for row in rows):,.2f}</strong></p>
    {receipts}</body></html>"""
    writer = PdfWriter()
    get_pdf(html, options={"orientation": "Portrait", "page-size": "A4"}, output=writer)
    for title, reader in pdfs:
        first_page = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page, excluded_keys=("/Annots", "/AA", "/A"))
        writer.add_outline_item(title, first_page)
    output = BytesIO()
    writer.write(output)
    frappe.local.response.update(filename=_filename(employee_name, filename_period),
                                 filecontent=output.getvalue(), type="download", content_type="application/pdf")
