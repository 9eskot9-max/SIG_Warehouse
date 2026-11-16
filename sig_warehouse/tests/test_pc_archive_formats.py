"""Archive format compatibility without contacting the VPS or writing ERP data."""
import base64
import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest
from cryptography.fernet import Fernet


@pytest.fixture
def archive(monkeypatch):
    frappe = types.ModuleType("frappe")
    frappe.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
    monkeypatch.setitem(sys.modules, "frappe", frappe)
    path = Path(__file__).parents[1] / "sig_warehouse" / "pc_archive.py"
    spec = importlib.util.spec_from_file_location("pc_archive_format_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("plain", [True, False])
def test_archive_reads_plain_and_legacy_encrypted_receipts(archive, monkeypatch, plain):
    raw = b"\xff\xd8\xffreceipt bytes"
    cipher = Fernet(Fernet.generate_key())
    payload = raw if plain else cipher.encrypt(raw)
    class Response:
        status_code = 200
        def iter_content(self, _): return [payload]
        def close(self): pass
    monkeypatch.setattr(archive, "_request", lambda *a, **k: Response())
    doc = types.SimpleNamespace(sync_archive_locator="https://sigtele.com/pc-archive/files/Cases/EMP/2026/11/id" + (".plain.enc" if plain else ".enc"),
                                archive_sha256=hashlib.sha256(raw).hexdigest())
    result = archive._read_archive(doc, None, "https://sigtele.com/pc-archive", "token", cipher)
    assert base64.b64decode(result["data"]) == raw
    doc.archive_sha256 = "0" * 64
    with pytest.raises(ValueError, match="checksum"):
        archive._read_archive(doc, None, "https://sigtele.com/pc-archive", "token", cipher)
