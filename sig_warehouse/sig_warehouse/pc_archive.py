"""Private, idempotent receipt media transfer to the SIG PC archive."""

import base64
import hashlib
import re
from urllib.parse import unquote, urljoin, urlparse

import frappe
import requests
from cryptography.fernet import Fernet, InvalidToken


MAX_MEDIA_BYTES = 10 * 1024 * 1024
SOURCE_HOST = "cdnydm.com"
ARCHIVE_HOST = "sigtele.com"
TRANSACTION = "SIG PC Transaction"


def _archive_config():
    base = str(frappe.conf.get("sig_pc_archive_url") or "https://sigtele.com/pc-archive").rstrip("/")
    parsed = urlparse(base)
    token = str(frappe.conf.get("sig_pc_archive_token") or "")
    key = str(frappe.conf.get("encryption_key") or "")
    if (parsed.scheme != "https" or parsed.hostname != ARCHIVE_HOST
            or parsed.port not in (None, 443) or parsed.path != "/pc-archive"):
        frappe.throw("Petty-cash archive URL is not configured to the approved HTTPS endpoint.")
    if not token:
        frappe.throw("Petty-cash archive credentials are not configured; receipt confirmation is held.")
    if not key:
        frappe.throw("ERP encryption key is unavailable; receipt confirmation is held.")
    try:
        cipher = Fernet(key.encode("ascii"))
    except Exception:
        frappe.throw("ERP encryption key is invalid; receipt confirmation is held.")
    return base, token, cipher


def _media_type(raw):
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"%PDF-"):
        return "application/pdf"
    frappe.throw("Receipt source is not a supported image or PDF.")


def _allowed_source_url(value):
    parsed = urlparse(str(value or ""))
    host = (parsed.hostname or "").lower().rstrip(".")
    return (parsed.scheme == "https" and parsed.port in (None, 443)
            and (host == SOURCE_HOST or host.endswith("." + SOURCE_HOST))
            and not parsed.username and not parsed.password)


