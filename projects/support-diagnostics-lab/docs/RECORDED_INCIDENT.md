# Recorded incident walkthrough — 30 September 2026

[Read the visual case study](https://bilalaseel.pages.dev/projects/support-diagnostics/walkthrough) · [Raw capture manifest](../examples/incident-2026-09-30/manifest.json)

## Scope and provenance

Owned synthetic Python HTTP fixture, Windows, IPv4 loopback port 56119. AI-assisted implementation and documentation; the assistant executed all recorded commands at Bilal's request. Independent practice by Bilal is not recorded. No production systems or customer data.

## Sequence and observations

1. Baseline: localhost resolves; TCP succeeds; HTTP 200 with the expected service identity and healthy status.
2. Deliberately change the running fixture's mode to unavailable: same TCP port succeeds; HTTP 503 and unavailable status are observed.
3. Restore healthy mode in the same fixture: repeat DNS, TCP and HTTP probes, then the automated checker. All three stages pass and the expected health payload returns.
4. Stop and close the owned fixture: TCP fails; separate curl probe fails to connect; the automated checker correctly skips HTTP after TCP failure.
5. Check missing.support-lab.invalid through the checker: name not found; dependent TCP and HTTP stages skipped.

The fixture was controlled through the public `lab/service.py` `create_server` API and its `mode` property, using one server process/port for the baseline, 503 and recovery sequence. Changing the mode intentionally injects/removes the application fault; it is not a diagnosis of an unknown production cause.

## Evidence and interpretation

The capture records actual Resolve-DnsName, Test-NetConnection and curl command output plus independent structured checker results. Each JSON includes timestamps and run IDs. curl's normal transfer meter is retained in stderr; its presence alone is not a command failure. Without --fail, curl can exit 0 for HTTP 503, so inspect the HTTP status and body.

Localhost name resolution is not a test of external DNS availability. TCP success is not application health. A failed TCP attempt is not proof of physical hardware failure. Recovery is scoped to this endpoint and time; no MTTR, uptime or production saving is claimed.

## Reproduce the method

Use the [manual practice guide](MANUAL_PRACTICE_AR.md) to launch healthy/unavailable fixtures and repeat probes. The guide uses default port 8765; recorded evidence above uses port 56119. Keep the same chosen port in the fixture and probes. Do not copy recorded outputs as your own results.

## Example customer update — not sent

The test service is reachable but its health endpoint returns an unavailable response. Connectivity and application-health results differ. Restore healthy mode and repeat the same checks before confirming recovery.

## Technical handover

Baseline, fault and recovery used one local endpoint. The known trigger was the injected unavailable mode. HTTP 200 and the expected application payload returned after restoration. Linked records preserve observations and remaining limits. The fixture was stopped after capture.

## References

- [Microsoft Test-NetConnection](https://learn.microsoft.com/en-us/powershell/module/nettcpip/test-netconnection?view=windowsserver2025-ps)
- [RFC 9110 HTTP 503](https://www.rfc-editor.org/rfc/rfc9110.html#name-503-service-unavailable)
