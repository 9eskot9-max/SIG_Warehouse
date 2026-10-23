"""SIG Letters: template-driven letters drafted and issued in ERPNext.

Pattern: the same one HRMS uses for Appointment Letters (Template -> Letter -> Print Format), with a
richer block model so one print format renders any SIG letter (technical proposal, warranty,
authorisation, price clarification ...).

    SIG Letter Template   (master)   subject / greeting / closing / blocks, with {{ jinja }} variables
    SIG Letter Block      (child)    block_type: Paragraph | Heading | Bullets | Table | Note
    SIG Letter            (submit)   addressee, date, language, blocks, signer; name = yymmddA
    Print Format          "SIG Letter (Infographic)"  one Jinja format for every letter type

Document life
    Draft  -> a person (or the API) fills a letter from a template; anyone can print a draft.
    Submit -> the letter is issued: sig_verify issues the token + styled QR (registry entry
              "SIG Letter"), "Authorized by" is the submitter, the PDF is the official copy.
    Cancel -> the public verify page then reports it as Cancelled.

API contract (what an AI / script sends): see ``blocks.py``. The payload is the same JSON the local
letter builder already uses (to / attn / subject / greeting / blocks / closing), so existing letters
(e.g. ERPNext/outputs/letters/enova_technical_proposal_261021A.json) convert with
``blocks.legacy_payload_to_doc``. Blocks are typed (p / h / ul / table / note), never raw HTML.

Staged layout (everything below is local until the release owner ships it)
    sig_letters/
        blocks.py        pure: payload <-> child rows, validation          (unit-tested)
        reference.py     pure: yymmdd + A, B, ... per-day reference         (unit-tested)
        doctype/         sig_letter, sig_letter_block, sig_letter_template
        print_format/    sig_letter.html  (wkhtmltopdf-safe: tables, no flex/grid/variables)
        templates/       seed template library (JSON)
        design/          tokens.json  (from SIG_Company_Profile_Handover/05_Handover_Docs/DESIGN_SYSTEM.md)

The initial DocType permissions are restricted to System Manager. Submitted letters use the
shared SIG verification registry and the app-owned styled QR renderer.
"""
