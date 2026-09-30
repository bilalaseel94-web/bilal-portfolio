#Requires -Version 7.0
param([string]$TargetName='localhost', [string]$Port='8765', [string]$OutputDirectory='./reports')
$ErrorActionPreference = 'Stop'
$observed = $null
try {
    Import-Module "$PSScriptRoot/src/SupportDiagnostics.psm1" -Force
    Import-Module "$PSScriptRoot/src/Reports.psm1" -Force
    $portNumber = 0
    if (-not [int]::TryParse($Port, [ref]$portNumber)) { throw 'Port must be a whole number between 1 and 65535.' }
    $observed = Get-SupportEvidence -TargetName $TargetName -Port $portNumber
    $paths = Save-SupportReport -Evidence $observed -OutputDirectory $OutputDirectory
    [pscustomobject]@{finding=$observed.finding;JsonPath=$paths.JsonPath;HtmlPath=$paths.HtmlPath} | ConvertTo-Json -Compress
    if ($observed.finding -eq 'healthy') { exit 0 } else { exit 1 }
} catch {
    if ($observed) {
        [Console]::Error.WriteLine("Report saving failed; observed finding remains '$($observed.finding)'.")
        [pscustomobject]@{reportSaved=$false;evidence=$observed} | ConvertTo-Json -Depth 12 -Compress
    }
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
