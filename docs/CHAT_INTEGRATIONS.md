# Chat Integrations

## Shared Behavior

Slack, Discord, and Telegram all route questions through `AskService`, the same service used by `POST /chat`. This keeps retrieval, citations, no-answer handling, logging, and metrics consistent across UI and bots.

## Slack

Slack slash commands call the FastAPI endpoint:

```text
POST /bots/slack/ask
```

Set:

```env
SLACK_VERIFICATION_TOKEN=optional_legacy_token
```

For production, expose the API with a public HTTPS URL and configure a slash command:

```text
/ask
https://your-domain.example/bots/slack/ask
```

## Discord

Set:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
```

The `bots` Docker service starts the Discord adapter and registers `/ask question`.

## Telegram

Set:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

The `bots` Docker service starts polling and supports:

```text
/ask What is the leave policy?
```

## Local Docker

```bash
docker compose up --build api worker bots postgres qdrant redis
```

If no bot tokens are configured, the bot runner idles and the API remains usable.
