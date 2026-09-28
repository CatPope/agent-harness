Option Explicit
' 주간발표회 WBS — 일정 관리(원본) <-> 인원별(참조) 동기화
' 인원별 시트는 열 때마다 원본에서 다시 조립되고, 인원별에서 고친 값은 원본에 써 넣어진다.
' 2026-09-24 v2.4.0: 재조립을 블록 단위·수동 계산으로 바꿈. 행마다 서식을 붙여넣던 방식은 13~23초 걸렸고
' 조건부 서식 규칙이 84개로 불어났다. 지금은 규칙을 지우고 전체 범위에 두 개만 다시 건다.

Public Const SRC_NAME As String = "일정 관리"
Public Const DST_NAME As String = "인원별"
Public Const TPL_NAME As String = "_서식"
Public Const CFG_NAME As String = "설정"
Public Const FIRST_ROW As Long = 8
Public Const REBUILD_ROWS As Long = 500
' 작업 제목은 모든 행에서 C:G 병합 셀(C)에 있다. 하위 항목은 앞 빈칸으로 들여쓴다 (v2.3.0, 2026-09-24).
Public Const C_TITLE As Long = 3, C_TITLE_END As Long = 7, C_WHO As Long = 8, C_DONE As Long = 9
Public Const C_PRIO As Long = 10, C_W0 As Long = 11, C_W1 As Long = 12
Public Const C_BAR0 As Long = 13                          ' M 열부터 타임라인. 끝 열은 _서식 1행의 주 번호로 잰다
' 막대 색. 파이썬 생성기 wbs_build.py 의 GREEN/YELLOW 와 같아야 한다
Public Const COLOR_S As Long = 198 + 239 * 256& + 206 * 65536      ' C6EFCE 초록 Should
Public Const COLOR_C As Long = 255 + 235 * 256& + 156 * 65536      ' FFEB9C 노랑 Could

Public Function ColLetter(col As Long) As String
    ColLetter = Split(ThisWorkbook.Worksheets(SRC_NAME).Cells(1, col).Address(True, False), "$")(0)
End Function

Public Function SrcLastRow() As Long
    Dim ws As Worksheet: Set ws = ThisWorkbook.Worksheets(SRC_NAME)
    SrcLastRow = ws.Cells(ws.Rows.Count, C_TITLE).End(xlUp).Row
End Function

Public Function IsTaskRow(ws As Worksheet, r As Long) As Boolean
    IsTaskRow = InStr(CStr(ws.Cells(r, 1).Value), ".") > 0
End Function

' 하위 항목이 없는 작업 행 = 완료 비율이 수식이 아닌 행
Public Function IsLeafRow(ws As Worksheet, r As Long) As Boolean
    IsLeafRow = IsTaskRow(ws, r) And Not ws.Cells(r, C_DONE).HasFormula
End Function

Public Function SrcRowOf(key As String) As Long
    Dim ws As Worksheet, r As Long
    If InStr(key, ".") = 0 Then Exit Function
    Set ws = ThisWorkbook.Worksheets(SRC_NAME)
    For r = FIRST_ROW To SrcLastRow()
        If CStr(ws.Cells(r, 1).Value) = key Then SrcRowOf = r: Exit Function
    Next
End Function

' 인원별 시트의 셀이 원본을 참조하는 수식. 파이썬 생성기의 ref_formulas 와 같아야 한다.
Public Function FormulaFor(col As Long, srcRow As Long) As String
    Dim s As String: s = "'" & SRC_NAME & "'!"
    Select Case col
        Case 1: FormulaFor = "=" & s & "A" & srcRow
        Case Else: FormulaFor = "=" & s & ColLetter(col) & srcRow
    End Select
End Function

' 작업 제목 칸 C:G 를 행마다 병합한다 (서식 복사가 병합을 놓쳐도 보장)
Private Sub MergeTitle(ws As Worksheet, r0 As Long, r1 As Long)
    ws.Range(ws.Cells(r0, C_TITLE), ws.Cells(r1, C_TITLE_END)).Merge True
End Sub

