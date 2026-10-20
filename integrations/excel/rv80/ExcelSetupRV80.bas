Attribute VB_Name = "ExcelSetupRV80"
Option Explicit
'V-excelsetup.rv80.261020002

Public Sub ExcelSetup_RefreshFromERP()
    ES_Refresh "RV80"
End Sub

Public Sub ExcelSetup_ForceRefresh()
    ES_Refresh "RV80", True
End Sub

Public Sub ESHost_Validate(ByVal datasets As Object)
    Dim required As Variant, row As Object, registry As Worksheet, r As Long, matched As Boolean
    Dim profiles As Object, aliases As Object, projects As Object, block As Collection
    Dim activeProfiles As Long, activeContacts As Long, activeTags As Long
    For Each required In Array("projects", "builder_profiles", "builder_contacts", "project_builder_links", "tag_definitions", "builder_defaults")
        If Not datasets.Exists(CStr(required)) Then Err.Raise vbObjectError + 2820, , "Missing RV80 dataset: " & required
    Next required
    Set profiles = CreateObject("Scripting.Dictionary"): Set aliases = CreateObject("Scripting.Dictionary")
    aliases.CompareMode = vbTextCompare: Set projects = CreateObject("Scripting.Dictionary")
    For Each row In datasets("builder_profiles")
        If CBool(row("enabled")) Then
            If profiles.Exists(CStr(row("id"))) Or aliases.Exists(CStr(row("alias"))) Then Err.Raise vbObjectError + 2823, , "Duplicate Builder profile ID or alias."
            profiles.Add CStr(row("id")), True: aliases.Add CStr(row("alias")), True
            activeProfiles = activeProfiles + 1
        End If
    Next row
    For Each row In datasets("builder_contacts")
        If CBool(row("enabled")) Then
            If Len(CStr(row("tawal_contact"))) = 0 Then Err.Raise vbObjectError + 2823, , "Resolve every enabled Builder contact in the ERP directory before replacement."
            If Not profiles.Exists(CStr(row("profile"))) Then Err.Raise vbObjectError + 2823, , "Builder contact has no enabled profile."
            activeContacts = activeContacts + 1
        End If
    Next row
    For Each row In datasets("tag_definitions")
        If CBool(row("enabled")) Then activeTags = activeTags + 1
    Next row
    If activeProfiles = 0 Or activeContacts = 0 Or activeTags = 0 Then Err.Raise vbObjectError + 2821, , "Builder profiles, contacts and Tags definitions are incomplete. Existing Builder retained."
    If datasets("projects").Count > 0 Then Set registry = ThisWorkbook.Worksheets("ERPProjects")
    For Each row In datasets("projects")
        If Not CBool(row("enabled")) Then GoTo NextProject
        matched = False
        For r = 2 To registry.Cells(registry.Rows.Count, 1).End(xlUp).Row
            If StrComp(CStr(registry.Cells(r, 1).Value2), CStr(row("project")), vbTextCompare) = 0 And _
               (Len(Trim$(CStr(row("po")))) = 0 Or StrComp(CStr(registry.Cells(r, 2).Value2), CStr(row("po")), vbTextCompare) = 0) Then matched = True: Exit For
        Next r
        If Not matched Then Err.Raise vbObjectError + 2827, , "Refresh Items + Projects from ERP. Setup Project/PO is absent: " & row("project")
        projects(CStr(row("project"))) = True
NextProject:
    Next row
    For Each row In datasets("project_builder_links")
        If CBool(row("enabled")) Then
            If Not projects.Exists(CStr(row("project"))) Or Not profiles.Exists(CStr(row("profile"))) Then Err.Raise vbObjectError + 2823, , "Project assignment has an unresolved Project or profile."
        End If
    Next row
    Set block = ESHost_BuilderRows(datasets)
    If block.Count > 999 Then Err.Raise vbObjectError + 2822, , "Builder supports at most 999 contact/profile rows."
End Sub

Public Function ESHost_Snapshot(ByVal minRows As Long) As Collection
    Dim snapshots As New Collection, ws As Worksheet, region As Variant
    Set ws = ThisWorkbook.Worksheets("Builder")
    For Each region In Array("Q:V", "W:X", "Y:Y", "BD:BD", "AR:AS", "AW:AZ")
        ES_SnapshotRange snapshots, ws, CStr(region), minRows
    Next region
    Set ESHost_Snapshot = snapshots
End Function

