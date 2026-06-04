# API Examples

Base URL:

```bash
export API_URL=http://localhost:8000
```

## Health

```bash
curl "$API_URL/healthz"
```

## Upload Document

```bash
curl -X POST "$API_URL/documents/upload" \
  -F "file=@samples/company_policy.pdf"
```

Expected response:

```json
{
  "document_id": "0f0e4c2b-6d67-4f6a-b45f-80f2c3c4d83d",
  "filename": "company_policy.pdf",
  "status": "indexed",
  "page_count": 8,
  "chunk_count": 24,
  "metadata": {
    "content_type": "application/pdf",
    "source_type": "pdf"
  }
}
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

## Ask An English Question With Document Filter

```bash
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What documents are required for reimbursement?",
    "document_ids": ["0f0e4c2b-6d67-4f6a-b45f-80f2c3c4d83d"]
  }'
```

## No-Answer Test

```bash
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What was the weather in Tokyo yesterday?"
  }'
```

Expected behavior:

- `no_answer` is `true`;
- `citations` is empty;
- answer says the information is not available in uploaded documents.

## Submit Feedback

```bash
curl -X POST "$API_URL/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "bfa99353-3e8a-4fb5-8f63-760d26296fd4",
    "rating": 1,
    "comment": "Citation was correct."
  }'
```

Rating convention:

- `1`: helpful;
- `0`: neutral;
- `-1`: needs work.

## Metrics

```bash
curl "$API_URL/metrics"
```

## Delete Document

```bash
curl -X DELETE "$API_URL/documents/0f0e4c2b-6d67-4f6a-b45f-80f2c3c4d83d" -i
```
