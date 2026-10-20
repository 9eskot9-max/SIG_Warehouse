Attribute VB_Name = "ExcelSetupSync"
Option Explicit
'V-excelsetup.common.261020002
Public Const ES_ADAPTER_VERSION As Long = 2
Private Const ES_ENDPOINT As String = "https://neosys.frappe.cloud/api/method/sig_warehouse.sig_operations.excel_setup.get_setup_bundle"
Private Const ES_CACHE As String = "_ExcelSetupCache"
Private Const ES_META As String = "_ExcelSetupMeta"
Private mRows As Object
Private mRevision As String

Public Sub ES_Refresh(ByVal workbookType As String, Optional ByVal force As Boolean = False)
    Dim http As Object, root As Object, data As Object, datasets As Object
    Dim auth As String, payload As String, cache As Worksheet, meta As Worksheet, backup As Worksheet
    Dim oldCache As Variant, oldMeta As Variant, snapshots As Collection, pack As Variant
    Dim item As Variant, rows As Collection, row As Object, count As Long, n As Long
    Dim values() As Variant, screen As Boolean, events As Boolean, calc As Long, writing As Boolean
    Dim msg As String, errText As String, lastRevision As Long, restoreFailed As Boolean
    On Error GoTo Failed
    If Not ACN.AC_RequireSession() Then Exit Sub
    auth = ACN.AC_GetErpExcelSetupReadKey()
    If InStr(auth, ":") = 0 Then Err.Raise vbObjectError + 2800, , "Setup fetch key is unavailable in the protected ACN mirror."
    Set http = CreateObject("WinHttp.WinHttpRequest.5.1")
    http.SetTimeouts 15000, 15000, 30000, 60000
    If Not force Then lastRevision = ES_Revision()
    http.Open "GET", ES_ENDPOINT & "?workbook_type=" & workbookType & "&adapter_version=2&last_revision=" & lastRevision, False
    http.SetRequestHeader "Authorization", "token " & auth
    http.SetRequestHeader "Accept", "application/json"
    http.Send
    auth = ""
    If http.Status <> 200 Then Err.Raise vbObjectError + 2801, , "Excel Setup fetch failed (HTTP " & http.Status & "). Existing setup was retained."
    Set root = JsonConverter.ParseJson(http.ResponseText)
    Set data = root("message")
    If CStr(data("contract")) <> "SIG_EXCEL_SETUP_V2" Or CStr(data("workbook_type")) <> workbookType Then Err.Raise vbObjectError + 2802, , "Unexpected setup contract/workbook."
    If CLng(data("schema_version")) <> 2 Or CLng(data("minimum_adapter_version")) <> ES_ADAPTER_VERSION Then Err.Raise vbObjectError + 2803, , "Import the matching Excel Setup BAS release."
    If Not CBool(data("complete")) Then Err.Raise vbObjectError + 2804, , "ERP setup is unpublished or incomplete for this workbook. Existing setup was retained."
    If CBool(data("unchanged")) Then
        If Not ES_Ready() Then Err.Raise vbObjectError + 2805, , "Local setup metadata is incomplete; use ExcelSetup_ForceRefresh."
        MsgBox "Excel Setup is current. Revision " & ES_Revision(), vbInformation
        Exit Sub
    End If
    payload = CStr(data("payload_json"))
    If AC_Crypto.AC_Sha256Utf8B64(payload) <> CStr(data("payload_sha256_b64")) Then Err.Raise vbObjectError + 2806, , "Setup checksum validation failed."
    Set datasets = JsonConverter.ParseJson(payload)
    ESHost_Validate datasets
    msg = "Replace imported Excel Setup with ERP revision " & CStr(data("revision")) & "?" & vbCrLf
    For Each item In datasets.Keys
        Set rows = datasets(item)
        If rows.Count <> CLng(data("counts")(item)) Then Err.Raise vbObjectError + 2807, , "Setup row count mismatch."
        msg = msg & vbCrLf & CStr(item) & ": " & rows.Count
        count = count + rows.Count
    Next item
    msg = msg & vbCrLf & ES_PreviewDiff(datasets)
    msg = msg & vbCrLf & vbCrLf & "Generated setup ranges will be replaced. Active contact choices are preserved where valid." & vbCrLf & "Stock, Tags transactions, Mapping and final AB are not imported by this action."
    If MsgBox(msg, vbYesNo + vbQuestion, "Refresh Excel Setup") <> vbYes Then Exit Sub
    Set cache = ES_Sheet(ES_CACHE): Set meta = ES_Sheet(ES_META)
    oldCache = cache.Range("A1:C" & Application.Max(2, cache.Cells(cache.Rows.Count, 1).End(xlUp).Row)).Value2
    oldMeta = meta.Range("A1:B10").Value2
    Set snapshots = ESHost_Snapshot(count + 2)
    Set backup = ES_Sheet("_ExcelSetupPrevious")
    backup.Cells.ClearContents
    backup.Range("A1").Resize(UBound(oldCache, 1), UBound(oldCache, 2)).Value2 = oldCache
    backup.Range("E1:F10").Value2 = oldMeta
    screen = Application.ScreenUpdating: events = Application.EnableEvents: calc = Application.Calculation
    Application.ScreenUpdating = False: Application.EnableEvents = False: Application.Calculation = xlCalculationManual
    writing = True
    cache.Cells.ClearContents
    cache.Columns("A:C").NumberFormat = "@"
    cache.Range("A1:C1").Value = Array("Dataset", "ID", "JSON")
    If count > 0 Then
        ReDim values(1 To count, 1 To 3)
        For Each item In datasets.Keys
            For Each row In datasets(item)
                n = n + 1
                values(n, 1) = CStr(item): values(n, 2) = CStr(row("id"))
                values(n, 3) = JsonConverter.ConvertToJson(row)
                If Len(CStr(values(n, 3))) > 32767 Then Err.Raise vbObjectError + 2808, , "Setup row exceeds Excel cell capacity."
            Next row
        Next item
        cache.Range("A2").Resize(count, 3).Value2 = values
    End If
    ESHost_Apply datasets
    meta.Range("A1:B10").ClearContents
    meta.Cells(1, 1) = "Revision": meta.Cells(1, 2) = CLng(data("revision"))
    meta.Cells(2, 1) = "Hash": meta.Cells(2, 2) = CStr(data("hash"))
    meta.Cells(3, 1) = "Imported": meta.Cells(3, 2) = Now
    meta.Cells(4, 1) = "ACN user (reported)": meta.Cells(4, 2) = ACN.AC_GetCurrentUser()
    meta.Cells(5, 1) = "Workbook": meta.Cells(5, 2) = workbookType
    meta.Cells(6, 1) = "Adapter": meta.Cells(6, 2) = ES_ADAPTER_VERSION
    meta.Cells(7, 1) = "Contract": meta.Cells(7, 2) = "SIG_EXCEL_SETUP_V2"
    meta.Cells(8, 1) = "Status": meta.Cells(8, 2) = "Imported locally; server receipt not implemented"
    Set mRows = Nothing: mRevision = ""
    writing = False
    Application.ScreenUpdating = screen: Application.EnableEvents = events: Application.Calculation = calc
    MsgBox "Excel Setup imported. Revision " & ES_Revision() & ". Save the workbook normally to retain it.", vbInformation
    Exit Sub