Private Function ContactKey(ByVal alias As String, ByVal name As String, ByVal email As String) As String
    If Len(Trim$(email)) > 0 Then
        ContactKey = LCase$(Trim$(alias) & "|email:" & Trim$(email))
    Else
        ContactKey = LCase$(Trim$(alias) & "|name:" & Trim$(name))
    End If
End Function

Private Function ESHost_ProfileRow(ByVal profile As Object, ByVal contact As Object) As Object
    Dim row As Object, field As Variant
    Set row = CreateObject("Scripting.Dictionary")
    For Each field In Array("alias", "template", "internal_pm")
        row.Add CStr(field), profile(CStr(field))
    Next field
    For Each field In Array("contact_name", "contact_phone", "contact_email")
        If contact Is Nothing Then row.Add CStr(field), "" Else row.Add CStr(field), contact(CStr(field))
    Next field
    Set ESHost_ProfileRow = row
End Function

Private Function ESHost_BuilderRows(ByVal datasets As Object) As Collection
    Dim result As New Collection, profile As Object, contact As Object, found As Boolean
    For Each profile In datasets("builder_profiles")
        If CBool(profile("enabled")) Then
            found = False
            For Each contact In datasets("builder_contacts")
                If CBool(contact("enabled")) And CStr(contact("profile")) = CStr(profile("id")) Then
                    result.Add ESHost_ProfileRow(profile, contact): found = True
                End If
            Next contact
            If Not found Then result.Add ESHost_ProfileRow(profile, Nothing)
        End If
    Next profile
    Set ESHost_BuilderRows = result
End Function

Public Sub ESHost_Apply(ByVal datasets As Object)
    Dim ws As Worksheet, row As Object, active As Object, selected As Object, profiles As Collection
    Dim empRefs As Object, empRef As Variant, aliasKey As String
    Dim defs As New Collection, reasons As New Collection, wording As New Collection, implementers As New Collection
    Dim r As Long, lastRow As Long, key As String, block() As Variant, i As Long
    Set ws = ThisWorkbook.Worksheets("Builder")
    Set active = CreateObject("Scripting.Dictionary"): Set selected = CreateObject("Scripting.Dictionary")
    Set empRefs = CreateObject("Scripting.Dictionary"): empRefs.CompareMode = vbTextCompare
    lastRow = Application.Max(2, ws.Cells(ws.Rows.Count, "R").End(xlUp).Row)
    For r = 2 To lastRow
        aliasKey = Trim$(CStr(ws.Cells(r, "R").Value2))
        If Len(aliasKey) > 0 And Not empRefs.Exists(aliasKey) Then empRefs.Add aliasKey, Array(CStr(ws.Cells(r, "Y").Value2), CStr(ws.Cells(r, "BD").Value2))
        If CStr(ws.Cells(r, "Q").Value2) = "1" Then active(ContactKey(aliasKey, CStr(ws.Cells(r, "S")), CStr(ws.Cells(r, "U")))) = True
    Next r
    ' Profiles/contacts are flattened once per alias, never once per Project link.
    Set profiles = ESHost_BuilderRows(datasets)
    ws.Range("Q2:V" & Application.Max(lastRow, profiles.Count + 1)).ClearContents
    ws.Range("Y2:Y" & Application.Max(lastRow, profiles.Count + 1)).ClearContents
    ws.Range("BD2:BD" & Application.Max(lastRow, profiles.Count + 1)).ClearContents
    ws.Range("Y2:Y" & Application.Max(lastRow, profiles.Count + 1)).NumberFormat = "@"
    If profiles.Count > 0 Then
        ReDim block(1 To profiles.Count, 1 To 6)
        For Each row In profiles
            i = i + 1: key = ContactKey(row("alias"), row("contact_name"), row("contact_email"))
            aliasKey = LCase$(Trim$(CStr(row("alias"))))
            If active.Exists(key) And Not selected.Exists(aliasKey) Then
                block(i, 1) = 1: selected(aliasKey) = True
            End If
            block(i, 2) = row("alias"): block(i, 3) = row("contact_name")
            block(i, 4) = row("contact_phone"): block(i, 5) = row("contact_email"): block(i, 6) = row("template")
            ws.Cells(i + 1, "Y").Value2 = row("internal_pm")
            ' BD is a workbook-local UserPasswords index; preserve only when PM is unchanged.
            If empRefs.Exists(aliasKey) Then
                empRef = empRefs(aliasKey)
                If StrComp(Trim$(CStr(empRef(0))), Trim$(CStr(row("internal_pm"))), vbTextCompare) = 0 Then ws.Cells(i + 1, "BD").Value2 = empRef(1)
            End If
        Next row
        ws.Range("Q2").Resize(profiles.Count, 6).NumberFormat = "@"
        ws.Range("Q2").Resize(profiles.Count, 6).Value2 = block
    End If
    ' AB vocabulary, AC PO validation, geography and staff directories are independent.
    ' Project scope and explicit assignments stay in the normalized cache.
    For Each row In datasets("tag_definitions")
        If CBool(row("enabled")) And Len(CStr(row("po"))) = 0 Then defs.Add row
    Next row
    ES_WriteRegion ws, 44, defs, Array("item", "rule")
    For Each row In datasets("builder_defaults")
        If CBool(row("enabled")) Then
            If Len(CStr(row("po"))) > 0 Then Err.Raise vbObjectError + 2824, , "PO-scoped Builder wording requires a scoped consumer; use shared wording in adapter v2."
            Select Case CStr(row("kind"))
            Case "purpose_reason": reasons.Add row
            Case "csv_remarks": wording.Add row
            Case "tms_implementer": implementers.Add row
            Case Else: Err.Raise vbObjectError + 2825, , "Builder kind is not supported by adapter v2: " & row("kind")
            End Select
        End If
    Next row
    ES_WriteRegion ws, 49, reasons, Array("key", "value")
    ES_WriteRegion ws, 51, wording, Array("key", "value")
    ES_WriteRegion ws, 23, implementers, Array("key", "value")
