# AI Provider Setup

The app is provider-agnostic for generation and embeddings. It uses the OpenAI SDK because Gemini, Groq, OpenAI, and many gateways expose OpenAI-compatible endpoints.

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

## Fast Chat With Groq

Groq is good for fast chat models, but this app still needs an embedding provider. Pair Groq chat with Gemini embeddings:

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

If your gateway only supports chat, use Gemini/OpenAI/hash for embeddings.

## Local Development Fallback

No API key is required for local smoke tests:

```env
LLM_PROVIDER=development
EMBEDDING_PROVIDER=hash
EMBEDDING_DIMENSIONS=3072
```

This mode is deterministic and useful for tests, but it is not portfolio-quality model output.

## Optional Reranker

Hybrid retrieval is the default. To test a reranked pipeline:

```env
RETRIEVAL_MODE=hybrid_rerank
RERANKER_PROVIDER=cohere
RERANKER_MODEL=rerank-v3.5
COHERE_API_KEY=your_cohere_key
```

Leave `RERANKER_PROVIDER=none` for the fastest free-friendly demo.

## Optional Bot Tokens

```env
SLACK_VERIFICATION_TOKEN=
DISCORD_BOT_TOKEN=
TELEGRAM_BOT_TOKEN=
```

See [CHAT_INTEGRATIONS.md](CHAT_INTEGRATIONS.md).

## Important Qdrant Note

Qdrant collections are created with a fixed dense vector size. If you switch embedding models and the new model returns a different vector dimension, recreate the collection or Docker volume before indexing new documents.