Failed:
    errText = Err.Description
    If writing Then
        On Error Resume Next
        For Each pack In snapshots
            Err.Clear
            pack(0).Formula = pack(1)
            If Err.Number <> 0 Then restoreFailed = True
        Next pack
        Err.Clear
        cache.Cells.ClearContents
        cache.Range("A1").Resize(UBound(oldCache, 1), UBound(oldCache, 2)).Value2 = oldCache
        If Err.Number <> 0 Then restoreFailed = True
        Err.Clear
        meta.Range("A1:B10").Value2 = oldMeta
        If Err.Number <> 0 Then restoreFailed = True
        If restoreFailed Then
            meta.Cells(1, 2).Value2 = 0
            meta.Cells(8, 2).Value2 = "Restore incomplete: reconcile previous setup before refresh"
            errText = errText & vbCrLf & "One or more ranges could not be restored. Setup use is blocked; reconcile the previous snapshot before retrying."
        End If
        Set mRows = Nothing: mRevision = ""
        Application.ScreenUpdating = screen: Application.EnableEvents = events: Application.Calculation = calc
        On Error GoTo 0
    End If
    MsgBox "Excel Setup was not imported: " & errText, vbExclamation
End Sub

Private Function ES_PreviewDiff(ByVal datasets As Object) As String
    Dim old As Object, incoming As Object, ws As Worksheet, item As Variant, row As Object
    Dim r As Long, key As String, added As Long, changed As Long, omitted As Long
    Set old = CreateObject("Scripting.Dictionary"): Set incoming = CreateObject("Scripting.Dictionary")
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(ES_CACHE)
    On Error GoTo 0
    If Not ws Is Nothing Then
        For r = 2 To ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
            key = CStr(ws.Cells(r, 1).Value2) & "|" & CStr(ws.Cells(r, 2).Value2)
            old(key) = CStr(ws.Cells(r, 3).Value2)
        Next r
    End If
    For Each item In datasets.Keys
        For Each row In datasets(item)
            key = CStr(item) & "|" & CStr(row("id")): incoming(key) = True
            If Not old.Exists(key) Then
                added = added + 1
            ElseIf CStr(old(key)) <> JsonConverter.ConvertToJson(row) Then
                changed = changed + 1
            End If
        Next row
    Next item
    For Each item In old.Keys
        If Not incoming.Exists(CStr(item)) Then omitted = omitted + 1
    Next item
    ES_PreviewDiff = "Compared with the imported cache: " & added & " added, " & changed & " changed, " & omitted & " omitted." & vbCrLf & _
        "For the first import, reconcile the seed against the current Builder/Configure data before confirming."
