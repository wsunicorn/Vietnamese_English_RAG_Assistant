import asyncio
import logging

from app.bots.discord_bot import run_discord_bot
from app.bots.telegram_bot import run_telegram_bot
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await init_db()
    tasks = []
    if settings.discord_bot_token:
        tasks.append(asyncio.create_task(run_discord_bot(settings)))
    if settings.telegram_bot_token:
        tasks.append(asyncio.create_task(run_telegram_bot(settings)))
    if not tasks:
        logger.info("No Discord or Telegram token configured; bot runner is idle.")
        while True:
            await asyncio.sleep(3600)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
