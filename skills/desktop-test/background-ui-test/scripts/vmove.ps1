param([long]$Hwnd = 0, [string]$Process = "", [long]$RefHwnd = 0, [string]$RefProcess = "", [switch]$Check)
# 창을 기준 창(-RefHwnd 또는 -RefProcess, 보통 에이전트 세션이 도는 터미널)이 있는 가상 데스크톱으로 옮긴다.
# 옮기기는 Windows 10 19041~19045 에서 확인한 내부 인터페이스다. Windows 11 은 내부 GUID 가 달라 그대로는 안 된다(확인 안 함). -Check 는 공개 API 라 어디서나 된다.
# -Check: 사용자가 지금 시험 데스크톱(기준 창의 데스크톱)에 있는지만 알려 준다.
$src = @'
using System; using System.Runtime.InteropServices;
[ComImport, Guid("a5cd92ff-29be-454c-8d04-d82879fb3f1b"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IVirtualDesktopManager { [PreserveSig] int IsWindowOnCurrentVirtualDesktop(IntPtr h, out int on); [PreserveSig] int GetWindowDesktopId(IntPtr h, out Guid id); }
[ComImport, Guid("372E1D3B-38D3-42E4-A15B-8AB2B178F513"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface IApplicationView { }
[ComImport, Guid("FF72FFDD-BE7E-43FC-9C03-AD81681E88E4"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)] interface IVirtualDesktop { bool IsViewVisible(IApplicationView v); Guid GetId(); }
[ComImport, Guid("F31574D6-B682-4CDC-BD56-1827860ABEC6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IVirtualDesktopManagerInternal {
  int GetCount(); void MoveViewToDesktop(IApplicationView view, IVirtualDesktop desktop); bool CanViewMoveDesktops(IApplicationView view);
  IVirtualDesktop GetCurrentDesktop(); void GetDesktops([MarshalAs(UnmanagedType.IUnknown)] out object d);
  [PreserveSig] int GetAdjacentDesktop(IVirtualDesktop from, int dir, out IVirtualDesktop d); void SwitchDesktop(IVirtualDesktop d);
  IVirtualDesktop CreateDesktop(); void RemoveDesktop(IVirtualDesktop d, IVirtualDesktop fallback); IVirtualDesktop FindDesktop(ref Guid id);
}
[ComImport, Guid("1841C6D7-4F9D-42C0-AF41-8747538F10E5"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IApplicationViewCollection {
  [PreserveSig] int GetViews([MarshalAs(UnmanagedType.IUnknown)] out object a); [PreserveSig] int GetViewsByZOrder([MarshalAs(UnmanagedType.IUnknown)] out object a);
  [PreserveSig] int GetViewsByAppUserModelId([MarshalAs(UnmanagedType.LPWStr)] string id, [MarshalAs(UnmanagedType.IUnknown)] out object a);
  [PreserveSig] int GetViewForHwnd(IntPtr h, out IApplicationView v);
}
[ComImport, Guid("6D5140C1-7436-11CE-8034-00AA006009FA"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IServiceProvider10 { [return: MarshalAs(UnmanagedType.IUnknown)] object QueryService(ref Guid service, ref Guid riid); }
public static class VMove {
  static IVirtualDesktopManager Pub() { return (IVirtualDesktopManager)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("aa509086-5ca9-4c25-8f95-589d3c07b48a"))); }
  public static Guid DeskOf(IntPtr h) { Guid g; Pub().GetWindowDesktopId(h, out g); return g; }
  public static bool OnCurrent(IntPtr h) { int on; Pub().IsWindowOnCurrentVirtualDesktop(h, out on); return on != 0; }
  public static string Move(IntPtr h, Guid target) {
    var shell = (IServiceProvider10)Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("C2F03A33-21F5-47FA-B4BB-156362A2F239")));
    Guid sMgr = new Guid("C5E0CDCA-7B6E-41B2-9FC4-D93975CC467B"), iMgr = typeof(IVirtualDesktopManagerInternal).GUID;
    var mgr = (IVirtualDesktopManagerInternal)shell.QueryService(ref sMgr, ref iMgr);
    Guid sCol = typeof(IApplicationViewCollection).GUID, iCol = typeof(IApplicationViewCollection).GUID;
    var col = (IApplicationViewCollection)shell.QueryService(ref sCol, ref iCol);
    IApplicationView view; int hr = col.GetViewForHwnd(h, out view); if (hr != 0) return "view 없음 hr=" + hr;
    mgr.MoveViewToDesktop(view, mgr.FindDesktop(ref target)); return "moved";
  }
}
'@
if (-not ("VMove" -as [type])) { Add-Type -TypeDefinition $src }
if ($RefHwnd -eq 0 -and $RefProcess) { $RefHwnd = (Get-Process $RefProcess -EA SilentlyContinue | ? MainWindowHandle -ne 0 | Select -First 1).MainWindowHandle }
if (-not $RefHwnd) { "기준 창이 없다. -RefHwnd 또는 -RefProcess 를 준다"; exit 1 }
$target = [VMove]::DeskOf([IntPtr]$RefHwnd)
if ($Check) { if ([VMove]::OnCurrent([IntPtr]$RefHwnd)) { "here" } else { "away" }; return }
$hs = @(); if ($Hwnd) { $hs += $Hwnd }
if ($Process) { $hs += Get-Process $Process -EA SilentlyContinue | ? MainWindowHandle -ne 0 | % { [long]$_.MainWindowHandle } }
foreach ($h in $hs) {
  $before = [VMove]::DeskOf([IntPtr]$h)
  if ($before -eq $target) { "$h 이미 시험 데스크톱"; continue }
  "$h " + [VMove]::Move([IntPtr]$h, $target) + " ($($before.ToString().Substring(0,8)) -> $($target.ToString().Substring(0,8)))"
}
