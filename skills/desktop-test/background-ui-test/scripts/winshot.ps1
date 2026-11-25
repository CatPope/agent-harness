param([string]$Name = "shot.png", [string]$OutDir = ".", [string]$Title = "", [string]$Process = "", [long]$Hwnd = 0, [switch]$List)
# 창 하나만 PrintWindow(PW_RENDERFULLCONTENT)로 캡처한다. 다른 가상 데스크톱에 있어도 찍힌다.
# 최소화된 창은 빈 그림(수백 바이트)이 나온다. 조건에 맞는 창이 여럿이면 가장 큰 창을 고른다. 확실히 하려면 -Hwnd.
Add-Type -AssemblyName System.Drawing
Add-Type -TypeDefinition @'
using System; using System.Text; using System.Runtime.InteropServices;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr p);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint f);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public struct RECT { public int L, T, R, B; }
}
'@
[W]::SetProcessDPIAware() | Out-Null
$wins = New-Object System.Collections.ArrayList
[W]::EnumWindows({ param($h, $p)
  if ([W]::IsWindowVisible($h)) {
    $sb = New-Object System.Text.StringBuilder 512; [W]::GetWindowText($h, $sb, 512) | Out-Null
    if ($sb.Length -gt 0) { $procId = 0; [W]::GetWindowThreadProcessId($h, [ref]$procId) | Out-Null
      $pn = (Get-Process -Id $procId -ErrorAction SilentlyContinue).Name
      [void]$wins.Add([pscustomobject]@{ H = $h; Title = $sb.ToString(); Proc = $pn }) } }
  $true }, [IntPtr]::Zero) | Out-Null
if ($List) { $wins | Select Proc, Title | Format-Table -AutoSize | Out-String -Width 300; return }
$w = $wins | ? { ($Title -eq "" -or $_.Title -like "*$Title*") -and ($Process -eq "" -or $_.Proc -like $Process) } | Sort-Object { $W_size = New-Object W+RECT; [W]::GetWindowRect($_.H, [ref]$W_size) | Out-Null; -(($W_size.R - $W_size.L) * ($W_size.B - $W_size.T)) } | Select -First 1
if ($Hwnd) { $w = $wins | ? { [long]$_.H -eq $Hwnd } | Select -First 1 }
if (-not $w) { "창 없음: Title=$Title Process=$Process"; return }
$r = New-Object W+RECT; [W]::GetWindowRect($w.H, [ref]$r) | Out-Null
$bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
$g = [System.Drawing.Graphics]::FromImage($bmp); $hdc = $g.GetHdc()
[W]::PrintWindow($w.H, $hdc, 2) | Out-Null
$g.ReleaseHdc($hdc); $g.Dispose()
New-Item -ItemType Directory -Force $OutDir | Out-Null
$out = Join-Path (Resolve-Path $OutDir) $Name
$bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
"$out [$($w.Proc)] $($w.Title) ($(Get-Date -Format 'HH:mm:ss'))"
