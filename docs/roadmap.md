# Roadmap and Feature Gate

Mirrors Chapter 13 of the architecture document. Every feature enters the
project through this gate. Verdicts: Adopt / Adopt-with-amendments /
Integrate-don't-build / Defer.

## Admission gate (all six must pass)

| # | Question |
|---|----------|
| G1 | Privacy — no unlogged, non-revocable egress? |
| G2 | Capacity — fits the bandwidth/KV arithmetic at worst-case concurrency? |
| G3 | State — stateful services go to compose, never the inference host? |
| G4 | Trust — untrusted input gets an injection review; data is never instructions? |
| G5 | Offline — degrades gracefully without internet? |
| G6 | Ops — failure mode fits the one-operator register? |

## Amendments (reserved seams — build in PR 1/2, before features)

- **A1 Gateway identity**: per-consumer API keys + quotas at llama-swap's choke point.
- **A2 Memory namespaces**: `user_id` in the memory adapter API from commit one.
- **A3 Tool permissions**: MCP servers allowlisted, containerized, least-privilege.
- **A4 Egress ledger**: declared connectors only (search, calendar, model sync), logged.
- **A5 Async boundary**: agent jobs via queue service; no agent execution on the inference host.
- **A6 Offline posture**: LAN alias URLs + local-CA fallback for Serve certificates.

## Dossier

| Feature | Verdict | Effort | Impact / depends on |
|---|---|---|---|
| Offline use | Adopt (mostly free) | S | A6; one-page runbook |
| Autonomous agents | Adopt w/ amendments | L | A1, A3, A5 first; blast-radius rule |
| Deep research (SearXNG) | Adopt via tool | M | MCP tool + container; A4; cache results |
| Email integration | **Defer** | M | Read-only allowlist after A3 matures; injection + PII risk |
| Calendar sync | Adopt | S | Read-only CalDAV connector; A2 |
| Document editor | Integrate, don't build | M | OnlyOffice/Collabora in compose; file-based docs |
| Persistent memory | Present (Ch. 3) | - | Extend with namespaces (A2) now |
| MCP / plugins | Adopt w/ governance | M | A1, A3; supply-chain review per server |
| Mobile app (PWA) | Present (Ch. 11) | S | Web push, share sheet; native not justified |
| Multi-user (family) | Adopt incrementally | M | A1, A2; WebUI accounts; audit |
| Privacy (local-first) | Invariant | S | Formalized by A4 |

Out of scope for initial delivery unless implementation effort is negligible.

## v1.5 - Shared memory contexts (Chapter 14)

Team/family collaboration lands as an additive extension, not a redesign:
one new namespace root (`viking://family/`), a two-level ACL
(`services/memory/namespaces.example.yaml`), and cross-namespace
retrieval with provenance labels. Default policy: **read shared, write
private**; explicit override copies with attribution. Gate: PASS (G1 via
write-default + confirmation gate + audit log; G2 trivial; G3-G6 clean).
Roadmap slot: early v1.5 - after multi-user accounts (A1+A2), before
autonomous agents go wide.

## v1.6 - Security and privacy audit (Chapter 15)

Comprehensive pass over the full design: threat model (7 actors),
back-door check (4 inbound surfaces, 6-row egress ledger in
`docs/egress-ledger.yaml`), 13-finding dossier (S1-S13; 7 absorbed from
the external audit brief, 6 new). Remediation is phased: Phase 1 day-one
baseline (under half a day, folded into PR 0-2, see
`docs/security.md`) + Phase 2 hardening backlog after v1 stabilizes.
Delivery timescales unchanged.
