import sys
import types
from types import SimpleNamespace

try:
    import frappe  # noqa: F401
except ImportError:
    frappe_stub = types.ModuleType("frappe")
    frappe_stub.whitelist = lambda *args, **kwargs: (lambda fn: fn)
    sys.modules["frappe"] = frappe_stub

from sig_warehouse.sig_warehouse import rollup


class RowDoc(dict):
    __getattr__ = dict.get


class FakeDb:
    def __init__(self, rows):
        self.rows = {row["name"]: dict(row) for row in rows}
        self.writes = []

    def get_value(self, doctype, name, fieldname):
        assert doctype == "Stock Entry Detail"
        return self.rows[name].get(fieldname)

    def set_value(self, doctype, name, fieldname, value, update_modified=True):
        assert doctype == "Stock Entry Detail"
        assert update_modified is False
        self.rows[name][fieldname] = value
        self.writes.append((name, fieldname, value))


class FakeFrappe:
    def __init__(self, rows):
        self.db = FakeDb(rows)

    def get_all(self, doctype, filters=None, fields=None, **_kwargs):
        assert doctype == "Stock Entry Detail"
        rows = [
            row for row in self.db.rows.values()
            if row.get("parent") == filters["parent"]
            and row.get("parenttype") == filters["parenttype"]
        ]
        return [SimpleNamespace(**{field: row.get(field) for field in fields}) for row in rows]

    def clear_document_cache(self, *_args, **_kwargs):
        pass


def _source_line(name, parent, row_key="CUC-1"):
    return {
        "name": name, "parent": parent, "parenttype": "Stock Entry",
        "item_code": "ITEM-1", "qty": 10, "uom": "Nos", "custom_site": "SITE-1",
        "project": "PROJ-1", "material_request": "MR-1", "custom_row_key": row_key,
        "custom_qty_custody": 0, "custom_qty_returned": 0,
        "custom_return_closed": 0,
    }


def test_return_submit_and_cancel_update_only_the_linked_dn(monkeypatch):
    fake = FakeFrappe([_source_line("A-ROW", "DN-A"), _source_line("B-ROW", "DN-B")])
    monkeypatch.setattr(rollup, "frappe", fake)
    ret = SimpleNamespace(
        is_return=1, custom_return_against_se="DN-A", return_against=None,
        items=[RowDoc(
            name="RET-ROW", item_code="ITEM-1", qty=3, uom="Nos",
            custom_original_stock_entry="DN-A", against_stock_entry="DN-A",
            custom_original_se_detail="A-ROW", ste_detail="A-ROW",
        )],
    )

    sources = rollup._return_source_names(ret)
    assert sources == {"DN-A"}
    submitted = rollup._apply_return_event("DN-A", ret, direction=1)
    assert submitted["updated"] is True
    assert fake.db.rows["A-ROW"]["custom_qty_returned"] == 3
    assert fake.db.rows["B-ROW"]["custom_qty_returned"] == 0

    cancelled = rollup._apply_return_event("DN-A", ret, direction=-1)
    assert cancelled["updated"] is True
    assert fake.db.rows["A-ROW"]["custom_qty_returned"] == 0
    assert fake.db.rows["B-ROW"]["custom_qty_returned"] == 0


def test_unlinked_return_is_not_guessed_across_different_mapping_rows(monkeypatch):
    fake = FakeFrappe([
        _source_line("A-ROW-1", "DN-A", "CUC-1"),
        _source_line("A-ROW-2", "DN-A", "CUC-2"),
    ])
    monkeypatch.setattr(rollup, "frappe", fake)
    ret = SimpleNamespace(
        is_return=1, custom_return_against_se="DN-A", return_against=None,
        items=[RowDoc(name="RET-ROW", item_code="ITEM-1", qty=3, uom="Nos")],
    )

    result = rollup._apply_return_event("DN-A", ret, direction=1)

    assert result["updated"] is False
    assert result["reason"] == "RETURN_LINE_AMBIGUOUS"
    assert fake.db.writes == []
    assert fake.db.rows["A-ROW-1"]["custom_qty_returned"] == 0
    assert fake.db.rows["A-ROW-2"]["custom_qty_returned"] == 0


def test_return_header_mismatch_never_allocates_to_the_wrong_dn(monkeypatch):
    fake = FakeFrappe([_source_line("A-ROW", "DN-A")])
    monkeypatch.setattr(rollup, "frappe", fake)
    ret = SimpleNamespace(
        is_return=1, custom_return_against_se="DN-B", return_against=None,
        items=[RowDoc(
            name="RET-ROW", item_code="ITEM-1", qty=3, uom="Nos",
            custom_original_stock_entry="DN-A", custom_original_se_detail="A-ROW",
        )],
    )

    result = rollup._apply_return_event("DN-A", ret, direction=1)

    assert result["updated"] is False
    assert result["reason"] == "RETURN_HEADER_SOURCE_MISMATCH"
    assert fake.db.writes == []


def test_native_return_cannot_bypass_reasoned_reopen_of_closed_line(monkeypatch):
    source = _source_line("A-ROW", "DN-A")
    source["custom_return_closed"] = 1
    fake = FakeFrappe([source])
    monkeypatch.setattr(rollup, "frappe", fake)
    ret = SimpleNamespace(
        is_return=1, custom_return_against_se="DN-A", return_against=None,
        items=[RowDoc(
            name="RET-ROW", item_code="ITEM-1", qty=3, uom="Nos",
            custom_original_stock_entry="DN-A", custom_original_se_detail="A-ROW",
        )],
    )

    result = rollup._apply_return_event("DN-A", ret, direction=1)

    assert result["updated"] is False
    assert result["reason"] == "RETURN_SOURCE_LINE_CLOSED"
    assert fake.db.writes == []
    assert fake.db.rows["A-ROW"]["custom_qty_returned"] == 0


def test_unlinked_return_cannot_guess_which_closed_duplicate_line_to_reopen(monkeypatch):
    source = _source_line("A-ROW-1", "DN-A")
    source["custom_return_closed"] = 1
    fake = FakeFrappe([source, _source_line("A-ROW-2", "DN-A")])
    monkeypatch.setattr(rollup, "frappe", fake)
    ret = SimpleNamespace(
        is_return=1, custom_return_against_se="DN-A", return_against=None,
        items=[RowDoc(name="RET-ROW", item_code="ITEM-1", qty=3, uom="Nos")],
    )

    result = rollup._apply_return_event("DN-A", ret, direction=1)

    assert result["updated"] is False
    assert result["reason"] == "RETURN_LINE_CLOSED_LINK_REQUIRED"
    assert fake.db.writes == []