Private Function SortKey(ws As Worksheet, r As Long) As String
    Dim parts() As String, i As Long, k As String
    parts = Split(CStr(ws.Cells(r, 1).Value), ".")
    For i = LBound(parts) To UBound(parts)
        k = k & Format(Val(parts(i)), "000")
    Next
    SortKey = Format(Val(ws.Cells(r, C_W0).Value), "00") & Format(Val(ws.Cells(r, C_W1).Value), "00") & k
End Function

' 막대 조건부 서식을 전체 범위에 두 개만 다시 건다. 파이썬 put_header 의 FormulaRule 과 같은 식이다.
Private Sub ResetBars(ws As Worksheet, lastRow As Long)
    Dim tpl As Worksheet, lastCol As Long, rng As Range, a As String
    Set tpl = ThisWorkbook.Worksheets(TPL_NAME)
    lastCol = tpl.Cells(1, tpl.Columns.Count).End(xlToLeft).Column
    ws.Range(ws.Rows(FIRST_ROW), ws.Rows(FIRST_ROW + REBUILD_ROWS)).FormatConditions.Delete
    Set rng = ws.Range(ws.Cells(FIRST_ROW, C_BAR0), ws.Cells(lastRow, lastCol))
    a = ColLetter(C_BAR0)
    With rng.FormatConditions.Add(Type:=xlExpression, Formula1:= _
        "=AND($" & ColLetter(C_PRIO) & FIRST_ROW & "=""S""," & a & "$1>=$" & ColLetter(C_W0) & FIRST_ROW & "," & a & "$1<=$" & ColLetter(C_W1) & FIRST_ROW & ")")
        .Interior.Color = COLOR_S
        .StopIfTrue = True
    End With
    With rng.FormatConditions.Add(Type:=xlExpression, Formula1:= _
        "=AND($" & ColLetter(C_PRIO) & FIRST_ROW & "=""C""," & a & "$1>=$" & ColLetter(C_W0) & FIRST_ROW & "," & a & "$1<=$" & ColLetter(C_W1) & FIRST_ROW & ")")
        .Interior.Color = COLOR_C
        .StopIfTrue = True
    End With
End Sub

