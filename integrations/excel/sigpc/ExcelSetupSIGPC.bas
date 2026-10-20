Attribute VB_Name = "ExcelSetupSIGPC"
Option Explicit
'V-excelsetup.sigpc.261020001

Public Sub ExcelSetup_RefreshFromERP()
    ES_Refresh "SIGPC"
End Sub

Public Sub ExcelSetup_ForceRefresh()
    ES_Refresh "SIGPC", True
End Sub

Public Sub ESHost_Validate(ByVal datasets As Object)
    Dim required As Variant
    For Each required In Array("projects", "tag_definitions", "tag_upl_links", "material_upl_links")
        If Not datasets.Exists(CStr(required)) Then Err.Raise vbObjectError + 2830, , "Missing SIGPC dataset: " & required
    Next required
    If datasets("tag_upl_links").Count = 0 Then Err.Raise vbObjectError + 2831, , "Publish SIGPC Tags-UPL links before replacement."
End Sub

Public Function ESHost_Snapshot(ByVal minRows As Long) As Collection
    Dim snapshots As New Collection
    ES_SnapshotRange snapshots, ThisWorkbook.Worksheets("Configure"), "AA:AE", minRows
    Set ESHost_Snapshot = snapshots
End Function

Public Sub ESHost_Apply(ByVal datasets As Object)
    Dim rows As New Collection, row As Object, projected As Object
    For Each row In datasets("tag_upl_links")
        If CBool(row("enabled")) And Len(CStr(row("po"))) = 0 And Len(CStr(row("upl_revision"))) = 0 Then
            Set projected = CreateObject("Scripting.Dictionary")
            projected.Add "cuc", row("cuc"): projected.Add "description", row("description")
            projected.Add "tag_item", row("tag_item"): projected.Add "tag_matcher", row("tag_matcher")
            projected.Add "builder_rule", row("builder_rule"): rows.Add projected
        End If
    Next row
    ES_WriteRegion ThisWorkbook.Worksheets("Configure"), 27, rows, Array("cuc", "description", "tag_item", "tag_matcher", "builder_rule")
    ' Scoped and material links live in the normalized cache. AsBuiltCycle reads
    ' them directly; do not flatten scopes into ambiguous whcd/whupl columns.
End Sub

Public Function ESHost_CucMap(ByVal po As String, ByVal descriptions As Boolean) As Object
    Dim result As Object, row As Object, key As String, value As String
    Set result = CreateObject("Scripting.Dictionary"): result.CompareMode = vbTextCompare
    For Each row In ES_Rows("tag_upl_links", po)
        key = CStr(row("cuc"))
        If descriptions Then value = CStr(row("tag_matcher")) Else value = CStr(row("tag_item"))
        If result.Exists(key) Then
            If CStr(result(key)) <> value Then Err.Raise vbObjectError + 2832, , "Conflicting scoped Tags-UPL link for " & key
        Else
            result.Add key, value
        End If
    Next row
    Set ESHost_CucMap = result
End Function