def _download_source(url):
    if not _allowed_source_url(url):
        frappe.throw("Receipt source must be an HTTPS cdnydm.com media link.")
    current = url
    response = None
    for _ in range(4):
        if not _allowed_source_url(current):
            frappe.throw("Receipt source redirected outside the approved media host.")
        try:
            response = requests.get(current, timeout=(8, 25), stream=True, allow_redirects=False,
                                    headers={"User-Agent": "SIG-PC-Archive/1.0"})
        except requests.RequestException:
            frappe.throw("Receipt image could not be fetched from its source.")
        if response.is_redirect or response.is_permanent_redirect:
            target = urljoin(current, response.headers.get("Location", ""))
            response.close()
            current = target
            continue
        if response.status_code != 200:
            response.close()
            frappe.throw("Receipt image could not be fetched from its source.")
        chunks, size = [], 0
        try:
            for chunk in response.iter_content(64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_MEDIA_BYTES:
                    frappe.throw("Receipt image exceeds the 10 MB archive limit.")
                chunks.append(chunk)
        finally:
            response.close()
        raw = b"".join(chunks)
        if not raw:
            frappe.throw("Receipt source returned an empty file.")
        return raw, _media_type(raw)
    frappe.throw("Receipt source redirected too many times.")


def _safe_source_id(doc):
    value = str(doc.source_id or doc.name or "")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", value)
    if not safe or safe in (".", "..") or len(safe) > 116:
        frappe.throw("Receipt source ID cannot be archived safely.")
    return value, safe


def _request(method, url, token, *, params=None, data=None, timeout=(8, 35)):
    try:
        response = requests.request(method, url, params=params, data=data,
                                     headers={"Authorization": "Bearer " + token,
                                              "User-Agent": "SIG-PC-Archive/1.0"},
                                     timeout=timeout, allow_redirects=False,
                                     stream=method.upper() == "GET")
    except requests.RequestException:
        frappe.throw("Petty-cash archive service could not be reached.")
    if response.is_redirect:
        response.close()
        frappe.throw("Petty-cash archive service redirected an authenticated request.")
    return response


def _locator_url(base, locator):
    parsed = urlparse(str(locator or ""))
    segments = [unquote(part) for part in parsed.path.split("/") if part]
    if (parsed.scheme != "https" or parsed.hostname != ARCHIVE_HOST or parsed.port not in (None, 443)
            or not parsed.path.startswith("/pc-archive/files/Cases/")
            or parsed.query or parsed.fragment or len(segments) != 7
            or any(part in (".", "..") or not re.fullmatch(r"[A-Za-z0-9._-]+", part) for part in segments)):
        frappe.throw("Archive service returned an invalid receipt locator.")
    return "https://" + ARCHIVE_HOST + parsed.path


def _bounded_response_bytes(response, limit):
    chunks, size = [], 0
    for chunk in response.iter_content(64 * 1024):
        if not chunk:
            continue
        size += len(chunk)
        if size > limit:
            frappe.throw("Archived receipt exceeds the archive read limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _read_archive(doc, employee, base, token, cipher):
    locator = str(doc.sync_archive_locator or "")
    if not locator or not doc.archive_sha256:
        frappe.throw("Receipt has no verified archive object.")
    url = _locator_url(base, locator)
    response = _request("GET", url, token, timeout=(8, 35))
    try:
        if response.status_code != 200:
            frappe.throw("Archived receipt could not be read back from the VPS.")
        encrypted = _bounded_response_bytes(response, 15 * 1024 * 1024)
    finally:
        response.close()
    try:
        raw = cipher.decrypt(encrypted)
    except InvalidToken:
        frappe.throw("Archived receipt failed its encryption integrity check.")
    digest = hashlib.sha256(raw).hexdigest()
    if not hmac_compare(digest, str(doc.archive_sha256)):
        frappe.throw("Archived receipt checksum does not match its saved verification value.")
    return {"mime_type": _media_type(raw), "data": base64.b64encode(raw).decode("ascii"),
            "sha256": digest}


def hmac_compare(left, right):
    # Avoid timing differences when comparing an authenticated media digest.
    import hmac
    return hmac.compare_digest(left, right)


def _set_state(doc, status, *, locator=None, sha256=None, error=None, attempts=None):
    values = {"archive_status": status}
    if locator is not None:
        values["sync_archive_locator"] = locator
    if sha256 is not None:
        values["archive_sha256"] = sha256
    if error is not None:
        values["last_archive_error"] = str(error)[:2000]
    if attempts is not None:
        values["archive_attempts"] = attempts
    frappe.db.set_value(TRANSACTION, doc.name, values, update_modified=False)
    for field, value in values.items():
        doc.set(field, value)


def ensure_archived(doc, employee, *, commit_state=True):
    """Fetch, encrypt, upload, and read back before a receipt is confirmed."""
    if doc.sync_archive_locator and doc.archive_sha256:
        try:
            base, token, cipher = _archive_config()
            _read_archive(doc, employee, base, token, cipher)
            _set_state(doc, "Archived", error="")
            if commit_state:
                frappe.db.commit()
            return
        except Exception as exc:
            _set_state(doc, "Failed", error=str(exc).strip()[:2000])
            frappe.db.commit()
            raise

    attempts = int(doc.archive_attempts or 0) + 1
    _set_state(doc, "Processing", error="", attempts=attempts)
    if commit_state:
        frappe.db.commit()
    try:
        base, token, cipher = _archive_config()
        if not doc.source_media_url:
            frappe.throw("Receipt has no source media URL to archive.")
        raw, mime = _download_source(doc.source_media_url)
        content_sha256 = hashlib.sha256(raw).hexdigest()
        encrypted = cipher.encrypt(raw)
        source_id, filename = _safe_source_id(doc)
        tx_date = str(doc.transaction_date or "")[:10]
        try:
            year, month, _day = tx_date.split("-")
            if len(year) != 4 or len(month) != 2:
                raise ValueError("date")
        except ValueError:
            frappe.throw("Receipt date is invalid for the archive path.")
        params = {"employee": employee.name, "year": year, "month": month,
                  "source_id": source_id, "filename": filename + ".enc",
                  "content_sha256": content_sha256, "mime_type": mime}
        response = _request("POST", base + "/upload", token, params=params, data=encrypted,
                            timeout=(8, 60))
        try:
            if response.status_code not in (200, 201):
                if response.status_code == 409:
                    frappe.throw("VPS refused a duplicate or conflicting source ID; receipt was not confirmed.")
                frappe.throw("VPS did not accept the receipt archive upload.")
            result = response.json()
        except ValueError:
            frappe.throw("VPS returned an invalid archive response.")
        finally:
            response.close()
        if not result.get("ok") or result.get("content_sha256") != content_sha256:
            frappe.throw("VPS archive response did not verify the source checksum.")
        locator = str(result.get("locator") or "")
        read_url = _locator_url(base, locator)
        readback = _request("GET", read_url, token, timeout=(8, 35))
        try:
            if readback.status_code != 200:
                frappe.throw("VPS archive upload was not readable on verification.")
            stored_encrypted = _bounded_response_bytes(readback, 15 * 1024 * 1024)
        finally:
            readback.close()
        try:
            verified = cipher.decrypt(stored_encrypted)
        except InvalidToken:
            frappe.throw("VPS archive read-back failed its encryption integrity check.")
        if hashlib.sha256(verified).hexdigest() != content_sha256 or _media_type(verified) != mime:
            frappe.throw("VPS archive read-back does not match the receipt source.")
        _set_state(doc, "Archived", locator=locator, sha256=content_sha256, error="")
        if commit_state:
            frappe.db.commit()
    except Exception as exc:
        message = str(exc).strip() or "Archive transfer failed."
        if len(message) > 2000:
            message = message[:2000]
        _set_state(doc, "Failed", error=message, attempts=attempts)
        frappe.db.commit()
        raise


def archived_media(doc, employee):
    """Return an authorized receipt image from the private encrypted archive."""
    base, token, cipher = _archive_config()
    return _read_archive(doc, employee, base, token, cipher)
