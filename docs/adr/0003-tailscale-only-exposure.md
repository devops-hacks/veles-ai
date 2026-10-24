# ADR-0003: Tailnet-only exposure; zero public surface by default

- Status: accepted
- Date: 2026-10-18

## Context
The server must never be reachable from the public internet; family access
must be transparent on LAN and away (Ch. 4, Ch. 11).

## Decision
All surfaces bind to the tailnet: `tailscale serve` issues TLS for
`ai.<tailnet>.ts.net`; ACLs split tag:admin and tag:family; Funnel stays off
unless a guest needs read-only access; egress follows the A4 ledger.

## Consequences
No port forwarding, no public DNS, no public TLS renewal; offline LAN use
needs the A6 alias; DERP adds 50-200ms only on hostile relay paths.