End Function

Public Function ES_Sheet(ByVal name As String) As Worksheet
    Dim ws As Worksheet
    On Error Resume Next
    Set ws = ThisWorkbook.Worksheets(name)
    On Error GoTo 0
    If ws Is Nothing Then
        Set ws = ThisWorkbook.Worksheets.Add(After:=ThisWorkbook.Worksheets(ThisWorkbook.Worksheets.Count))
        ws.Name = name
    End If
    ws.Visible = xlSheetVeryHidden
    Set ES_Sheet = ws
End Function

Public Function ES_Revision() As Long
    On Error Resume Next
    ES_Revision = CLng(ThisWorkbook.Worksheets(ES_META).Cells(1, 2).Value2)
    On Error GoTo 0
End Function

Public Function ES_Ready() As Boolean
    On Error GoTo Missing
    ES_Ready = (ES_Revision() > 0 And CStr(ThisWorkbook.Worksheets(ES_META).Cells(7, 2).Value2) = "SIG_EXCEL_SETUP_V2" _
        And CLng(ThisWorkbook.Worksheets(ES_META).Cells(6, 2).Value2) = ES_ADAPTER_VERSION _
        And ThisWorkbook.Worksheets(ES_CACHE).Cells(2, 1).Value2 <> "")
Missing:
End Function

Public Sub ES_RequireReady()
    If Not ACN.AC_RequireSession() Then Err.Raise vbObjectError + 2810, , "Sign in through ACN before using shared setup."
    If Not ES_Ready() Then Err.Raise vbObjectError + 2811, , "Refresh Excel Setup from ERP first."
End Sub

Public Function ES_AllRows(ByVal dataset As String) As Collection
    Dim ws As Worksheet, r As Long, row As Object, key As Variant, rows As Collection
    ES_RequireReady
    If mRows Is Nothing Or mRevision <> CStr(ES_Revision()) Then
        Set mRows = CreateObject("Scripting.Dictionary")
        Set ws = ThisWorkbook.Worksheets(ES_CACHE)
        For r = 2 To ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
            key = CStr(ws.Cells(r, 1).Value2)
            If Not mRows.Exists(key) Then
                Set rows = New Collection: mRows.Add key, rows
            End If
            Set row = JsonConverter.ParseJson(CStr(ws.Cells(r, 3).Value2))
            mRows(key).Add row
        Next r
        mRevision = CStr(ES_Revision())
    End If
    If mRows.Exists(dataset) Then
        Set ES_AllRows = mRows(dataset)
    Else
        Set ES_AllRows = New Collection
    End If
End Function

Public Function ES_UplRevision(ByVal po As String) As String
    Dim row As Object, found As String
    For Each row In ES_AllRows("projects")
        If CBool(row("enabled")) And StrComp(CStr(row("po")), po, vbTextCompare) = 0 Then
            If row.Exists("upl_revision") Then
                If Len(CStr(row("upl_revision"))) > 0 Then
                    If Len(found) > 0 And StrComp(found, CStr(row("upl_revision")), vbTextCompare) <> 0 Then Err.Raise vbObjectError + 2812, , "Conflicting UPL revisions for PO " & po
                    found = CStr(row("upl_revision"))
                End If
            End If
        End If
    Next row
    ES_UplRevision = found
