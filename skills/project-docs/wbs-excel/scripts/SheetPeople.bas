Option Explicit

Private Sub Worksheet_Activate()
    RebuildPeople
End Sub

Private Sub Worksheet_Change(ByVal Target As Range)
    PushToSource Target
End Sub
