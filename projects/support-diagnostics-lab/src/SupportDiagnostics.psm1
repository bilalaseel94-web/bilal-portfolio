Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-LabLimits { @{ dns=5000; tcp=3000; http=5000; body=8192 } }

function New-LabStage($Name, $Status, $Duration, $Facts, $Reason) {
    [pscustomobject]@{name=$Name; status=$Status; durationMs=[long]$Duration; facts=$Facts; reason=$Reason}
}

function Wait-LabTask([Threading.Tasks.Task]$Task, [int]$Milliseconds) {
    if (-not $Task.Wait($Milliseconds)) { throw [TimeoutException]::new('deadline-exceeded') }
    $Task.GetAwaiter().GetResult()
}

function Get-LabRootError($Exception) {
    while ($Exception.InnerException) { $Exception = $Exception.InnerException }
    $Exception
}

function Resolve-LabName([string]$Name, [scriptblock]$Lookup = {param($value) [Net.Dns]::GetHostAddressesAsync($value)}) {
    $clock = [Diagnostics.Stopwatch]::StartNew()
    try {
        $task = & $Lookup $Name
        $ips = @(Wait-LabTask $task (Get-LabLimits).dns)
        $addresses = @($ips | ForEach-Object { $_.ToString() })
        $selected = if ($addresses -contains '127.0.0.1') { '127.0.0.1' } else { $null }
        if (-not $selected) { return New-LabStage dns failure $clock.ElapsedMilliseconds @{addresses=$addresses;selectedAddress=$null} 'address-not-permitted' }
        New-LabStage dns success $clock.ElapsedMilliseconds @{addresses=$addresses;selectedAddress=$selected} $null
    } catch {
        $root = Get-LabRootError $_.Exception
        $reason = 'resolver-error'; $status = 'failure'
        if ($root -is [TimeoutException]) { $reason='deadline-exceeded'; $status='timeout' }
        elseif ($root -is [Net.Sockets.SocketException] -and $root.SocketErrorCode -in @('HostNotFound','NoData')) { $reason='name-not-found' }
        New-LabStage dns $status $clock.ElapsedMilliseconds @{addresses=@();selectedAddress=$null} $reason
    }
}

