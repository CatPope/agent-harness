param(
  [Parameter(Mandatory)][long]$Hwnd,
  [ValidateSet("dump","invoke","set","toggle","focus")][string]$Action = "dump",
  [string]$Name = "",            # 요소 이름(부분 일치)
  [string]$Type = "",            # ControlType 이름(Button, Edit, Hyperlink ...)
  [int]$Index = 0,               # 같은 조건 여러 개면 몇 번째
  [string]$Value = "",
  [int]$Max = 200
)
# UI Automation 으로 창 안의 요소를 찾아 누르거나 값을 넣는다. 실제 마우스·키보드를 쓰지 않는다.
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$A = [System.Windows.Automation.AutomationElement]
$root = $A::FromHandle([IntPtr]$Hwnd)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
$items = foreach ($e in $all) {
  try { $c = $e.Current } catch { continue }
  $t = $c.ControlType.ProgrammaticName -replace '^ControlType\.', ''
  if (($Name -eq "" -or $c.Name -like "*$Name*") -and ($Type -eq "" -or $t -eq $Type)) { [pscustomobject]@{ E = $e; Type = $t; Name = $c.Name; Id = $c.AutomationId } }
}
if ($Action -eq "dump") { $items | ? { $_.Name -or $_.Type -in 'Edit','Button','Hyperlink','CheckBox','ComboBox' } | Select -First $Max Type, Name, Id | Format-Table -AutoSize | Out-String -Width 250; return }
$it = @($items)[$Index]
if (-not $it) { "요소 없음: Name=$Name Type=$Type Index=$Index (후보 $(@($items).Count)개)"; exit 1 }
$e = $it.E
switch ($Action) {
  "invoke" { $p = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern, [ref]$p)) { $p.Invoke() }
    elseif ($e.TryGetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern, [ref]$p)) { $p.Select() }
    elseif ($e.TryGetCurrentPattern([System.Windows.Automation.LegacyIAccessiblePattern]::Pattern, [ref]$p)) { $p.DoDefaultAction() }
    else { "누를 수 없는 요소"; exit 1 } }
  "set" { $p = $null
    if ($e.TryGetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern, [ref]$p)) { $p.SetValue($Value) } else { "값을 넣을 수 없는 요소"; exit 1 } }
  "toggle" { $p = $e.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern); $p.Toggle() }
  "focus" { $e.SetFocus() }
}
"$Action ok: [$($it.Type)] $($it.Name)"
