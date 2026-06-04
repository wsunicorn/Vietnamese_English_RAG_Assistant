# UI Design Direction

## Design Read

Reading this as: technical B2B AI tooling for recruiters and Upwork clients, with a sober product-console language, leaning toward crisp Tailwind-style structure, high information clarity, and restrained motion.

## Principles

- Show the actual workflow immediately: upload, document list, chat, citations, metrics.
- Avoid generic AI purple gradients, centered marketing-only hero sections, and decorative card sprawl.
- Use dense but readable panels: this is an operational tool, not a landing page.
- Keep one accent color across the app: teal/green for retrieval confidence and action.
- Use clear loading, empty, and error states.
- Make citations inspectable without opening dev tools.

## Screens

Main screen:

- Left panel: corpus, upload, indexed documents, delete action.
- Center panel: chat transcript, no-answer state, feedback controls.
- Right panel: citation cards with filename, page, score, quote.
- Top strip: document count, chunk count, chat count, average latency.

Responsive behavior:

- Desktop: three-column tool surface.
- Tablet/mobile: stacked panels, chat remains central.
- Buttons remain one line and high contrast.

## Portfolio Screenshots

Capture these states:

- Empty app before upload.
- Successful document upload.
- Vietnamese question with citations.
- English question with citations.
- No-answer response.
- Feedback submitted.
- Metrics after multiple chats.
