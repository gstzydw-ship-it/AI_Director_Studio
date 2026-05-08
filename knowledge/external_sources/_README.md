---
title: External Architecture Sources
doc_type: index
status: active
runtime_retrieval: false
---

# External Architecture Sources

This directory stores curated external projects that are useful for human review and architecture planning.

These files are not runtime rule cards and must not be injected into director agents. They are used to extract patterns, boundaries, and implementation ideas that can later be translated into local rules, tests, or tooling.

## Inclusion Policy

- Keep only sources with a clear reusable pattern for this director system.
- Summarize what to borrow and what to avoid.
- Do not install or run external frameworks from this directory.
- Do not treat external project docs as binding runtime instructions.
- Convert any accepted idea into local rule cards, tests, or scripts before it affects production behavior.

## Runtime Boundary

Every file here should use `runtime_retrieval: false`. The knowledge loader skips these files during vector/BM25 construction and agent knowledge injection.
