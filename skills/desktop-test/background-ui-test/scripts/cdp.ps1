param(
  [Parameter(Mandatory)][int]$Port,
  [ValidateSet("targets","eval","click","type","key","shot","text","upload")][string]$Action = "targets",
  [string]$Url = "",          # 대상 페이지 주소 일부(여러 탭이면 고른다)
  [string]$Selector = "",     # click/upload: CSS 선택자
  [string]$Text = "",         # click: 보이는 글자로 찾기 / type: 칠 글자 / eval: JS / key: Enter, Tab ...
  [string]$File = "",         # shot: 저장 경로 / upload: 올릴 파일
  [int]$Delay = 40            # 글자 사이 간격(ms)
)
# Chrome DevTools Protocol 로 페이지에 실제 마우스·키 이벤트를 넣는다. OS 포커스를 건드리지 않는다.
$ErrorActionPreference = "Stop"
$targets = Invoke-RestMethod "http://127.0.0.1:$Port/json/list"
$pages = @($targets | ? { $_.type -eq "page" -and ($Url -eq "" -or $_.url -like "*$Url*") })
if ($Action -eq "targets") { $targets | ? type -eq page | Select title, url | Format-Table -AutoSize | Out-String -Width 250; return }
if (-not $pages) { throw "페이지 없음: $Url" }
$ws = New-Object System.Net.WebSockets.ClientWebSocket
$ws.Options.KeepAliveInterval = [TimeSpan]::Zero
$ws.ConnectAsync([Uri]$pages[0].webSocketDebuggerUrl, [Threading.CancellationToken]::None).Wait()
$script:id = 0
$script:events = New-Object System.Collections.ArrayList
function Recv() {
  $buf = New-Object byte[] 1048576; $ms = New-Object System.IO.MemoryStream
  do { $seg = New-Object ArraySegment[byte] -ArgumentList (, $buf); $r = $ws.ReceiveAsync($seg, [Threading.CancellationToken]::None).Result; $ms.Write($buf, 0, $r.Count) } while (-not $r.EndOfMessage)
  [Text.Encoding]::UTF8.GetString($ms.ToArray()) | ConvertFrom-Json
}
function Send($method, $params = @{}) {
  $script:id++; $myId = $script:id
  $json = @{ id = $myId; method = $method; params = $params } | ConvertTo-Json -Depth 10 -Compress
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $ws.SendAsync((New-Object ArraySegment[byte] -ArgumentList (, $bytes)), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [Threading.CancellationToken]::None).Wait()
  while ($true) { $m = Recv; if ($m.id -eq $myId) { if ($m.error) { throw "$method : $($m.error.message)" }; return $m.result }; [void]$script:events.Add($m) }
}
function Eval($js) { $r = Send "Runtime.evaluate" @{ expression = $js; returnByValue = $true; awaitPromise = $true }; if ($r.exceptionDetails) { throw $r.exceptionDetails.exception.description }; $r.result.value }
function Center() {
  # 선택자 또는 보이는 글자로 요소를 찾아 화면 안으로 스크롤하고 가운데 좌표를 돌려준다
  $sel = $Selector | ConvertTo-Json; $txt = $Text | ConvertTo-Json
  $js = @"
(() => { let el = null; const sel = $sel, txt = $txt;
  if (sel) { const all = [...document.querySelectorAll(sel)]; el = txt ? all.find(e => e.innerText.trim().includes(txt) || (e.value||'').includes(txt) || (e.getAttribute('aria-label')||'').includes(txt)) : all[0]; }
  else { const c = [...document.querySelectorAll('button,a,[role=button],label,input,[onclick],li,td,div,span')].filter(e => e.offsetParent !== null);
    el = c.find(e => e.innerText && e.innerText.trim() === txt) || c.find(e => (e.getAttribute('aria-label')||'') === txt) || c.find(e => e.innerText && e.innerText.trim().startsWith(txt)); }
  if (!el) return null; el.scrollIntoView({block:'center'}); const r = el.getBoundingClientRect();
  return { x: r.left + r.width/2, y: r.top + r.height/2, tag: el.tagName, label: (el.innerText||el.value||el.getAttribute('aria-label')||'').trim().slice(0,60) }; })()
"@
  $p = Eval $js; if (-not $p) { throw "요소 없음: sel=$Selector text=$Text" }; $p
}
function MouseClick($x, $y) {
  Send "Input.dispatchMouseEvent" @{ type = "mouseMoved"; x = $x; y = $y } | Out-Null; Start-Sleep -Milliseconds 80
  Send "Input.dispatchMouseEvent" @{ type = "mousePressed"; x = $x; y = $y; button = "left"; clickCount = 1 } | Out-Null; Start-Sleep -Milliseconds 60
  Send "Input.dispatchMouseEvent" @{ type = "mouseReleased"; x = $x; y = $y; button = "left"; clickCount = 1 } | Out-Null
}
# 창이 뒤에 있어도 페이지는 포커스를 가진 것처럼 동작하게 한다(포커스 이벤트, :focus)
Send "Emulation.setFocusEmulationEnabled" @{ enabled = $true } | Out-Null
switch ($Action) {
  "eval"  { Eval $Text | ConvertTo-Json -Depth 6 }
  "text"  { Eval "document.body.innerText" }
  "click" { $p = Center; MouseClick $p.x $p.y; "click ok: <$($p.tag)> $($p.label) @($([int]$p.x),$([int]$p.y))" }
  "type"  {
    foreach ($ch in $Text.ToCharArray()) {
      $s = [string]$ch
      if ($s -match '^[\x20-\x7e]$') {
        Send "Input.dispatchKeyEvent" @{ type = "keyDown"; text = $s; key = $s; unmodifiedText = $s } | Out-Null
        Send "Input.dispatchKeyEvent" @{ type = "keyUp"; key = $s } | Out-Null
      } else { Send "Input.insertText" @{ text = $s } | Out-Null }   # 한글은 IME 확정 입력처럼 넣는다
      Start-Sleep -Milliseconds $Delay
    }
    "type ok: $($Text.Length)자" }
  "key"   {
    $codes = @{ Enter = 13; Tab = 9; Escape = 27; Backspace = 8 }
    $vk = $codes[$Text]; $extra = @{}; if ($Text -eq "Enter") { $extra.text = "`r" }
    Send "Input.dispatchKeyEvent" (@{ type = "rawKeyDown"; key = $Text; code = $Text; windowsVirtualKeyCode = $vk } ) | Out-Null
    if ($extra.text) { Send "Input.dispatchKeyEvent" @{ type = "char"; text = "`r"; key = "Enter" } | Out-Null }
    Send "Input.dispatchKeyEvent" @{ type = "keyUp"; key = $Text; code = $Text; windowsVirtualKeyCode = $vk } | Out-Null
    "key ok: $Text" }
  "shot"  { $r = Send "Page.captureScreenshot" @{ format = "png" }; [IO.File]::WriteAllBytes($File, [Convert]::FromBase64String($r.data)); "shot ok: $File" }
  "upload" {
    # 실제처럼 업로드 버튼을 누르되, 뜨는 파일 선택 창은 CDP 가 가로채 파일을 넣는다
    Send "Page.enable" | Out-Null
    Send "Page.setInterceptFileChooserDialog" @{ enabled = $true } | Out-Null
    $p = Center; MouseClick $p.x $p.y
    $ev = $null; $deadline = (Get-Date).AddSeconds(5)
    while (-not $ev -and (Get-Date) -lt $deadline) { $ev = $script:events | ? { $_.method -eq "Page.fileChooserOpened" } | Select -First 1; if (-not $ev) { [void]$script:events.Add((Recv)) } }
    if (-not $ev) { throw "파일 선택 창이 열리지 않음" }
    Send "DOM.setFileInputFiles" @{ files = @($File); backendNodeId = $ev.params.backendNodeId } | Out-Null
    Send "Page.setInterceptFileChooserDialog" @{ enabled = $false } | Out-Null
    "upload ok: $File (버튼 <$($p.tag)> $($p.label))" }
}
$ws.Dispose()
