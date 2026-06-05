# API Examples

```bash
export API_URL=http://localhost:8000
```

## Health

```bash
curl "$API_URL/healthz"
```

## Upload File

Supports PDF, DOCX, TXT, Markdown, and Notion export ZIP.

```bash
curl -X POST "$API_URL/documents/upload" \
  -F "file=@samples/company_handbook.md"
```

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

## List Sources

```bash
curl "$API_URL/sources"
```

## Sync A Source

```bash
curl -X POST "$API_URL/sources/{source_id}/sync"
```

## Delete A Source

```bash
curl -X DELETE "$API_URL/sources/{source_id}" -i
```

## Reindex All Sources

```bash
curl -X POST "$API_URL/reindex"
```

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

## Ask With Document Filter

```bash
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What documents are required for reimbursement?",
    "document_ids": ["document-id-here"]
  }'
```

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

## Metrics

```bash
curl "$API_URL/metrics"
```

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