End Sub

Public Function ESHost_TagRuleArrays(ByVal po As String, ByRef items As Variant, ByRef rules As Variant) As Boolean
    Dim rows As Collection, row As Object, a() As Variant, b() As Variant, n As Long
    Static cached As Object, revision As Long
    Dim key As String, pack As Variant
    If cached Is Nothing Or revision <> ES_Revision() Then
        Set cached = CreateObject("Scripting.Dictionary"): cached.CompareMode = vbTextCompare
        revision = ES_Revision()
    End If
    key = Trim$(po)
    If cached.Exists(key) Then
        pack = cached(key): items = pack(0): rules = pack(1): ESHost_TagRuleArrays = True: Exit Function
    End If
    Set rows = ES_Rows("tag_definitions", po)
    If rows.Count = 0 Then Exit Function
    ReDim a(1 To rows.Count, 1 To 1): ReDim b(1 To rows.Count, 1 To 1)
    For Each row In rows
        n = n + 1: a(n, 1) = row("item"): b(n, 1) = row("rule")
    Next row
    items = a: rules = b: cached.Add key, Array(a, b): ESHost_TagRuleArrays = True
End Function

Public Sub ExcelSetup_ExportSeed()
    Dim datasets As Object, defs As New Collection, defaults As New Collection
    Dim row As Object, ws As Worksheet, r As Long, columns As Variant, kind As Variant
    If Not ACN.AC_RequireSession() Then Exit Sub
    Set datasets = CreateObject("Scripting.Dictionary"): Set ws = ThisWorkbook.Worksheets("Builder")
    For r = 2 To ws.Cells(ws.Rows.Count, "AR").End(xlUp).Row
        If Len(Trim$(CStr(ws.Cells(r, "AR")))) > 0 And Len(Trim$(CStr(ws.Cells(r, "AS")))) > 0 Then
            Set row = CreateObject("Scripting.Dictionary")
            row.Add "id", "rv80-tag-" & r: row.Add "item", CStr(ws.Cells(r, "AR"))
            row.Add "rule", CStr(ws.Cells(r, "AS")): row.Add "priority", CStr(r): row.Add "po", "": row.Add "enabled", True
            defs.Add row
        End If
    Next r
    For Each columns In Array(Array("AW", "AX", "purpose_reason"), Array("AY", "AZ", "csv_remarks"), Array("W", "X", "tms_implementer"))
        For r = 2 To ws.Cells(ws.Rows.Count, columns(0)).End(xlUp).Row
            If Len(Trim$(CStr(ws.Cells(r, columns(0))))) > 0 Then
                Set row = CreateObject("Scripting.Dictionary")
                row.Add "id", "rv80-" & columns(0) & "-" & r: row.Add "kind", columns(2)
                row.Add "key", CStr(ws.Cells(r, columns(0))): row.Add "value", CStr(ws.Cells(r, columns(1)))
                row.Add "value2", "": row.Add "po", "": row.Add "enabled", True: defaults.Add row
            End If
        Next r
    Next columns
    datasets.Add "tag_definitions", defs: datasets.Add "builder_defaults", defaults
    ESHost_ExportBuilderProfiles ws, datasets
    ES_WriteSeed datasets, "RV80"
