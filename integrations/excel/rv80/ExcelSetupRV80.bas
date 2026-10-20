Attribute VB_Name = "ExcelSetupRV80"
Option Explicit
'V-excelsetup.rv80.261020001

Public Sub ExcelSetup_RefreshFromERP()
    ES_Refresh "RV80"
End Sub

Public Sub ExcelSetup_ForceRefresh()
    ES_Refresh "RV80", True
End Sub

Public Sub ESHost_Validate(ByVal datasets As Object)
    Dim required As Variant, row As Object, registry As Worksheet, r As Long, matched As Boolean
    For Each required In Array("projects", "tag_definitions", "builder_defaults")
        If Not datasets.Exists(CStr(required)) Then Err.Raise vbObjectError + 2820, , "Missing RV80 dataset: " & required
    Next required
    If datasets("projects").Count = 0 Or datasets("tag_definitions").Count = 0 Then Err.Raise vbObjectError + 2821, , "RV80 needs Project setup and Tags definitions before replacement."
    If datasets("projects").Count > 999 Then Err.Raise vbObjectError + 2822, , "Builder's current consumers support 999 contact rows."
    Set registry = ThisWorkbook.Worksheets("ERPProjects")
    For Each row In datasets("projects")
        If Not CBool(row("enabled")) Then GoTo NextProject
        matched = False
        For r = 2 To registry.Cells(registry.Rows.Count, 1).End(xlUp).Row
            If StrComp(CStr(registry.Cells(r, 1).Value2), CStr(row("project")), vbTextCompare) = 0 And _
               (Len(Trim$(CStr(row("po")))) = 0 Or StrComp(CStr(registry.Cells(r, 2).Value2), CStr(row("po")), vbTextCompare) = 0) Then matched = True: Exit For
        Next r
        If Not matched Then Err.Raise vbObjectError + 2827, , "Refresh the existing Items + Projects from ERP catalogue first. Setup Project/PO is absent: " & row("project")
NextProject:
    Next row
End Sub

Public Function ESHost_Snapshot(ByVal minRows As Long) As Collection
    Dim snapshots As New Collection, ws As Worksheet, region As Variant
    Set ws = ThisWorkbook.Worksheets("Builder")
    For Each region In Array("Q:V", "W:X", "Y:Y", "AB:AB", "BD:BD", "AR:AS", "AW:AZ")
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

Public Sub ESHost_Apply(ByVal datasets As Object)
    Dim ws As Worksheet, row As Object, active As Object, selected As Object, projects As New Collection
    Dim defs As New Collection, reasons As New Collection, wording As New Collection, implementers As New Collection
    Dim r As Long, lastRow As Long, key As String, block() As Variant, i As Long
    Set ws = ThisWorkbook.Worksheets("Builder")
    Set active = CreateObject("Scripting.Dictionary"): Set selected = CreateObject("Scripting.Dictionary")
    lastRow = Application.Max(2, ws.Cells(ws.Rows.Count, "R").End(xlUp).Row)
    For r = 2 To lastRow
        If CStr(ws.Cells(r, "Q").Value2) = "1" Then
            active(ContactKey(CStr(ws.Cells(r, "R")), CStr(ws.Cells(r, "S")), CStr(ws.Cells(r, "U")))) = True
        End If
    Next r
    For Each row In datasets("projects")
        If CBool(row("enabled")) Then projects.Add row
    Next row
    ws.Range("Q2:V" & Application.Max(lastRow, projects.Count + 1)).ClearContents
    ws.Range("Y2:Y" & Application.Max(lastRow, projects.Count + 1)).ClearContents
    ws.Range("AB2:AB" & Application.Max(lastRow, projects.Count + 1)).ClearContents
    ws.Range("BD2:BD" & Application.Max(lastRow, projects.Count + 1)).ClearContents
    ws.Range("Y2:Y" & Application.Max(lastRow, projects.Count + 1)).NumberFormat = "@"
    ws.Range("AB2:AB" & Application.Max(lastRow, projects.Count + 1)).NumberFormat = "@"
    If projects.Count > 0 Then
        ReDim block(1 To projects.Count, 1 To 6)
        For Each row In projects
            i = i + 1: key = ContactKey(row("alias"), row("contact_name"), row("contact_email"))
            If active.Exists(key) And Not selected.Exists(LCase$(CStr(row("alias")))) Then
                block(i, 1) = 1: selected(LCase$(CStr(row("alias")))) = True
            End If
            block(i, 2) = row("alias"): block(i, 3) = row("contact_name")
            block(i, 4) = row("contact_phone"): block(i, 5) = row("contact_email"): block(i, 6) = row("template")
            ws.Cells(i + 1, "Y").Value2 = row("internal_pm")
            ws.Cells(i + 1, "AB").Value2 = ErpCat_FamilyForPo(CStr(row("po")))
        Next row
        ws.Range("Q2").Resize(projects.Count, 6).NumberFormat = "@"
        ws.Range("Q2").Resize(projects.Count, 6).Value2 = block
    End If
    For Each row In datasets("tag_definitions")
        If CBool(row("enabled")) And Len(CStr(row("po"))) = 0 Then defs.Add row
    Next row
    ES_WriteRegion ws, 44, defs, Array("item", "rule")
    For Each row In datasets("builder_defaults")
        If CBool(row("enabled")) Then
            If Len(CStr(row("po"))) > 0 Then Err.Raise vbObjectError + 2824, , "PO-scoped Builder wording requires a scoped consumer; use shared wording in adapter v1."
            Select Case CStr(row("kind"))
            Case "purpose_reason": reasons.Add row
            Case "csv_remarks": wording.Add row
            Case "tms_implementer": implementers.Add row
            Case Else: Err.Raise vbObjectError + 2825, , "Builder kind is not supported by adapter v1: " & row("kind")
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
    Dim datasets As Object, defs As New Collection, defaults As New Collection, projects As Collection
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
    Set projects = ESHost_ExportBuilderProjects(ws)
    datasets.Add "projects", projects
    ES_WriteSeed datasets, "RV80"
