# 보이는 창마다 가상 데스크톱 ID 를 붙여 보여 준다(IVirtualDesktopManager, 공개 API).
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
[ComImport, Guid("a5cd92ff-29be-454c-8d04-d82879fb3f1b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IVirtualDesktopManager {
  [PreserveSig] int IsWindowOnCurrentVirtualDesktop(IntPtr h, out int on);
  [PreserveSig] int GetWindowDesktopId(IntPtr h, out Guid id);
  [PreserveSig] int MoveWindowToDesktop(IntPtr h, ref Guid id);
}
public class VD {
  delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  public static List<string> List() {
    var m = (IVirtualDesktopManager)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("aa509086-5ca9-4c25-8f95-589d3c07b48a")));
    var rows = new List<string>();
    EnumWindows((h, p) => {
      if (!IsWindowVisible(h)) return true;
      var sb = new StringBuilder(512); GetWindowText(h, sb, 512); if (sb.Length == 0) return true;
      uint pid; GetWindowThreadProcessId(h, out pid);
      Guid id; int on = 0;
      if (m.GetWindowDesktopId(h, out id) != 0 || id == Guid.Empty) return true;
      m.IsWindowOnCurrentVirtualDesktop(h, out on);
      string pn = ""; try { pn = System.Diagnostics.Process.GetProcessById((int)pid).ProcessName; } catch {}
      rows.Add(h.ToInt64() + "\t" + pn + "\t" + id.ToString().Substring(0, 8) + "\t" + (on != 0 ? "현재" : "-") + "\t" + sb);
      return true; }, IntPtr.Zero);
    return rows;
  }
}
'@
[VD]::List()
