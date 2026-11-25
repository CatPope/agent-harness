param([Parameter(Mandatory)][long]$Hwnd)
# 대화상자 자식 창을 모두 보여 준다(핸들, 클래스, 컨트롤 ID, 부모). dlgfill.ps1 이 이름 칸을 못 찾을 때 쓴다.
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class DD {
  delegate bool P(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumChildWindows(IntPtr p, P f, IntPtr l);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern int GetDlgCtrlID(IntPtr h);
  [DllImport("user32.dll")] static extern IntPtr GetParent(IntPtr h);
  static string C(IntPtr h) { var s = new StringBuilder(128); GetClassName(h, s, 128); return s.ToString(); }
  public static List<string> All(IntPtr d) { var r = new List<string>();
    EnumChildWindows(d, (h, l) => { var t = new StringBuilder(128); GetWindowText(h, t, 128);
      r.Add(h.ToInt64() + " " + C(h) + " id=" + GetDlgCtrlID(h) + " <- " + C(GetParent(h)) + "/" + GetDlgCtrlID(GetParent(h)) + " '" + t + "'"); return true; }, IntPtr.Zero);
    return r; }
}
'@
[DD]::All([IntPtr]$Hwnd)
