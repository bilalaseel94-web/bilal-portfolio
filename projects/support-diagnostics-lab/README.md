# Support Diagnostics Lab

A small local troubleshooting lab: distinguish a name-resolution problem, an unreachable TCP port and an application returning HTTP 503. Preserve the evidence, explain its limits, and verify recovery.

**Project status:** AI-assisted implementation. Software verification and the owner's independent practice are separate. This is a synthetic personal learning project, not an employer system or proof of production results.

## Run locally

Requires PowerShell 7+ (`pwsh`) and Python 3.12+ (`python`), with no additional packages. If either command is unavailable, use its installed executable's full path. No administrator access is required for the lab itself.

In one terminal at the project root:

```powershell
python lab/service.py --port 8765 --mode healthy
```

Keep it open. In another PowerShell terminal, first try the manual checks in [the practice guide](docs/MANUAL_PRACTICE_AR.md), then:

```powershell
pwsh -NoProfile -File ./Invoke-SupportCheck.ps1 -TargetName localhost -Port 8765
```

The checker saves new JSON and HTML files under `reports/`. Open the printed HTML path. Exit codes: 0 = the expected lab service passed, 1 = a diagnostic issue was observed, 2 = invalid input or setup/report-saving failure.

Stop the server with Ctrl+C. To simulate application failure, start it with `--mode unavailable`. Recheck after restoring `--mode healthy`. If the port is occupied, choose another and pass it to both commands. The lab never stops other programs for you.

## Boundaries

- TCP/HTTP connections are restricted to IPv4 loopback. This tool is not a network scanner.
- The reserved `missing.support-lab.invalid` exercise uses the configured OS DNS resolver. Results can vary; a timeout is not reported as a confirmed nonexistent name.
- A listening port does not prove the application works. A failed check does not prove defective hardware. All findings are scoped to the test and time shown.
- HTTP redirects and proxies are disabled. No credentials, personal device inventory or employer logs are collected.
- No scheduled task, background service or AI API is involved. The service runs only while started.

## Learn and verify

[Start here — العربية](docs/START_HERE_AR.md) · [Manual practice](docs/MANUAL_PRACTICE_AR.md) · [Interview questions](docs/INTERVIEW_PRACTICE_AR.md) · [Incident template](docs/INCIDENT_TEMPLATE.md)

```powershell
python -m unittest discover -s tests -v
pwsh -NoProfile -File tests/checks.Tests.ps1
pwsh -NoProfile -File tests/reports.Tests.ps1
```

Tests use local synthetic services and temporary files. They do not establish that Bilal completed the independent exercises. The website must distinguish project technologies from demonstrated personal proficiency.

## Recorded investigation

[Incident walkthrough](docs/RECORDED_INCIDENT.md) follows a real local baseline → injected HTTP 503 → verified recovery sequence, with command transcripts, raw evidence and example customer/technical updates. These are assistant-run observations, not independent owner practice.
