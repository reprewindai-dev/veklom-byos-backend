# UACPGemini V2 Working Copy

**Root = UACP V3 control plane. Nested `source-uacpgemini` = UACP V2 working reference copy.**

This folder is the runnable V2 workspace cloned from `reprewindai-dev/uacpgemini`.

Naming rule:

- This folder is the `UACP V2 nested working copy`.
- The parent repository root is the `UACP V3 root project`.
- `V2 executes; V3 governs.`

## What it is

- Gemini-based deterministic planning shell
- React + Tailwind + Motion frontend
- Express + WebSocket backend
- plans, runs, events, SSRN-style signals, and observability telemetry

## Local run

```bash
npm install
npm run dev
```

Default URL:

- [http://localhost:3001](http://localhost:3001)

## Notes

- Port defaults to `3001` here so it can run side by side with the V3 app in the parent folder.
- `npm run lint` passes.
- `npm run build` passes.