End Sub

Private Function ESHost_ExportBuilderProjects(ByVal builder As Worksheet) As Collection
    Dim result As New Collection, setup As Worksheet, header As Range
    Dim r As Long, k As Long, lastSetup As Long, po As String, alias As String, row As Object, skipped As Long
    On Error Resume Next
    Set setup = ThisWorkbook.Worksheets("ERP Setup")
    On Error GoTo 0
    If setup Is Nothing Then Err.Raise vbObjectError + 2828, , "The existing ERP Setup import is required for Project/PO seed references."
    Set header = setup.Cells.Find(What:="PO / Agreement", LookIn:=xlValues, LookAt:=xlWhole)
    If header Is Nothing Then Err.Raise vbObjectError + 2829, , "ERP Setup headers do not match SIG_PROJECT_SETUP_V1. Refresh its existing importer."
    lastSetup = setup.Cells(setup.Rows.Count, header.Column).End(xlUp).Row
    For r = 2 To builder.Cells(builder.Rows.Count, "R").End(xlUp).Row
        alias = Trim$(CStr(builder.Cells(r, "R").Value2))
        If Len(alias) = 0 Then GoTo NextBuilder
        po = Trim$(CStr(builder.Cells(r, "AC").Value2))
        If Len(po) = 0 Then skipped = skipped + 1: GoTo NextBuilder
        k = header.Row + 1
        Do While k <= lastSetup And StrComp(Trim$(CStr(setup.Cells(k, header.Column).Value2)), po, vbTextCompare) <> 0
            k = k + 1
        Loop
        If k > lastSetup Then Err.Raise vbObjectError + 2840, , "Builder PO is absent from ERP Setup: " & po
        Set row = CreateObject("Scripting.Dictionary")
        row.Add "id", "rv80-project-" & r: row.Add "project", CStr(setup.Cells(k, header.Column + 1).Value2)
        row.Add "po", po: row.Add "alias", alias: row.Add "family", CStr(setup.Cells(k, header.Column + 4).Value2)
        row.Add "stream", "": row.Add "template", CStr(builder.Cells(r, "V").Value2)
        row.Add "internal_pm", CStr(builder.Cells(r, "Y").Value2): row.Add "contact_name", CStr(builder.Cells(r, "S").Value2)
        row.Add "contact_phone", CStr(builder.Cells(r, "T").Value2): row.Add "contact_email", CStr(builder.Cells(r, "U").Value2)
        row.Add "upl_revision", "": row.Add "enabled", True: result.Add row
NextBuilder:
    Next r
    If skipped > 0 Then MsgBox skipped & " Builder rows have no BA/PO, so their ERP Project cannot be identified from this row. They were omitted; link the alias to a selected canonical Project in ERP Excel Setup (PO may remain blank).", vbExclamation
    Set ESHost_ExportBuilderProjects = result
End Function