End Sub

Private Sub ESHost_MergeProfileValue(ByVal profile As Object, ByVal field As String, ByVal value As String)
    value = Trim$(value)
    If Len(value) = 0 Then Exit Sub
    If Len(CStr(profile(field))) > 0 And StrComp(CStr(profile(field)), value, vbTextCompare) <> 0 Then Err.Raise vbObjectError + 2840, , "Conflicting " & field & " for Builder alias " & profile("alias") & ". Review its source contact rows."
    profile(field) = value
End Sub

Private Sub ESHost_ExportBuilderProfiles(ByVal builder As Worksheet, ByVal datasets As Object)
    Dim profiles As Object, contacts As Object, profileRows As New Collection, contactRows As New Collection
    Dim r As Long, alias As String, profileKey As String, contactId As String, contactKeyText As String
    Dim profile As Object, row As Object, item As Variant
    Set profiles = CreateObject("Scripting.Dictionary"): profiles.CompareMode = vbTextCompare
    Set contacts = CreateObject("Scripting.Dictionary")
    For r = 2 To builder.Cells(builder.Rows.Count, "R").End(xlUp).Row
        alias = Trim$(CStr(builder.Cells(r, "R").Value2))
        If Len(alias) = 0 Then GoTo NextBuilder
        profileKey = LCase$(alias)
        If Not profiles.Exists(profileKey) Then
            Set profile = CreateObject("Scripting.Dictionary")
            profile.Add "id", ES_SeedId("builder", profileKey): profile.Add "alias", alias
            profile.Add "template", "": profile.Add "internal_pm", "": profile.Add "enabled", True
            profiles.Add profileKey, profile
        End If
        Set profile = profiles(profileKey)
        ESHost_MergeProfileValue profile, "template", CStr(builder.Cells(r, "V").Value2)
        ESHost_MergeProfileValue profile, "internal_pm", CStr(builder.Cells(r, "Y").Value2)
        If Len(Trim$(CStr(builder.Cells(r, "S").Value2))) = 0 And Len(Trim$(CStr(builder.Cells(r, "U").Value2))) = 0 Then GoTo NextBuilder
        contactKeyText = LCase$(Trim$(CStr(builder.Cells(r, "U").Value2)))
        If Len(contactKeyText) = 0 Then contactKeyText = LCase$(Trim$(CStr(builder.Cells(r, "S").Value2))) & "|" & Trim$(CStr(builder.Cells(r, "T").Value2))
        contactId = ES_SeedId("contact", profileKey & "|" & contactKeyText)
        If Not contacts.Exists(contactId) Then
            Set row = CreateObject("Scripting.Dictionary")
            row.Add "id", contactId: row.Add "profile", profile("id"): row.Add "tawal_contact", ""
            row.Add "contact_name", CStr(builder.Cells(r, "S").Value2)
            row.Add "contact_phone", CStr(builder.Cells(r, "T").Value2): row.Add "contact_email", CStr(builder.Cells(r, "U").Value2)
            row.Add "origin", "RV80 Builder": row.Add "enabled", True: contacts.Add contactId, row
        Else
            Set row = contacts(contactId)
            If StrComp(CStr(row("contact_name")), Trim$(CStr(builder.Cells(r, "S").Value2)), vbTextCompare) <> 0 Or _
               StrComp(CStr(row("contact_phone")), Trim$(CStr(builder.Cells(r, "T").Value2)), vbTextCompare) <> 0 Or _
               StrComp(CStr(row("contact_email")), Trim$(CStr(builder.Cells(r, "U").Value2)), vbTextCompare) <> 0 Then Err.Raise vbObjectError + 2840, , "Conflicting contact details for Builder alias " & alias
        End If
NextBuilder:
    Next r
    For Each item In profiles.Keys
        profileRows.Add profiles(item)
    Next item
    For Each item In contacts.Keys
        contactRows.Add contacts(item)
    Next item
    datasets.Add "builder_profiles", profileRows: datasets.Add "builder_contacts", contactRows
    ' No Project links exported: AC is a separate PO dropdown list, never a join key.
End Sub