Public Sub ESHost_MaterialLinks(ByVal po As String, ByVal sourceUnit As String, ByRef links As Object, ByRef excluded As Object, ByRef conflicts As Object)
    Dim row As Object, candidates As Object, code As String
    Static cached As Object, revision As Long
    Dim key As String, pack As Variant
    If cached Is Nothing Or revision <> ES_Revision() Then
        Set cached = CreateObject("Scripting.Dictionary"): cached.CompareMode = vbTextCompare
        revision = ES_Revision()
    End If
    key = Trim$(po) & "|" & Trim$(sourceUnit)
    If cached.Exists(key) Then
        pack = cached(key): Set links = pack(0): Set excluded = pack(1): Set conflicts = pack(2): Exit Sub
    End If
    Set links = CreateObject("Scripting.Dictionary"): links.CompareMode = vbTextCompare
    Set excluded = CreateObject("Scripting.Dictionary"): excluded.CompareMode = vbTextCompare
    Set conflicts = CreateObject("Scripting.Dictionary"): conflicts.CompareMode = vbTextCompare
    For Each row In ES_Rows("material_upl_links", po)
        code = CStr(row("item_code"))
        Select Case CStr(row("treatment"))
        Case "Excluded": excluded(code) = True
        Case "Manual": conflicts(code) = True
        Case "Direct 1:1"
            If StrComp(sourceUnit, CStr(row("source_uom")), vbTextCompare) <> 0 Or StrComp(sourceUnit, CStr(row("target_uom")), vbTextCompare) <> 0 Then
                conflicts(code) = True
            Else
                If Not links.Exists(code) Then
                    Set candidates = CreateObject("Scripting.Dictionary"): candidates.CompareMode = vbTextCompare
                    links.Add code, candidates
                End If
                links(code)(CStr(row("cuc"))) = CStr(row("cuc"))
            End If
        End Select
    Next row
    For Each row In ES_Rows("material_upl_links", po)
        code = CStr(row("item_code"))
        If links.Exists(code) And excluded.Exists(code) Then conflicts(code) = True
    Next row
    cached.Add key, Array(links, excluded, conflicts)
End Sub

Public Sub ExcelSetup_ExportSeed()
    Dim datasets As Object, tags As New Collection, materials As New Collection, row As Object
    Dim ws As Worksheet, r As Long, header As Range, upl As Range, code As Range
    If Not ACN.AC_RequireSession() Then Exit Sub
    Set datasets = CreateObject("Scripting.Dictionary"): Set ws = ThisWorkbook.Worksheets("Configure")
    For r = 2 To ws.Cells(ws.Rows.Count, "AA").End(xlUp).Row
        If Len(Trim$(CStr(ws.Cells(r, "AA")))) > 0 And Len(Trim$(CStr(ws.Cells(r, "AC")))) > 0 Then
            Set row = CreateObject("Scripting.Dictionary")
            row.Add "id", "sigpc-tag-upl-" & r: row.Add "cuc", CStr(ws.Cells(r, "AA"))
            row.Add "description", CStr(ws.Cells(r, "AB")): row.Add "tag_item", CStr(ws.Cells(r, "AC"))
            row.Add "tag_matcher", CStr(ws.Cells(r, "AD")): row.Add "builder_rule", CStr(ws.Cells(r, "AE"))
            row.Add "po", "": row.Add "upl_revision", "": row.Add "enabled", True: tags.Add row
        End If
    Next r
    Set code = ws.Cells.Find(What:="whcd", LookIn:=xlValues, LookAt:=xlWhole)
    If Not code Is Nothing Then
        Set upl = ws.Rows(code.Row).Find(What:="whupl", LookIn:=xlValues, LookAt:=xlWhole)
        If Not upl Is Nothing Then
            For r = code.Row + 1 To ws.Cells(ws.Rows.Count, code.Column).End(xlUp).Row
                If Len(Trim$(CStr(ws.Cells(r, code.Column)))) > 0 Then
                    Set row = CreateObject("Scripting.Dictionary")
                    row.Add "id", "sigpc-material-upl-" & r: row.Add "item_code", CStr(ws.Cells(r, code.Column))
                    row.Add "cuc", CStr(ws.Cells(r, upl.Column)): row.Add "source_uom", "": row.Add "target_uom", ""
                    If UCase$(CStr(ws.Cells(r, upl.Column))) = "X" Then row.Add "treatment", "Excluded" Else row.Add "treatment", "Manual"
                    row.Add "quantity_basis", "Unreviewed legacy link": row.Add "po", "": row.Add "upl_revision", "": row.Add "enabled", True
                    materials.Add row
                End If
            Next r
        End If
    End If
    datasets.Add "tag_upl_links", tags: datasets.Add "material_upl_links", materials
    ES_WriteSeed datasets, "SIGPC"
End Sub
