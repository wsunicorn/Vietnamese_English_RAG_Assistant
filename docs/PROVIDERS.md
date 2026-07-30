# AI Provider Setup

The app is provider-agnostic for generation and embeddings: every provider is called through the OpenAI Python SDK against an OpenAI-compatible endpoint (`AsyncOpenAI(api_key=..., base_url=...)`), because Gemini, Groq, OpenAI, and most gateways expose OpenAI-compatible `/chat/completions` and `/embeddings` routes. `LLM_PROVIDER` and `EMBEDDING_PROVIDER` are configured independently, so you can mix and match (e.g. fast Groq chat + Gemini embeddings).

## Recommended Free-Friendly Setup

Use Gemini for both chat and embeddings:

```env
LLM_PROVIDER=gemini
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_CHAT_MODEL=gemini-3.1-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-2-preview
```

Create the key in Google AI Studio:

```text
https://aistudio.google.com/apikey
```

Gemini's embeddings endpoint is called through `OpenAICompatibleEmbeddingClient`, which batches at 100 items per request and 100 requests/minute (Gemini's free-tier limit), spacing batches ~4.5s apart and retrying 429s with exponential backoff (parsing Gemini's `retryDelay` field when present). Large uploads or sitemap syncs on the free tier will therefore take noticeably longer than on a paid key — that's expected, not a hang.

## Fast Chat With Groq

Groq is good for fast/cheap chat models, but it does not serve embeddings for this app — `EMBEDDING_PROVIDER=groq` raises a clear `ValueError` at startup rather than failing silently. Pair Groq chat with Gemini (or OpenAI) embeddings:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key
GROQ_CHAT_MODEL=llama-3.1-8b-instant

EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_EMBEDDING_MODEL=gemini-embedding-2-preview
```

## OpenAI Setup

Use OpenAI when you want stronger answer quality and predictable embeddings:

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-your_key
OPENAI_CHAT_MODEL=gpt-5.5
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

`EMBEDDING_REQUEST_DIMENSIONS=true` additionally sends `dimensions=EMBEDDING_DIMENSIONS` on every embedding call — useful for OpenAI's `text-embedding-3-*` models, which support Matryoshka dimension truncation. Leave it `false` for providers that don't support that parameter (Gemini's client explicitly forces it off).

## Any OpenAI-Compatible API

Use this for OpenRouter, Together, LiteLLM, a local proxy, or another gateway:

```env
LLM_PROVIDER=openai-compatible
OPENAI_COMPATIBLE_API_KEY=your_gateway_key
OPENAI_COMPATIBLE_BASE_URL=https://your-provider.example/v1
OPENAI_COMPATIBLE_CHAT_MODEL=provider-chat-model

EMBEDDING_PROVIDER=openai-compatible
OPENAI_COMPATIBLE_EMBEDDING_MODEL=provider-embedding-model
```

`OPENAI_COMPATIBLE_BASE_URL` + the matching model name are required once you set the provider to `openai-compatible` — the app raises `ValueError` at request time rather than silently falling back if either is missing. If your gateway only supports chat, keep `EMBEDDING_PROVIDER` on `gemini`, `openai`, or `hash`.

## Local Development Fallback

No API key is required for local smoke tests:

```env
LLM_PROVIDER=development
EMBEDDING_PROVIDER=hash
EMBEDDING_DIMENSIONS=3072
```

`LLM_PROVIDER=development` (also accepts `dev`/`local`/`none`) skips the LLM entirely and returns a deterministic "development answer" built from the top 2 retrieved chunks — it still exercises retrieval, chunking, citations, and no-answer logic. `EMBEDDING_PROVIDER=hash` (also `local`/`development`/`dev`/`none`) uses `HashEmbeddingClient`: a token-hash-bucket embedding with no external calls, deterministic for a given `EMBEDDING_DIMENSIONS`, but not semantically meaningful — good for exercising the pipeline end to end, not for judging answer quality.

This combination is also what the fallback path silently uses in production if a real provider's API call fails at runtime (see [ARCHITECTURE.md#failure-modes](ARCHITECTURE.md#failure-modes)) — so "development answer" text appearing in production chat responses is a signal the configured provider is erroring, worth checking logs for.

## Optional Reranker

```env
RETRIEVAL_MODE=hybrid_rerank
RERANKER_PROVIDER=cohere
RERANKER_MODEL=rerank-v3.5
COHERE_API_KEY=your_cohere_key
```

Reranking is actually controlled by `RERANKER_PROVIDER` alone — it applies on top of whatever `RETRIEVAL_MODE` you pick (`dense`, `sparse`, or `hybrid`), not only `hybrid_rerank`. `hybrid_rerank` is a self-documenting value for "hybrid + reranker" but is functionally identical to `hybrid` in the retrieval layer. See [ARCHITECTURE.md#retrieval](ARCHITECTURE.md#retrieval) for the full explanation. Leave `RERANKER_PROVIDER=none` for the fastest free-friendly demo; if `COHERE_API_KEY` is missing or the Cohere call fails, the app logs a warning and keeps the original hybrid order rather than failing the chat request.

## Optional Bot Tokens

```env
SLACK_VERIFICATION_TOKEN=
DISCORD_BOT_TOKEN=
TELEGRAM_BOT_TOKEN=
```

`SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` are also present in `Settings` as placeholders for a future upgrade to Slack's HMAC request-signing verification and Slack Web API posting — neither is read by any code path today. See [CHAT_INTEGRATIONS.md](CHAT_INTEGRATIONS.md).

## Important Qdrant Note

Qdrant collections are created with a fixed dense vector size (`EMBEDDING_DIMENSIONS`, or the size of the first embedding actually returned if unset). If you switch embedding models/providers and the new model returns a different vector dimension, `ensure_collection()` raises immediately with a clear error — recreate the collection (or the `qdrant_storage` Docker volume) before indexing new documents with the new provider. Mixing dimensions in one collection is not supported.