End Function

Public Function ES_Rows(ByVal dataset As String, ByVal po As String) As Collection
    Dim result As New Collection, candidates As New Collection, row As Object, upRev As String, rowPo As String
    Dim best As Object, key As String, rank As Long
    Set best = CreateObject("Scripting.Dictionary"): best.CompareMode = vbTextCompare
    upRev = ES_UplRevision(po)
    For Each row In ES_AllRows(dataset)
        If CBool(row("enabled")) Then
            rowPo = "": If row.Exists("po") Then rowPo = CStr(row("po"))
            If Len(rowPo) = 0 Or StrComp(rowPo, po, vbTextCompare) = 0 Then
                If row.Exists("upl_revision") Then
                    If Len(CStr(row("upl_revision"))) > 0 Then
                        If Len(upRev) = 0 Then Err.Raise vbObjectError + 2813, , "Set the approved UPL revision for PO " & po & " in ERP Excel Setup."
                        If StrComp(CStr(row("upl_revision")), upRev, vbTextCompare) <> 0 Then GoTo NextRow
                    End If
                End If
                key = ES_RuleGroup(dataset, row)
                rank = ES_RuleRank(row)
                If Not best.Exists(key) Then
                    best.Add key, rank
                ElseIf CLng(best(key)) < rank Then
                    best(key) = rank
                End If
                candidates.Add row
            End If
        End If
NextRow:
    Next row
    For Each row In candidates
        If ES_RuleRank(row) = CLng(best(ES_RuleGroup(dataset, row))) Then result.Add row
    Next row
    Set ES_Rows = result
End Function

Private Function ES_RuleGroup(ByVal dataset As String, ByVal row As Object) As String
    Select Case dataset
    Case "material_upl_links": ES_RuleGroup = CStr(row("item_code"))
    Case "tag_upl_links": ES_RuleGroup = CStr(row("tag_item"))
    Case "tag_definitions": ES_RuleGroup = CStr(row("item"))
    Case Else: ES_RuleGroup = CStr(row("id"))
    End Select
End Function

Private Function ES_RuleRank(ByVal row As Object) As Long
    If row.Exists("po") Then
        If Len(CStr(row("po"))) > 0 Then ES_RuleRank = 2
    End If
    If row.Exists("upl_revision") Then
        If Len(CStr(row("upl_revision"))) > 0 Then ES_RuleRank = ES_RuleRank + 1
    End If
End Function

Public Sub ES_OpenSetup()
    ThisWorkbook.FollowHyperlink "https://neosys.frappe.cloud/app/excel-setup"
End Sub

Public Sub ES_Status()
    MsgBox "Local Excel Setup revision: " & ES_Revision() & vbCrLf & "Refresh imports published setup; editing is in ERP Excel Setup.", vbInformation
End Sub

Public Sub ES_SnapshotRange(ByVal snapshots As Collection, ByVal ws As Worksheet, ByVal columns As String, ByVal minRows As Long)
    Dim parts As Variant, lastRow As Long, rg As Range
    parts = Split(columns, ":")
    lastRow = Application.Max(minRows, ws.Cells(ws.Rows.Count, parts(0)).End(xlUp).Row, ws.Cells(ws.Rows.Count, parts(UBound(parts))).End(xlUp).Row, 2)
    Set rg = ws.Range(parts(0) & "2:" & parts(UBound(parts)) & lastRow)
    snapshots.Add Array(rg, rg.Formula)
End Sub

Public Sub ES_WriteRegion(ByVal ws As Worksheet, ByVal firstColumn As Long, ByVal rows As Collection, ByVal fields As Variant)
    Dim lastRow As Long, row As Object, i As Long, j As Long, values() As Variant
    lastRow = 2
    For j = LBound(fields) To UBound(fields)
        lastRow = Application.Max(lastRow, ws.Cells(ws.Rows.Count, firstColumn + j - LBound(fields)).End(xlUp).Row)
    Next j
    ws.Range(ws.Cells(2, firstColumn), ws.Cells(lastRow, firstColumn + UBound(fields) - LBound(fields))).ClearContents
    If rows.Count = 0 Then Exit Sub
    ReDim values(1 To rows.Count, 1 To UBound(fields) - LBound(fields) + 1)
    For Each row In rows
        i = i + 1
        For j = LBound(fields) To UBound(fields)
            values(i, j - LBound(fields) + 1) = row(CStr(fields(j)))
        Next j
    Next row
    ws.Cells(2, firstColumn).Resize(rows.Count, UBound(values, 2)).NumberFormat = "@"
    ws.Cells(2, firstColumn).Resize(rows.Count, UBound(values, 2)).Value2 = values
