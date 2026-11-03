# Merged RV80 Excel Setup: implementation checklist

- [x] Prepare RV80 v3 payload with Tags-to-UPL and material-to-UPL links; preserve legacy field values while hiding the redundant UPL description input.
- [ ] Deploy the reviewed ERP change using the deployment permission guide and verify the actual-user persona and permissions.
- [ ] Import and compile the matching deployed RV80 modules, refresh the merged workbook, and verify a real GCL and AsBuilt case, including ambiguous UPL matches and scoped links.
- [ ] Review PO-scoped tag-link override semantics before automatically copying scoped rules.
- [ ] Implement and verify the proposed new-PO automation: detect family, choose the highest numeric eligible same-family PO as an editable starting point, preserve operator overrides and require review for uncertain defaults and PO-specific UPL data. This remains design only.

A source change or a GitHub push is not evidence of ERP deployment or workbook acceptance.
