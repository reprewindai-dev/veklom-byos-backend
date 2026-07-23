---
name: dependency-update-multi-package
description: Workflow command scaffold for dependency-update-multi-package in veklom-byos-backend.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /dependency-update-multi-package

Use this workflow when working on **dependency-update-multi-package** in `veklom-byos-backend`.

## Goal

Updates dependencies across multiple package.json and package-lock.json files in different directories, typically as part of automated dependency management (e.g., Dependabot).

## Common Files

- `**/package.json`
- `**/package-lock.json`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Identify outdated dependencies in each package.
- Update the version numbers in package.json files.
- Regenerate package-lock.json files to reflect new dependency versions.
- Commit all changed package.json and package-lock.json files together.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.