End Sub

Public Sub ES_WriteSeed(ByVal datasets As Object, ByVal workbookType As String)
    Dim package As Object, target As Variant, stream As Object
    Set package = CreateObject("Scripting.Dictionary")
    package.Add "schema_version", 2
    package.Add "batch_id", workbookType & "-seed-" & Format$(Now, "yyyymmddhhnnss")
    package.Add "source", workbookType & " declared setup export"
    package.Add "datasets", datasets
    target = Application.GetSaveAsFilename(InitialFileName:=workbookType & "-excel-setup-seed.json", FileFilter:="JSON (*.json),*.json")
    If VarType(target) = vbBoolean Then Exit Sub
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 2: stream.Charset = "utf-8": stream.Open
    stream.WriteText JsonConverter.ConvertToJson(package, Whitespace:=2)
    stream.SaveToFile CStr(target), 2: stream.Close
    MsgBox "Seed exported. Import through ERP Excel Setup preview; resolve conflicts before publishing.", vbInformation
End Sub

Public Function ES_SeedId(ByVal kind As String, ByVal key As String) As String
    Dim token As String
    token = AC_Crypto.AC_Sha256Utf8B64(LCase$(Trim$(key)))
    token = Replace(Replace(Replace(token, "+", "-"), "/", "_"), "=", "")
    ES_SeedId = kind & "-" & token
End Function

Public Function ES_ProfileAliasForProject(ByVal erpProject As String, Optional ByVal selector As String = "") As String
    Dim link As Object, profile As Object, found As String, rank As Long, bestRank As Long
    Dim ambiguous As Boolean, hasLinks As Boolean
    bestRank = -1
    For Each link In ES_AllRows("project_builder_links")
        If CBool(link("enabled")) And StrComp(CStr(link("project")), erpProject, vbTextCompare) = 0 Then
            hasLinks = True
            For Each profile In ES_AllRows("builder_profiles")
                If CBool(profile("enabled")) And CStr(profile("id")) = CStr(link("profile")) Then
                    rank = -1
                    If Len(Trim$(selector)) > 0 Then
                        If StrComp(CStr(link("stream")), selector, vbTextCompare) = 0 Or StrComp(CStr(link("stream_alias")), selector, vbTextCompare) = 0 Then
                            rank = 3
                        ElseIf StrComp(CStr(profile("alias")), selector, vbTextCompare) = 0 Then
                            rank = 2
                        End If
                    ElseIf Len(CStr(link("stream"))) = 0 Then
                        rank = 1
                    End If
                    If rank >= 0 Then
                        If rank > bestRank Then
                            bestRank = rank: found = CStr(profile("alias")): ambiguous = False
                        ElseIf rank = bestRank And StrComp(found, CStr(profile("alias")), vbTextCompare) <> 0 Then
                            ambiguous = True
                        End If
                    End If
                End If
            Next profile
        End If
    Next link
    If ambiguous Or (hasLinks And Len(found) = 0) Then Err.Raise vbObjectError + 2841, , "Select an explicitly assigned Builder profile or Project stream for " & erpProject
    ES_ProfileAliasForProject = found
End Function

Public Function ES_BuilderAliasForPo(ByVal poOrProject As String, Optional ByVal selector As String = "") As String
    Dim row As Object, project As String
    For Each row In ES_AllRows("projects")
        If CBool(row("enabled")) Then
            If StrComp(CStr(row("po")), Trim$(poOrProject), vbTextCompare) = 0 Or StrComp(CStr(row("project")), Trim$(poOrProject), vbTextCompare) = 0 Then
                If Len(project) > 0 And project <> CStr(row("project")) Then Err.Raise vbObjectError + 2841, , "Ambiguous canonical Project for PO " & poOrProject
                project = CStr(row("project"))
            End If
        End If
    Next row
    If Len(project) > 0 Then ES_BuilderAliasForPo = ES_ProfileAliasForProject(project, selector)
End Function
