# API Examples

```bash
export API_URL=http://localhost:8000
```

## Health

```bash
curl "$API_URL/healthz"
```

## Upload File

Supports PDF, DOCX, TXT, Markdown, and Notion export ZIP (max 25 MB by default, `MAX_FILE_MB`).

```bash
curl -X POST "$API_URL/documents/upload" \
  -F "file=@samples/company_handbook.md"
```

A Notion export ZIP can contain many pages; the response's `documents` array lists one entry per indexed page. The top-level `page_count`/`chunk_count` are totals summed across all of them, but `document_id` is only the *first* page's id — use `documents[].document_id` (or `GET /documents`) to address a specific page, e.g. for `document_ids` filtering in `/chat`.

## Ingest Website Page

```bash
curl -X POST "$API_URL/documents/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/docs/handbook",
    "mode": "page",
    "max_pages": 1,
    "sync_interval_minutes": null
  }'
```

This returns `200` with `status="queued"` — the page isn't indexed synchronously, only a `data_sources` row and a queued job are created. Poll `GET /sources` or open `WS /ws/realtime` to see it flip to `indexed` (or `failed`).

## Ingest Sitemap

```bash
curl -X POST "$API_URL/documents/ingest-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/sitemap.xml",
    "mode": "sitemap",
    "max_pages": 25,
    "sync_interval_minutes": 1440
  }'
```

`sync_interval_minutes` (5 to 43200) makes this source eligible for automatic re-sync by the worker; omit or send `null` for manual-only sync. Sitemap indexes (`<sitemapindex>` referencing other sitemaps) are resolved recursively, and only URLs on the same domain as the sitemap you submitted are kept.

## List Sources

```bash
curl "$API_URL/sources"
```

Each entry includes `status` (`queued`/`running`/`indexed`/`failed`), `last_synced_at`, `last_error`, and live `document_count`/`chunk_count` aggregates.

## Sync A Source

```bash
curl -X POST "$API_URL/sources/{source_id}/sync"
```

Re-fetches and fully re-indexes that source (old chunks for it are deleted from Qdrant and Postgres first, then replaced).

## Delete A Source

```bash
curl -X DELETE "$API_URL/sources/{source_id}" -i
```

Deletes the source row, its documents, and its vectors in Qdrant.

## Reindex All Sources

```bash
curl -X POST "$API_URL/reindex"
```

Queues one `source_sync` job per existing source (skips any source that already has a job in flight).

## List Documents

```bash
curl "$API_URL/documents"
```

## Ask A Vietnamese Question

```bash
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Chinh sach nghi phep nam duoc quy dinh nhu the nao?",
    "top_k": 6
  }'
```

The response includes `citations` (with `source_type`/`source_url`/`source_path` when applicable), `retrieval_trace` (every candidate the retriever returned, not just the ones cited), `no_answer`, `confidence`, token `usage`, and `latency_ms`.

## Ask With Document Filter

```bash
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What documents are required for reimbursement?",
    "document_ids": ["document-id-here"]
  }'
```

`document_ids` restricts retrieval to those documents via a Qdrant `MatchAny` filter on `document_id` — it does not change the no-answer threshold or scoring.

## Feedback

```bash
curl -X POST "$API_URL/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "chat-id-here",
    "rating": 1,
    "comment": "Citation was correct."
  }'
```

`rating` must be `-1`, `0`, or `1`.

## Metrics

```bash
curl "$API_URL/metrics"
```

Aggregates counts (`documents`, `chunks`, `sources`, `chats`, `feedback`, `queued_jobs`) and `avg_chat_latency_ms`/`total_tokens`/`estimated_cost_usd` across all logged chats. `estimated_cost_usd` is `0` unless `INPUT_COST_PER_1M_TOKENS`/`OUTPUT_COST_PER_1M_TOKENS` are set — cost tracking is opt-in.

## Realtime Event Stream

```bash
# using websocat (https://github.com/vi/websocat)
websocat "ws://localhost:8000/ws/realtime"
```

```js
// from a browser console
const socket = new WebSocket("ws://localhost:8000/ws/realtime");
socket.onmessage = (event) => console.log(JSON.parse(event.data));
```

The first message is always `{"type": "connected", ...}`. After that you'll see events like `document.uploaded`, `source.queued`, `source.running`, `source.indexed`, `job.failed`, `chat.completed`, and `feedback.stored`, each with a `refresh` array naming which UI panels changed. If Redis pub/sub is unavailable, you'll instead get one `realtime.degraded` event followed by a `heartbeat` roughly every 20 seconds — the socket stays open either way.

## Slack Slash Command Endpoint

Configure Slack slash command URL:

```text
https://your-public-domain.example/bots/slack/ask
```

Local curl example:

```bash
curl -X POST "$API_URL/bots/slack/ask" \
  -F "text=What is the leave policy?" \
  -F "user_id=U123"
```

If `SLACK_VERIFICATION_TOKEN` is set, include `-F "token=your_token"` or the endpoint returns `401`. See [CHAT_INTEGRATIONS.md](CHAT_INTEGRATIONS.md) for what this token does and does not protect against.
