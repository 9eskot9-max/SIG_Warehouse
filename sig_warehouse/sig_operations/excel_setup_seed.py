"""Read-only migration utility for captured RV80 Builder cells.

Only the alias/contact block R:V and its Y PM extension are related by row.
AB, AC, implementer, staff and geography lists are deliberately never read.
This utility creates no Project scope or Project/profile assignments.
"""
import base64
import hashlib


def seed_id(kind, key):
    token = base64.urlsafe_b64encode(hashlib.sha256(key.strip().lower().encode("utf-8")).digest()).decode().rstrip("=")
    return kind + "-" + token


def text(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def builder_seed(rows, batch_id):
    profiles, contacts = {}, {}
    for cells in rows:
        alias = text(cells.get("R"))
        if not alias:
            continue
        key = alias.lower()
        profile = profiles.setdefault(key, {"id": seed_id("builder", key), "alias": alias,
                                            "template": "", "internal_pm": "", "enabled": True})
        for field, column in (("template", "V"), ("internal_pm", "Y")):
            value = text(cells.get(column))
            if value and profile[field] and profile[field].casefold() != value.casefold():
                raise ValueError("Conflicting " + field + " for Builder profile " + alias)
            if value:
                profile[field] = value
        name, phone, email = (text(cells.get(c)) for c in ("S", "T", "U"))
        if not name and not email:
            continue
        contact_key = email.lower() if email else name.lower() + "|" + phone
        contact_id = seed_id("contact", key + "|" + contact_key)
        row = {"id": contact_id, "profile": profile["id"], "tawal_contact": "",
               "contact_name": name, "contact_phone": phone, "contact_email": email,
               "origin": "RV80 Builder", "enabled": True}
        if contact_id in contacts and contacts[contact_id] != row:
            raise ValueError("Conflicting contact snapshot for Builder profile " + alias)
        contacts[contact_id] = row
    return {"schema_version": 2, "batch_id": batch_id, "source": "RV80 independent Builder R:V and Y",
            "datasets": {"builder_profiles": sorted(profiles.values(), key=lambda r: r["id"]),
                         "builder_contacts": sorted(contacts.values(), key=lambda r: r["id"])}}
