# 목차의 '#' 를 실제 쪽 번호로 채우고 PDF 로 뽑는다. 목차 줄과 본문 제목이 같은 글자여야 한다.
param([string[]]$Files)
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
foreach ($f in $Files) {
    $doc = $word.Documents.Open($f, $false, $false)
    $pages = @{}
    $tocs = @()
    foreach ($p in $doc.Paragraphs) {
        $t = $p.Range.Text.TrimEnd([char]13, [char]7)
        if ($t -match "^(.+)`t#$") { $tocs += ,@($p, $Matches[1].Trim()) ; continue }
        if ($t -match '^(\d+(\.\d+)*\.?|부록 [A-Z]\.) ' -and -not $pages.ContainsKey($t.Trim())) { $pages[$t.Trim()] = $p.Range.Information(3) }  # wdActiveEndAdjustedPageNumber. 부록 A. 도 제목으로 센다 (2026-09-25)
    }
    $missing = @()
    foreach ($e in $tocs) {
        $p = $e[0]; $key = $e[1]
        if ($pages.ContainsKey($key)) {
            $r = $p.Range; $r.MoveEnd(1, -1) | Out-Null   # 문단 기호 제외
            $r.Find.Execute("#", $false, $false, $false, $false, $false, $true, 0, $false, [string]$pages[$key], 1) | Out-Null
        } else { $missing += $key }
    }
    $doc.Save()
    $pdf = [IO.Path]::ChangeExtension($f, ".pdf")
    $pdf = Join-Path $env:TEMP ([IO.Path]::GetFileName($pdf))
    $doc.ExportAsFixedFormat($pdf, 17)
    $doc.Close($false)
    "{0}: toc {1}, missing [{2}], pages {3}, pdf {4}" -f (Split-Path $f -Leaf), $tocs.Count, ($missing -join ', '), $doc_pages, $pdf
}
$word.Quit()
