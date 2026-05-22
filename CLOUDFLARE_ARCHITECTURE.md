# Cloudflare Architecture for Veklom

This document outlines the architectural strategy for deploying the Veklom frontend and backend using Cloudflare's ecosystem, specifically comparing and utilizing Cloudflare Pages and Workers.

## Cloudflare Pages (Frontend Hosting)

Cloudflare Pages is Cloudflare’s static/JAMstack hosting platform: you push to Git and it builds and deploys your site globally on Cloudflare’s edge.

### What Cloudflare Pages is
It’s designed for frontend-heavy sites (static or JAMstack) like marketing pages, docs, and SPA frontends.
You connect a GitHub or GitLab repo, set a build command (e.g. for Next.js, Astro, SvelteKit), and Cloudflare runs the build and ships the assets worldwide.
Deploys are atomic and versioned: every push/PR gets its own preview URL, which is great for teams and review workflows.

### Key features relevant to Veklom
* **Global edge delivery:** Your static assets are served from Cloudflare’s worldwide PoPs with their CDN performance characteristics.
* **JAMstack focus:** First‑class support for React, Next.js SSG/ISR, Astro, SvelteKit, etc., including framework presets and environment variables.
* **Pages Functions:** You can attach lightweight server-side logic (similar to Workers) for simple APIs, SSR, or form handling, while keeping the main experience static. These functions are billed on the same model as Workers.
* **Git-based CI/CD:** Automatic build and deploy per branch, with preview URLs for PRs; main branch typically routes to production.
* **Custom domains + DNS:** You can attach your own domain and, if DNS is also on Cloudflare, it’s a single integrated workflow.

## When to use Pages vs Workers (For Veklom Control Planes)

From an architecture view (especially given our control plane and multi-tenant interests):

**Use Pages when:**
* You’re deploying static or mostly-static frontends (marketing sites, docs, simple dashboards).
* You want dead-simple Git-driven deploys and global hosting without managing infra.

**Use Workers (or Workers + Pages) when:**
* You need complex routing, custom APIs, queues, Durable Objects, or more serious backend compute.
* You want fine-grained control over request handling, multi-tenant isolation, or per-tenant logic at the edge.

A common pattern is: Pages serves the UI and static assets; Workers handle your APIs, auth, and more complex per-tenant logic.

| Use case | Cloudflare Pages | Cloudflare Workers |
|----------|-----------------|-------------------|
| Primary role | Static/JAMstack frontend hosting | General serverless compute & APIs |
| Deployment model | Git-based builds + previews | Direct code deploy via CLI/API |
| Dynamic logic | Light SSR/APIs via Pages Functions | Full flexibility (routing, queues, Durable Objects) |
| Pricing focus | Builds + static hosting, very generous free tier | Requests/CPU time, free tier + metered |
| Ideal workloads | Blogs, docs, marketing, simple SPAs | SaaS APIs, backend logic, complex apps |

## How this fits the Veklom Stack

Given the background (FastAPI backends, multi-tenant SaaS, control planes):

**Use Cloudflare Pages for:**
* Tenant-facing marketing sites or doc portals for products like Veklom or UACP.
* Serving the static shell of your dashboards, with calls back to your FastAPI or Worker-based APIs.

**Combine with Workers for:**
* Edge auth/session validation before hitting your core services.
* Latency-sensitive routing (e.g., region-aware routing of AI inference requests) at the edge.
