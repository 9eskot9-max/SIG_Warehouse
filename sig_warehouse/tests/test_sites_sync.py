import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


class Site(dict):
    __getattr__ = dict.get

    def insert(self):
        self["name"] = self["site_id"]
        DB[self["name"]] = self

    def save(self):
        if not CAN_WRITE[0]:
            raise PermissionError("no site write permission")
        DB[self["name"]] = self


DB = {}
CAN_WRITE = [True]


def get_doc(*args):
    return Site(args[0]) if len(args) == 1 else Site(DB[args[1]])


def get_all(doctype, filters, fields, **kwargs):
    requested = filters["site_id"][1]
    return [types.SimpleNamespace(**{f: row.get(f) for f in fields})
            for row in DB.values() if row["site_id"] in requested]


fake = types.ModuleType("frappe")
fake.whitelist = lambda **kwargs: lambda fn: fn
fake.get_roles = lambda: ["Warehouse Manager"]
fake.has_permission = lambda *args: True
fake.PermissionError = PermissionError
fake._ = lambda text: text
fake.throw = lambda message, *args: (_ for _ in ()).throw(ValueError(message))
fake.get_doc = get_doc
fake.get_all = get_all
path = Path(__file__).resolve().parents[1] / "sig_warehouse" / "sites.py"
spec = importlib.util.spec_from_file_location("sites_sync_under_test", path)
module = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"frappe": fake}):
    spec.loader.exec_module(module)


@pytest.fixture(autouse=True)
def reset():
    DB.clear()
    CAN_WRITE[0] = True


def test_create_and_repeat_with_coordinates_without_warehouse():
    batch = [{"site_id": "zru117", "latitude": 24.8076, "longitude": 46.6646, "region": "Riyadh"}]
    first = module.ensure_sites_from_rv80(batch)
    second = module.ensure_sites_from_rv80(batch)
    assert (first["created"], second["created"], second["updated"]) == (1, 0, 0)
    assert DB["ZRU117"]["geo_source"] == "Tawal export"
    assert "default_warehouse" not in DB["ZRU117"]


def test_existing_site_updates_coordinates_and_missing_coordinates_do_not_erase():
    module.ensure_sites_from_rv80([{"site_id": "A1", "latitude": 24.5, "longitude": 46.5}])
    result = module.ensure_sites_from_rv80([{"site_id": "A1", "latitude": 24.6, "longitude": 46.6}])
    module.ensure_sites_from_rv80([{"site_id": "A1"}])
    assert result["updated"] == 1
    assert DB["A1"]["site_latitude"] == 24.6


def test_rejects_incomplete_coordinates_and_requires_write():
    with pytest.raises(ValueError):
        module.ensure_sites_from_rv80([{"site_id": "A1", "latitude": 24.5}])
    module.ensure_sites_from_rv80([{"site_id": "A1"}])
    CAN_WRITE[0] = False
    with pytest.raises(PermissionError):
        module.ensure_sites_from_rv80([{"site_id": "A1", "latitude": 24.5, "longitude": 46.5}])
