$ErrorActionPreference = 'Stop'
Import-Module "$PSScriptRoot/../src/Reports.psm1" -Force
function Assert-True($Value, $Message) { if (-not $Value) { throw $Message } }
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('support-lab-' + [guid]::NewGuid().ToString('N'))
$evidence = [pscustomobject]@{schemaVersion=1; runId=[guid]::NewGuid().ToString('N'); timestampUtc=[DateTime]::UtcNow.ToString('o'); target='localhost'; port=8765; evidenceSource='controlled-test'; stages=@([pscustomobject]@{name='dns'; status='failure'; durationMs=1; facts=@{message='<script>alert(1)</script> & test'}; reason='test'}); finding='incomplete-evidence';nextStep='Review <the> evidence & verify.'}
try {
    $before = $evidence | ConvertTo-Json -Depth 10 -Compress
    $a = Save-SupportReport $evidence $temporary
    $original = [IO.File]::ReadAllText($a.JsonPath)
    $b = Save-SupportReport $evidence $temporary
    Assert-True ($a.JsonPath -ne $b.JsonPath) 'Paths must be distinct'
    Assert-True ($original -ceq [IO.File]::ReadAllText($a.JsonPath)) 'Prior evidence changed'
    $json = $original | ConvertFrom-Json
    Assert-True ($json.runId -ceq $evidence.runId) 'JSON identity mismatch'
    Assert-True ($json.stages[0].facts.message -ceq $evidence.stages[0].facts.message) 'JSON evidence changed'
    $html = [IO.File]::ReadAllText($a.HtmlPath)
    Assert-True ($html.Contains('&lt;script&gt;')) 'HTML must encode untrusted text'
    Assert-True (-not $html.Contains('<script>')) 'Executable HTML injection'
    Assert-True ($html.Contains($evidence.runId)) 'HTML identity mismatch'
    Assert-True ($html.Contains('controlled-test')) 'Evidence source absent'
    $occupied = Join-Path $temporary 'file-not-directory'
    [IO.File]::WriteAllText($occupied, 'preserve me')
    $failed = $false
    try { Save-SupportReport $evidence $occupied | Out-Null } catch { $failed=$true }
    Assert-True $failed 'Saving to a file must fail'
    Assert-True ([IO.File]::ReadAllText($occupied) -ceq 'preserve me') 'Existing file overwritten'
    Assert-True ($before -ceq ($evidence | ConvertTo-Json -Depth 10 -Compress)) 'Report saving mutated observations'
    Write-Output 'PASS: 11 report checks'
} finally {
    $resolved = [IO.Path]::GetFullPath($temporary)
    if ($resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath())) -and [IO.Path]::GetFileName($resolved).StartsWith('support-lab-') -and (Test-Path -LiteralPath $resolved)) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
