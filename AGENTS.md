# AGENTS.md — READ THIS FIRST

> [!IMPORTANT]
> **Canonical Veklom operating context:** [`00_VEKLOM_BIBLE.md`](./00_VEKLOM_BIBLE.md)
>
> Read the Bible before modifying, deploying, or making production claims about this repository. It is the cross-repo source for architecture, runtime-truth rules, product boundaries, port ownership, and evidence standards.

## Repository-local rule

This repository owns BYOS backend implementation details. Repo-local source, tests, migrations, API contracts, and build instructions remain authoritative for this codebase **only when they do not conflict with the Bible or current 

## Production rule

A change is not complete because it merged or passed locally. Use the Bible completion standard:

`repo change → pushed commit → deployed runtime → live verification → evidence/report`

Use 

Do not commit or print secrets. Do not fabricate production data or evidence. Do not allocate host ports from memory; verify current host bindings first. In particular, host port `8000` is owned by 

## Historical document

The superseded 2026-07-12 AGENTS topology is retained in Git history and indexed at [`docs/archive/2026-08-09/README.md`](./docs/archive/2026-08-09/README.md). It is `ARCHIVED`, not current instructions.