function Test-LabTcp([int]$Port) {
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $client = [Net.Sockets.TcpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
    try {
        Wait-LabTask ($client.ConnectAsync('127.0.0.1', $Port)) (Get-LabLimits).tcp | Out-Null
        New-LabStage tcp success $clock.ElapsedMilliseconds @{address='127.0.0.1';port=$Port} $null
    } catch {
        $root = Get-LabRootError $_.Exception
        $status = if ($root -is [TimeoutException]) { 'timeout' } else { 'failure' }
        $reason = if ($status -eq 'timeout') { 'deadline-exceeded' } else { 'connection-failed' }
        New-LabStage tcp $status $clock.ElapsedMilliseconds @{address='127.0.0.1';port=$Port} $reason
    } finally { $client.Dispose() }
}

function Test-LabHttp([int]$Port) {
    $limits = Get-LabLimits
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.AllowAutoRedirect = $false
    $handler.UseProxy = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.Timeout = [Threading.Timeout]::InfiniteTimeSpan
    $cancel = [Threading.CancellationTokenSource]::new($limits.http)
    $response = $null; $stream = $null; $statusCode = $null; $identity = $false
    try {
        $response = $client.GetAsync("http://127.0.0.1:$Port/health", [Net.Http.HttpCompletionOption]::ResponseHeadersRead, $cancel.Token).GetAwaiter().GetResult()
        $statusCode = [int]$response.StatusCode
        if ($statusCode -ge 300 -and $statusCode -lt 400) {
            return New-LabStage http failure $clock.ElapsedMilliseconds @{statusCode=$statusCode;identityVerified=$false} 'redirect-not-followed'
        }
        $stream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $buffer = [byte[]]::new($limits.body + 1); $used = 0
        while ($used -lt $buffer.Length) {
            $read = $stream.ReadAsync($buffer, $used, $buffer.Length - $used, $cancel.Token).GetAwaiter().GetResult()
            if ($read -eq 0) { break }; $used += $read
        }
        if ($used -gt $limits.body) {
            return New-LabStage http failure $clock.ElapsedMilliseconds @{statusCode=$statusCode;identityVerified=$false} 'response-too-large'
        }
        $payload = $null
        try { $payload = [Text.Encoding]::UTF8.GetString($buffer, 0, $used) | ConvertFrom-Json -AsHashtable -ErrorAction Stop } catch { }
        if ($payload -is [System.Collections.IDictionary] -and $payload['service'] -is [string]) { $identity = $payload['service'] -ceq 'support-diagnostics-lab' }
        $reason = 'unexpected-service'; $status = 'failure'
        if ($identity) {
            if ($statusCode -eq 200 -and $payload['status'] -is [string] -and $payload['status'] -ceq 'ok') { $status='success'; $reason=$null }
            elseif ($statusCode -eq 503) { $reason='application-unavailable' }
            else { $reason='unexpected-application-response' }
        }
        New-LabStage http $status $clock.ElapsedMilliseconds @{statusCode=$statusCode;identityVerified=[bool]$identity} $reason
    } catch {
        $timeout = $cancel.IsCancellationRequested
        $status = if ($timeout) { 'timeout' } else { 'failure' }
        $reason = if ($timeout) { 'deadline-exceeded' } else { 'http-request-failed' }
        New-LabStage http $status $clock.ElapsedMilliseconds @{statusCode=$statusCode;identityVerified=$false} $reason
    } finally {
        if ($stream) { $stream.Dispose() }
        if ($response) { $response.Dispose() }
        $client.Dispose(); $cancel.Dispose()
    }
}

function Get-SupportFinding([object[]]$Stages) {
    $issue = @($Stages | Where-Object { $_.status -notin @('success','skipped') })
    if ($issue.Count -eq 0 -and @($Stages | Where-Object status -eq success).Count -eq 3) {
        return [pscustomobject]@{finding='healthy';nextStep='The expected local service passed these checks at this time. Preserve this baseline for comparison.'}
    }
    if ($issue.Count -eq 0) { return [pscustomobject]@{finding='incomplete-evidence';nextStep='Complete the missing checks before drawing a conclusion.'} }
    $stage = $issue[0]
    $finding = if ($stage.status -eq 'timeout') { "$($stage.name)-timeout" } else { $stage.reason }
    $next = switch ($stage.name) {
        dns { 'Review the name and resolver result. Later checks were not performed; this does not establish a device fault.' }
        tcp { 'Confirm the local lab service is running on this port. A failed connection alone does not identify the underlying cause.' }
        http { 'The TCP connection succeeded. Review the application response, restore healthy mode and repeat the complete check.' }
        default { 'Review the available evidence and complete the missing checks.' }
    }
    [pscustomobject]@{finding=$finding;nextStep=$next}
}

function Invoke-LabChecks($TargetName, $Port, [scriptblock]$Resolve, [scriptblock]$Tcp, [scriptblock]$Http, $EvidenceSource) {
    $dns = & $Resolve $TargetName
    if ($dns.status -eq 'success' -and $dns.facts.selectedAddress -cne '127.0.0.1') {
        $dns = New-LabStage dns failure $dns.durationMs $dns.facts 'address-not-permitted'
    }
    $tcpStage = New-LabStage tcp skipped 0 @{} 'dns-check-did-not-pass'
    $httpStage = New-LabStage http skipped 0 @{} 'tcp-check-not-performed'
    if ($dns.status -eq 'success') {
        $tcpStage = & $Tcp $Port
        if ($tcpStage.status -eq 'success') { $httpStage = & $Http $Port }
        else { $httpStage = New-LabStage http skipped 0 @{} 'tcp-check-did-not-pass' }
    }
    $stages = @($dns, $tcpStage, $httpStage)
    $finding = Get-SupportFinding $stages
    [pscustomobject]@{
        schemaVersion=1;runId=[guid]::NewGuid().ToString('N');timestampUtc=[DateTime]::UtcNow.ToString('o')
        target=$TargetName;port=$Port;evidenceSource=$EvidenceSource;stages=$stages
        finding=$finding.finding;nextStep=$finding.nextStep
    }
}

function Get-SupportEvidence {
    param([Parameter(Mandatory)][AllowEmptyString()][string]$TargetName, [Parameter(Mandatory)][int]$Port)
    $normal = $TargetName.ToLowerInvariant()
    if ($normal -cnotin @('localhost','127.0.0.1','missing.support-lab.invalid')) { throw 'Target must be localhost, 127.0.0.1 or missing.support-lab.invalid.' }
    if ($Port -lt 1 -or $Port -gt 65535) { throw 'Port must be between 1 and 65535.' }
    Invoke-LabChecks $normal $Port {param($name) Resolve-LabName $name} {param($p) Test-LabTcp $p} {param($p) Test-LabHttp $p} 'local-run'
}

Export-ModuleMember -Function Get-SupportEvidence, Get-SupportFinding
