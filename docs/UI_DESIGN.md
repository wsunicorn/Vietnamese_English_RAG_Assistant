# UI Design

This documents the UI as actually built (`app/static/index.html`, `app.js`, `styles.css`), not an aspirational brief. It is a single static page with two sections that are shown/hidden by a tiny client-side router: a marketing **landing page** and an operator **app workspace**. Both are served by FastAPI from `/` — there is no separate frontend build step or framework.

## Design Language

- One accent color drives both themes: teal/green (`--accent: #34d399` in dark mode, `#087f5b` in light mode), used consistently for primary actions, active states, and the "retrieval confidence" feel across citations and status pills.
- Dark mode is the default (`data-theme="dark"` on `<html>`), overridable by `?theme=light` in the URL or the in-app toggle; the choice persists in `localStorage` under `rag-theme`.
- Typography: Manrope for UI text, JetBrains Mono for anything code/metadata-like (scores, token counts). Icons are Lucide, loaded from a CDN and rendered client-side.
- Client-side rendering only — no bundler. `app.js` is loaded as a native ES module and manages a single `state` object, DOM lookups cached in `els`, and manual `innerHTML` templating with `escapeHtml`/DOMPurify for anything derived from server data (citation quotes, filenames) before it's inserted into the DOM.

## Landing Page

Reached at `/#home` (default). Marketing surface for the portfolio, not the operator tool:

- Sticky nav with brand, an "Open App" link, and the theme toggle.
- Hero with an animated particle canvas background, headline, subheadline, and two CTAs (`Open Assistant` -> app workspace, `Explore Features` -> anchor scroll).
- A 6-card feature grid (multilingual RAG, hybrid retrieval, live citations, web ingestion, multi-source, realtime updates) and a scrolling tech-stack marquee (Gemini AI, Qdrant, FastAPI, PostgreSQL, Redis, Docker, Python, Embeddings).
- A closing CTA card and footer.

Scroll-triggered reveal animations (`.reveal` class) are applied via an `IntersectionObserver` in `app.js`.

## App Workspace

Reached at `/#app`. This is the actual product surface, and is what the [portfolio deliverables](../README.md#portfolio-deliverables) screenshots should focus on. Layout:

**Top bar**: brand mark (links back to the landing page), a live metrics strip (Sources / Documents / Chunks / Latency, populated from `GET /metrics` and refreshed on realtime events), a workspace-panel toggle (collapses the left rail on narrow viewports), a theme toggle, and a realtime connection indicator (`Connecting` / `Live` / degraded state, driven by the `/ws/realtime` socket).

**Left rail** (`document-rail`) — a tabbed panel with three views:

1. **Sources** (default tab): two collapsible forms — file upload (drag-and-drop styled dropzone, accepts `.pdf,.docx,.txt,.md,.markdown,.zip`, 25 MB note) and web/sitemap ingestion (URL, mode select, max pages, optional sync-interval minutes) — plus a live list of `data_sources` with status pill, type pill, last-synced time, and document/chunk counts. A "reindex all" button queues `POST /reindex`.
2. **Docs**: the flat list of indexed `documents`, each selectable (checkbox-style card) to scope the next chat question to specific documents; selection count shown, with a "Clear" action.
3. **History**: locally-remembered chat turns (client-side only, not a server endpoint) for quick recall, with a "Clear" action.

**Center panel** — the chat surface: message transcript rendered as Markdown (via `marked` + DOMPurify sanitization) with a `Top K` selector (4/6/8/10, sent as `ChatRequest.top_k`), a scope label reflecting the current document selection, a 4000-character composer, and an "N citations / View evidence" button that opens the evidence drawer.

**Evidence drawer** — a right-side sliding panel (modal on narrow viewports) with two tabs:

- **Cites**: citation cards — citation id, source title/filename, source-type pill, page, similarity/rerank score, and the quoted excerpt.
- **Trace**: the full `retrieval_trace` (every chunk the retriever returned, ranked, including ones the LLM didn't cite) — this is the debugging view for "why didn't it find X".

A toast stack (bottom-right) surfaces success/error notifications for uploads, ingestion, sync, and delete actions.

## Realtime Behavior

On entering the app workspace, `app.js` opens `WS /ws/realtime`. Incoming events carry a `refresh` array (e.g. `["documents", "sources", "metrics"]`); the client debounces and re-fetches only the named panels via the normal REST endpoints rather than trusting the event payload as the data itself. If the socket drops, the client auto-reconnects with backoff and the top-bar indicator reflects `Connecting`/degraded state so the operator knows live updates aren't currently flowing (the UI keeps working via manual refresh either way).

## Responsive Behavior

- Desktop: three-column-equivalent layout — collapsible rail, chat, and an overlay evidence drawer.
- Tablet/mobile: the rail becomes an off-canvas panel behind a scrim (`rail-scrim`), toggled by the workspace button; the evidence drawer becomes a bottom/full sheet; the chat composer and send button stay full-width and high-contrast.

## Portfolio Screenshots Checklist

Capture these states from the **app workspace**, not the landing page, since they're the actual proof of engineering:

- Empty workspace before any upload (source rail empty state).
- Successful document upload with chunk count.
- Source dashboard with a synced website/sitemap source.
- Vietnamese question with citations open in the evidence drawer.
- English question with citations open in the evidence drawer.
- Retrieval trace tab (shows ranked candidates including non-cited ones).
- No-answer response.
- Feedback submitted + metrics strip updated.
- Realtime indicator showing `Live` while a background sync completes.
