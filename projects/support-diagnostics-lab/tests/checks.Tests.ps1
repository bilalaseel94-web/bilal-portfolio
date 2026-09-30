$ErrorActionPreference = 'Stop'
Import-Module "$PSScriptRoot/../src/SupportDiagnostics.psm1" -Force
function Assert-Equal($Actual, $Expected) { if ($Actual -cne $Expected) { throw "Expected [$Expected], got [$Actual]" } }
$module = Get-Module SupportDiagnostics
$count = 0
foreach ($target in @('example.com','http://localhost','127.0.0.2','localhost/','')) {
    $thrown = $false
    try { Get-SupportEvidence -TargetName $target -Port 8765 | Out-Null } catch { $thrown = $true }
    Assert-Equal $thrown $true; $count++
}
foreach ($port in @(0,65536,-1)) {
    $thrown = $false
    try { Get-SupportEvidence -TargetName localhost -Port $port | Out-Null } catch { $thrown = $true }
    Assert-Equal $thrown $true; $count++
}
$results = & $module {
    $okDns = { New-LabStage dns success 1 @{addresses=@('127.0.0.1'); selectedAddress='127.0.0.1'} $null }
    $okTcp = { New-LabStage tcp success 1 @{} $null }
    $badDns = { New-LabStage dns failure 1 @{} 'name-not-found' }
    $timeoutDns = { New-LabStage dns timeout 1 @{} 'deadline-exceeded' }
    $badHttp = { New-LabStage http failure 1 @{statusCode=503; identityVerified=$true} 'application-unavailable' }
    $unknownHttp = { New-LabStage http failure 1 @{statusCode=200; identityVerified=$false} 'unexpected-service' }
    $externalDns = { New-LabStage dns success 1 @{addresses=@('203.0.113.1'); selectedAddress='203.0.113.1'} $null }
    [pscustomobject]@{
        missing = Invoke-LabChecks localhost 8765 $badDns $okTcp $badHttp 'controlled-test'
        timeout = Invoke-LabChecks localhost 8765 $timeoutDns $okTcp $badHttp 'controlled-test'
        application = Invoke-LabChecks localhost 8765 $okDns $okTcp $badHttp 'controlled-test'
        unknown = Invoke-LabChecks localhost 8765 $okDns $okTcp $unknownHttp 'controlled-test'
        external = Invoke-LabChecks localhost 8765 $externalDns { throw 'Must not connect' } $badHttp 'controlled-test'
        limits = Get-LabLimits
    }
}
Assert-Equal $results.missing.stages[2].status 'skipped'
Assert-Equal $results.missing.finding 'name-not-found'
Assert-Equal $results.timeout.finding 'dns-timeout'
Assert-Equal $results.application.finding 'application-unavailable'
Assert-Equal $results.unknown.finding 'unexpected-service'
Assert-Equal $results.external.stages[1].status 'skipped'
Assert-Equal $results.external.finding 'address-not-permitted'
Assert-Equal $results.limits.dns 5000
Assert-Equal $results.limits.tcp 3000
Assert-Equal $results.limits.http 5000
$clock = [Diagnostics.Stopwatch]::StartNew()
$deadline = & $module {
    try { Wait-LabTask ([Threading.Tasks.Task]::Delay(1000)) 30; 'not-timed-out' }
    catch [TimeoutException] { 'timed-out' }
}
Assert-Equal $deadline 'timed-out'
if ($clock.ElapsedMilliseconds -gt 800) { throw 'Deadline did not bound the operation' }
$dnsError = & $module {
    Resolve-LabName localhost { param($Name)
        $pending = [Threading.Tasks.TaskCompletionSource[Net.IPAddress[]]]::new()
        $pending.SetException([Net.Sockets.SocketException]::new(11001))
        return $pending.Task
    }
}
Assert-Equal $dnsError.reason 'name-not-found'
Write-Output "PASS: $($count + 12) diagnostic checks"
