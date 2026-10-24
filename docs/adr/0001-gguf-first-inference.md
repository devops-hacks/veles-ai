# ADR-0001: GGUF-first inference via llama.cpp + llama-swap

- Status: accepted
- Date: 2026-10-18
- Deciders: operator

## Context
Serving must be model-agnostic, multi-consumer, and honest about the memory
bandwidth arithmetic (Ch. 5, Ch. 11). Ollama adds a measurable wrapper tax
(~1.4-1.6x, up to 2-3x MoE) and historically lagged llama.cpp.

## Decision
Raw `llama-server` instances orchestrated by llama-swap; GGUF pinned in
`models/models.toml` is the single source of truth; MLX used only for
distributed/RDMA experiments.

## Consequences
Full control of `-np/-c/-fa/-ctk/-ctv/--cont-batching`; we own the swap
profiles; Ollama stays available as a fallback profile, never the default.
