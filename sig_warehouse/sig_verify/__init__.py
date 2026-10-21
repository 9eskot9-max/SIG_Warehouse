"""SIG document verification: a styled QR on submitted documents that opens a public check page.

What it does
    * On submit of a registered doctype (see ``registry.VERIFIABLE``) it stores a random
      token in the hidden field ``custom_verify_token`` and attaches a styled QR image
      (public File ``verify_qr_<name>.png``) that encodes ``<site>/verify?t=<token>``.
    * The public method ``sig_warehouse.sig_verify.api.verify`` (guest, rate limited) maps a
      token back to the document and returns only: number, date, validity, company, state
      (Valid / Cancelled / Draft) and total. Never line items, customer or contact data.
    * Print formats show the QR when the File exists (see the SIG Quotation print format).
      Nothing prints for drafts: the QR is created on submit.

Why it is safe to run on submit
    The token is written with ``update_modified=False`` so "modified by" stays the submitter
    (the print formats read it for "Authorized by"). Any failure is logged to the Error Log
    and never blocks the submit.

Adding another doctype (letter, warranty, ...) later
    1. Add an entry to ``registry.VERIFIABLE`` (field names are optional).
    2. Deploy: ``hooks.py`` registers the ``on_submit`` event from the registry and the patch
       ``add_verify_token_fields`` creates the hidden token field on every registered doctype.
    3. Show the QR in that doctype's print format: look up the File named ``verify_qr_<name>.png``
       attached to the document (see ``sig_quotation_infographic.html``).
    Documents submitted before the feature existed can be backfilled with
    ``bench --site <site> execute sig_warehouse.sig_verify.events.backfill --kwargs "{'doctype': 'Quotation', 'name': 'QTN-26-055'}"``.

Deploy notes (for the release owner)
    * Needs no new Python dependency: it uses Pillow and ``pyqrcode`` (both shipped with Frappe);
      ``qrcode`` is used instead when present.
    * Migration adds the Custom Field and repoints the existing /verify Web Page from the old
      Server Script ``sig_verify`` to this app's method. Leave that Server Script enabled until the
      probe below passes, then disable it (it is no longer called).
    * Probe after deploy: GET ``/api/method/sig_warehouse.sig_verify.api.verify?t=<token of a submitted
      quotation>`` as a guest returns ``{"valid": 1, ...}``; a bad token returns ``{"valid": 0}``.
    * Submit a test quotation as a normal user and confirm: File ``verify_qr_<name>.png`` exists,
      "modified by" is unchanged, the print shows the QR, and scanning opens /verify.
"""
