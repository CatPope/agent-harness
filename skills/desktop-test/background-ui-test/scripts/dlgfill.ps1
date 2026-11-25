param([Parameter(Mandatory)][long]$Hwnd, [Parameter(Mandatory)][string]$Path, [switch]$NoClick)
# Windows 파일·폴더 선택 창의 이름 칸(컨트롤 1148/1152 안 Edit)에 경로를 넣고 확인 버튼(ID 1)을 누른다.
# 창을 활성화하지 않는다(WM_SETTEXT 는 SendMessage, BM_CLICK 은 PostMessage).
# 다른 프로세스의 창이라 GetWindowText 로 다시 읽으면 빈 값이 나올 수 있다. 값은 들어가 있다.
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public class Dlg {
  [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr after, string cls, string title);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern IntPtr SendMessage(IntPtr h, int msg, IntPtr w, string l);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, int msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  delegate bool P(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, P f, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr h);
  static string Cls(IntPtr h) { var s = new StringBuilder(128); GetClassName(h, s, 128); return s.ToString(); }
  // 이름 칸: ComboBoxEx32(1148 또는 1152) 아래 ComboBox 아래 Edit
  public static IntPtr NameEdit(IntPtr d) {
    IntPtr found = IntPtr.Zero;
    EnumChildWindows(d, (h, l) => {
      if (Cls(h) != "Edit") return true;
      IntPtr p = GetParent(h); IntPtr pp = GetParent(p);
      foreach (int id in new[] { GetDlgCtrlID(h), GetDlgCtrlID(p), GetDlgCtrlID(pp) })
        if (id == 1148 || id == 1152) { found = h; return false; }
      return true; }, IntPtr.Zero);
    return found;
  }
}
'@ -ErrorAction SilentlyContinue
$d = [IntPtr]$Hwnd
$edit = [Dlg]::NameEdit($d)
if ($edit -eq [IntPtr]::Zero) { "이름 칸 못 찾음"; exit 1 }
$fg0 = [Dlg]::GetForegroundWindow()
[Dlg]::SendMessage($edit, 0x000C, [IntPtr]::Zero, $Path) | Out-Null   # WM_SETTEXT
$sb = New-Object Text.StringBuilder 1024; [Dlg]::GetWindowText($edit, $sb, 1024) | Out-Null
"칸 값: $sb"
if (-not $NoClick) {
  $ok = [Dlg]::GetDlgItem($d, 1)
  $bt = New-Object Text.StringBuilder 64; [Dlg]::GetWindowText($ok, $bt, 64) | Out-Null
  [Dlg]::PostMessage($ok, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null   # BM_CLICK. SendMessage 는 대화상자가 닫힐 때까지 돌아오지 않을 수 있다
  "눌름: $bt"
}
"앞 창 바뀜: " + ($fg0 -ne [Dlg]::GetForegroundWindow())