' 인원별 시트를 일정 관리 시트에서 다시 만든다 (시트를 열 때 자동 호출)
Public Sub RebuildPeople()
    Dim src As Worksheet, dst As Worksheet, tpl As Worksheet, cfg As Worksheet
    Dim ev As Boolean, su As Boolean, calc As Long
    Dim r As Long, p As Long, i As Long, j As Long, tmp As Long, cnt As Long, out As Long, secRow As Long, lastSrc As Long
    Dim rows() As Long, nm As String, who As String, allRefs As String
    Dim leaf() As Boolean, keys() As String, cols As Variant, c As Long, k As Long, arr() As Variant

    Set src = ThisWorkbook.Worksheets(SRC_NAME): Set dst = ThisWorkbook.Worksheets(DST_NAME)
    Set tpl = ThisWorkbook.Worksheets(TPL_NAME): Set cfg = ThisWorkbook.Worksheets(CFG_NAME)
    ev = Application.EnableEvents: su = Application.ScreenUpdating: calc = Application.Calculation
    Application.EnableEvents = False: Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    On Error GoTo fin

    ' 원본은 한 번만 훑어 캐시한다 — 셀 접근이 제일 느리다
    lastSrc = SrcLastRow()
    ReDim leaf(FIRST_ROW To lastSrc): ReDim keys(FIRST_ROW To lastSrc)
    For r = FIRST_ROW To lastSrc
        leaf(r) = IsLeafRow(src, r)
        If leaf(r) Then
            keys(r) = SortKey(src, r)
            allRefs = allRefs & IIf(Len(allRefs) > 0, ",", "") & "'" & SRC_NAME & "'!I" & r
        End If
    Next

    With dst.Range(dst.Rows(FIRST_ROW), dst.Rows(FIRST_ROW + REBUILD_ROWS))
        .UnMerge
        .Clear
    End With

    cols = Array(1, C_TITLE, C_WHO, C_DONE, C_PRIO, C_W0, C_W1)
    out = FIRST_ROW
    For p = 2 To cfg.Cells(cfg.Rows.Count, 1).End(xlUp).Row
        nm = CStr(cfg.Cells(p, 1).Value)
        If Len(nm) = 0 Then GoTo nextPerson
        cnt = 0: ReDim rows(1 To 1)
        For r = FIRST_ROW To lastSrc
            If leaf(r) Then
                who = CStr(src.Cells(r, C_WHO).Value)
                ' "전원" 은 비고(미참여 등)가 없는 사람에게만 붙는다
                If (who = "전원" And Len(cfg.Cells(p, 3).Value) = 0) Or InStr(who, nm) > 0 Then
                    cnt = cnt + 1: ReDim Preserve rows(1 To cnt): rows(cnt) = r
                End If
            End If
        Next
        For i = 2 To cnt                                  ' 시작주·끝주·번호 순
            tmp = rows(i): j = i - 1
            Do While j >= 1
                If keys(rows(j)) > keys(tmp) Then rows(j + 1) = rows(j): j = j - 1 Else Exit Do
            Loop
            rows(j + 1) = tmp
        Next

        ' 구분 행
        tpl.Rows(2).Copy Destination:=dst.Rows(out)
        dst.Rows(out).RowHeight = tpl.Rows(2).RowHeight
        MergeTitle dst, out, out
        dst.Cells(out, 1).Value = CStr(p - 1)
        dst.Cells(out, C_TITLE).Value = nm & " — " & cfg.Cells(p, 2).Value _
            & IIf(cnt > 0, " (" & cnt & "건)", "") _
            & IIf(Len(cfg.Cells(p, 3).Value) > 0, " — " & cfg.Cells(p, 3).Value, "")
        secRow = out: out = out + 1
        ' 항목 행 — 서식은 블록으로 한 번에 복사하고, 수식은 열마다 배열로 한 번에 넣는다
        If cnt > 0 Then
            tpl.Rows(3).Copy Destination:=dst.Rows(out & ":" & (out + cnt - 1))
            dst.Rows(out & ":" & (out + cnt - 1)).RowHeight = tpl.Rows(3).RowHeight
            MergeTitle dst, out, out + cnt - 1
            For k = LBound(cols) To UBound(cols)
                c = CLng(cols(k))
                ReDim arr(1 To cnt, 1 To 1)
                For i = 1 To cnt
                    arr(i, 1) = FormulaFor(c, rows(i))
                Next
                dst.Range(dst.Cells(out, c), dst.Cells(out + cnt - 1, c)).Formula = arr
            Next
            dst.Cells(secRow, C_DONE).Formula = "=AVERAGE(I" & out & ":I" & (out + cnt - 1) & ")"
            out = out + cnt
        End If
nextPerson:
    Next

    tpl.Rows(4).Copy Destination:=dst.Rows(out)
    MergeTitle dst, out, out
    dst.Cells(out, C_TITLE).Value = "전체 진척률"
    If Len(allRefs) > 0 Then dst.Cells(out, C_DONE).Formula = "=AVERAGE(" & allRefs & ")"
    ResetBars dst, out
fin:
    Application.CutCopyMode = False
    Application.Calculation = calc
    Application.ScreenUpdating = su
    Application.EnableEvents = ev
    If Err.Number <> 0 Then MsgBox "인원별 시트를 다시 만들지 못했습니다: " & Err.Description, vbExclamation
End Sub

' 인원별 시트에서 고친 값을 원본에 써 넣고, 셀은 다시 참조 수식으로 되돌린다
Public Sub PushToSource(Target As Range)
    Dim src As Worksheet, dst As Worksheet, c As Range, r As Long, col As Long, ev As Boolean
    ev = Application.EnableEvents
    Application.EnableEvents = False
    On Error GoTo fin
    Set src = ThisWorkbook.Worksheets(SRC_NAME): Set dst = ThisWorkbook.Worksheets(DST_NAME)
    For Each c In Target.Cells
        col = c.Column
        If c.Row >= FIRST_ROW And Not c.HasFormula Then
            If col = C_TITLE Or col = C_WHO Or col = C_DONE Or col = C_PRIO Or col = C_W0 Or col = C_W1 Then
                r = SrcRowOf(CStr(dst.Cells(c.Row, 1).Value))
                If r > 0 Then
                    src.Cells(r, col).Value = c.Value
                    c.Formula = FormulaFor(col, r)
                End If
            End If
        End If
    Next
fin:
    Application.EnableEvents = ev
End Sub
