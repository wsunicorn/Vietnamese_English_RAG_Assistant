# Chat Integrations

## Shared Behavior

Slack, Discord, and Telegram all route questions through `AskService.ask()` — the same service backing `POST /chat` and the web UI. This keeps retrieval, citations, no-answer handling, logging, and metrics identical across every surface; the only difference between adapters is how the question comes in and how the answer is formatted back out (`app/bots/common.py::format_chat_response`, which appends up to 3 compact `[C1] source` lines after the answer text).

Every bot call also writes a `request_metrics`/chat-log row tagged with `channel` (`"slack"`/`"discord"`/`"telegram"`) and `user_id`, so `/metrics` and the `chat_logs` table reflect bot usage alongside UI usage.

## Slack

Slack slash commands call the FastAPI endpoint directly (no separate Slack process needed):

```text
POST /bots/slack/ask
```

Set:

```env
SLACK_VERIFICATION_TOKEN=optional_legacy_token
```

If set, the endpoint rejects any request whose `token` form field doesn't match with `401`. **This is Slack's deprecated verification-token scheme, not real request-signature verification** — it's a shared secret sent in plaintext with the payload, not an HMAC over the request. `SLACK_SIGNING_SECRET` exists in `Settings` for the proper `X-Slack-Signature`/timestamp verification but is not implemented yet (tracked in [CHECKLIST.md](../CHECKLIST.md)); until it is, do not treat this endpoint as fully authenticated — restrict it at the network/reverse-proxy layer if you expose it publicly.

For production, expose the API with a public HTTPS URL and configure a slash command:

```text
/ask
https://your-domain.example/bots/slack/ask
```

The response is a plain in-channel message (`response_type: "in_channel"`), not an ephemeral ack followed by a delayed webhook — so the whole `/chat` round trip (embedding + retrieval + generation) happens inside Slack's ~3 second slash-command timeout budget. Keep `top_k`/prompt size modest and your LLM provider fast if you rely on this path in production.

## Discord

Set:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
```

The `bots` Docker service (`app/bots/runner.py`) starts the Discord adapter only if this token is present, and registers a single `/ask question:<text>` slash command via `discord.app_commands`. The interaction is deferred (`thinking=True`) immediately, so it isn't bound by Discord's 3-second ack window the way Slack is — the full retrieval+generation call can take as long as it needs, then `followup.send()` delivers the answer (truncated to 1900 characters to stay under Discord's message limit).

## Telegram

Set:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

The `bots` Docker service starts long-polling and supports:

```text
/ask What is the leave policy?
```

Replies are truncated to 3900 characters (Telegram's message limit is 4096).

## Local Docker

```bash
docker compose up --build api worker bots postgres qdrant redis
```

If no bot tokens are configured, `app/bots/runner.py` logs that it's idle and sleeps forever rather than exiting — the container stays healthy, it just does nothing, and the API/UI remain fully usable without it.
