Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Encode-LabText($Value) { [Net.WebUtility]::HtmlEncode([string]$Value) }

function Save-SupportReport {
    param([Parameter(Mandatory)][pscustomobject]$Evidence, [Parameter(Mandatory)][string]$OutputDirectory)
    $folder = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
    [IO.Directory]::CreateDirectory($folder) | Out-Null
    $stem = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffZ') + '-' + [guid]::NewGuid().ToString('N')
    $jsonPath = Join-Path $folder "$stem.json"
    $htmlPath = Join-Path $folder "$stem.html"
    $json = $Evidence | ConvertTo-Json -Depth 12
    $cards = foreach ($stage in $Evidence.stages) {
        $facts = Encode-LabText ($stage.facts | ConvertTo-Json -Depth 8)
        $state = Encode-LabText $stage.status
        "<article><div class='row'><h2>$(Encode-LabText $stage.name)</h2><span class='state $state'>$state</span></div><p>$(Encode-LabText $stage.durationMs) ms · $(Encode-LabText $stage.reason)</p><pre>$facts</pre></article>"
    }
    $title = Encode-LabText $Evidence.finding.Replace('-', ' ')
    $html = @"
<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Support Diagnostics Lab — $title</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0c121a;color:#e7edf5;font:16px/1.6 system-ui,sans-serif}main{max-width:1050px;margin:auto;padding:40px 24px}header{border-bottom:1px solid #344150;padding-bottom:24px}h1{font-size:clamp(28px,5vw,44px);line-height:1.2;margin:12px 0;text-transform:capitalize}h2{font-size:17px;text-transform:uppercase;margin:0}p{color:#bfcbd9}.eyebrow{color:#cce7a4;text-transform:uppercase;font-size:12px;letter-spacing:.16em}.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:28px 0}article,.interpretation{border:1px solid #344150;border-radius:12px;padding:20px;background:#121d29}.row{display:flex;align-items:center;justify-content:space-between;gap:8px}.state{font-size:12px;border:1px solid #8194aa;border-radius:20px;padding:3px 9px}.success{color:#cce7a4;border-color:#698653}.failure,.timeout{color:#ffb5a7;border-color:#ab695d}.skipped{color:#adbacc}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px;color:#cbd9e8}.meta{font-size:13px;overflow-wrap:anywhere}footer{font-size:13px;color:#a9b8c9;margin-top:25px}summary{cursor:pointer;color:#cce7a4}@media(max-width:750px){.grid{grid-template-columns:1fr}main{padding:24px 16px}}
</style><main><header><span class="eyebrow">Local test report · Support Diagnostics Lab</span><h1>$title</h1>
<p>$(Encode-LabText $Evidence.target):$(Encode-LabText $Evidence.port) · $(Encode-LabText $Evidence.timestampUtc)</p>
<p class="meta">Source: $(Encode-LabText $Evidence.evidenceSource) · Run: $(Encode-LabText $Evidence.runId)</p></header>
<section class="grid" aria-label="Observed checks">$($cards -join "`n")</section>
<section class="interpretation"><h2>Interpretation and next check</h2><p>$(Encode-LabText $Evidence.nextStep)</p><p>These observations describe this target and time. They do not establish a hardware fault or the health of an entire network.</p></section>
<details><summary>Complete evidence</summary><pre>$(Encode-LabText $json)</pre></details>
<footer>Synthetic personal lab. This report records a test run, not independent learner completion. Implementation was AI-assisted.</footer></main></html>
"@
    $created = [Collections.Generic.List[string]]::new()
    try {
        foreach ($item in @(@{path=$jsonPath;text=$json}, @{path=$htmlPath;text=$html})) {
            $file = [IO.File]::Open($item.path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
            $created.Add($item.path)
            try { $bytes=[Text.UTF8Encoding]::new($false).GetBytes($item.text); $file.Write($bytes,0,$bytes.Length) }
            finally { $file.Dispose() }
        }
    } catch {
        foreach ($path in $created) { [IO.File]::Delete($path) }
        throw
    }
    [pscustomobject]@{JsonPath=$jsonPath;HtmlPath=$htmlPath}
}

Export-ModuleMember -Function Save-SupportReport
